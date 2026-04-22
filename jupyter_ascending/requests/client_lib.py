from typing import TypeVar

import attr  # type: ignore
import time
import requests

from ..jsonrpc_utils import Ok
from ..jsonrpc_utils import parse, request

from jupyter_ascending._environment import EXECUTE_HOST_URL
from jupyter_ascending.handlers.server_extension import perform_notebook_request
from jupyter_ascending.json_requests import JsonBaseRequest

GenericJsonRequest = TypeVar("GenericJsonRequest", bound=JsonBaseRequest)

_NOTEBOOK_NOT_FOUND_SUBSTRING = "Unable to find a paired notebook"


class RequestFailure(Exception):
    pass


def request_notebook_command(json_request: GenericJsonRequest,
                             max_tries: int = 5,
                             retry_delay: float = 1.0) -> None:
    """This is a command to be used by the client libraries to send a command to this server.

    It calls unpacks the JsonRequest and calls `perform_notebook_request` defined above."""
    json = request(
        perform_notebook_request.__name__,
        params=dict(
            command_name=type(json_request).__name__,
            notebook_path=json_request.file_name,
            data=attr.asdict(json_request),
        ),
    )

    error: Exception | None = None

    for attempt in range(max_tries + 1):
        try:
            response = requests.post(EXECUTE_HOST_URL, json=json, timeout=9)
            response.raise_for_status()
            result = parse(response.json())

            if isinstance(result, Ok):
                return

            error_msg = f"JSONRPC request returned as failure: {result}"
            if _NOTEBOOK_NOT_FOUND_SUBSTRING in (result.message or ""):
                raise RequestFailure(error_msg)
            error = RequestFailure(error_msg)

        except requests.exceptions.ConnectionError as e:
            error = RequestFailure(
                "Unable to connect to server. Perhaps notebook is not running?"
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code < 500:
                raise RequestFailure(
                    "Unable to process request. Is jupyter-ascending installed in the server's python environment? Perhaps something else is running on this port?"
                ) from e
            error = RequestFailure(
                f"Server error (HTTP {e.response.status_code}), retrying...")

        if attempt < max_tries:
            time.sleep(retry_delay)

    if error is None:
        raise RequestFailure("Max retries exceeded with no retryable error.")

    raise error
