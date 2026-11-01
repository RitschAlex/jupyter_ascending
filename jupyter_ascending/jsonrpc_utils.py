import uuid
import orjson as json

from typing import Any, Callable, Optional, Union
from loguru import logger


class Result:
    pass


class Success(Result):

    def __init__(self, result: Any = None):
        self.result = result


class Error(Result):

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data


class JsonRpcError:

    def __init__(self, code: int, message: str, data: Any, id: Any):
        self.code = code
        self.message = message
        self.data = data
        self.id = id


class Ok:

    def __init__(self, result: Any, id: Any):
        self.result = result
        self.id = id


class ServerMethods:
    """
    Wrapper to make some things a bit nicer around jsonrpcserver.methods.Methods
    """

    def __init__(self):
        self.items = {}

    def add(self, f: Callable) -> Callable:
        self.items[f.__name__] = f
        return f

    def __getitem__(self, method_name: str) -> Callable:
        return self.items[method_name]

    def __contains__(self, method_name: str) -> bool:
        return method_name in self.items


_default_methods = ServerMethods()


def method(func: Callable) -> Callable:
    """Decorator to register a function as a JSON-RPC method."""
    return _default_methods.add(func)


def dispatch(request_str: str, methods: Optional[ServerMethods] = None) -> str:
    method_dict = methods if methods is not None else _default_methods

    try:
        req = json.loads(request_str)
    except json.JSONDecodeError:
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32700,
                "message": "Parse error"
            },
            "id": None
        }).decode("utf-8")

    if not isinstance(req, dict):
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32600,
                "message": "Invalid Request"
            },
            "id": None
        }).decode("utf-8")

    req_id = req.get("id")
    method_name = req.get("method")

    if not isinstance(method_name, str) or method_name not in method_dict:
        err_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": "Method not found"
            },
            "id": req_id
        }
        return json.dumps(err_response).decode("utf-8")

    func = method_dict[method_name]
    params = req.get("params", [])
    if params is None:
        params = []

    try:
        if isinstance(params, dict):
            res = func(**params)
        elif isinstance(params, list):
            res = func(*params)
        else:
            res = func(params)

        if isinstance(res, Success):
            return json.dumps({
                "jsonrpc": "2.0",
                "result": res.result,
                "id": req_id
            }).decode("utf-8")
        elif isinstance(res, Error):
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": res.code,
                    "message": res.message,
                    "data": res.data
                },
                "id": req_id
            }).decode("utf-8")
        else:
            return json.dumps({
                "jsonrpc": "2.0",
                "result": res,
                "id": req_id
            }).decode("utf-8")

    except Exception as e:
        logger.opt(
            exception=True).error(f"Error in method '{method_name}': {e}")
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e),
            },
            "id": req_id
        }).decode("utf-8")


async def async_dispatch(request_str: str,
                         methods: Optional[ServerMethods] = None) -> str:
    """Dispatch a JSON-RPC request string to the appropiate method."""

    method_dict = methods if methods is not None else _default_methods

    try:
        req = json.loads(request_str)
    except json.JSONDecodeError:
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32700,
                "message": "Parse error"
            },
            "id": None
        }).decode("utf-8")

    if not isinstance(req, dict):
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32600,
                "message": "Invalid Request"
            },
            "id": None
        }).decode("utf-8")

    req_id = req.get("id")
    method_name = req.get("method")

    if not isinstance(method_name, str) or method_name not in method_dict:
        err_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": "Method not found"
            },
            "id": req_id
        }
        return json.dumps(err_response).decode("utf-8")

    func = method_dict[method_name]
    params = req.get("params", [])
    if params is None:
        params = []

    try:
        if isinstance(params, dict):
            res = await func(**params)
        elif isinstance(params, list):
            res = await func(*params)
        else:
            res = await func(params)

        if isinstance(res, Success):
            return json.dumps({
                "jsonrpc": "2.0",
                "result": res.result,
                "id": req_id
            }).decode("utf-8")
        elif isinstance(res, Error):
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": res.code,
                    "message": res.message,
                    "data": res.data
                },
                "id": req_id
            }).decode("utf-8")
        else:
            return json.dumps({
                "jsonrpc": "2.0",
                "result": res,
                "id": req_id
            }).decode("utf-8")

    except Exception as e:
        logger.opt(
            exception=True).error(f"Error in method '{method_name}': {e}")
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            },
            "id": req_id
        }).decode("utf-8")


def request(method_name: str, params: Any = None) -> dict[str, Any]:
    """Builds a JOSN-RPC request payload."""
    req = {"jsonrpc": "2.0", "method": method_name, "id": str(uuid.uuid4())}
    if params is not None:
        req["params"] = params
    return req


def parse(response_dict: dict[str, Any]) -> Union[Ok, JsonRpcError]:
    """Parse a JSON-RPC request payload into an Ok or JsonRpcError"""
    if "error" in response_dict:
        err = response_dict["error"]
        return JsonRpcError(err.get("code"), err.get("message"),
                            err.get("data"), response_dict.get("id"))
    return Ok(response_dict.get("result"), response_dict.get("id"))
