import json
import uuid

from loguru import logger  # type: ignore
from functools import wraps
from typing import Any, Callable, Optional


def _wrap_request(f: Callable, start_msg: str, close_msg: str):

    @wraps(f)
    @logger.catch
    def wrapper(*args, **kwargs):
        logger.debug("{}: {}", start_msg, f.__name__)
        result = f(*args, **kwargs)
        logger.debug("{}: {}", close_msg, result)
        return result

    return wrapper


class ServerMethods:
    """
    Wrapper to make some things a bit nicer around jsonrpcserver.methods.Methods

    Basically our own version of jsonrpcserver.methods.Methods, wrapping each method with auto
    logging and error catching so that you don't have to remember to do that.
    """

    def __init__(self, start_msg: str, close_msg: str):
        self.items = {}
        self.start_msg = start_msg
        self.close_msg = close_msg

    def add(self, f: Callable) -> Callable:
        self.items[f.__name__] = f

        return _wrap_request(f, self.start_msg, self.close_msg)

    def __getitem__(self, method_name: str) -> Callable:
        return self.items[method_name]

    def __contains__(self, method_name: str) -> bool:
        return method_name in self.items


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


_methods = ServerMethods("JSON-RPC start", "JSON-RPC end")


def method(func: Callable) -> Callable:
    """Decorator to register a function as a JSON-RPC method."""
    # _methods[func.__name__] = func
    _methods.add(func)
    return func


def dispatch(request_str: str, methods: Optional[ServerMethods] = None) -> str:
    method_dict = methods if methods is not None else _methods

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
        })

    if not isinstance(req, dict):
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32600,
                "message": "Invalid Request"
            },
            "id": None
        })

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
        return json.dumps(err_response)

    func = method_dict[method_name]
    params = req.get("params", [])

    try:
        if isinstance(params, dict):
            res = func(**params)
        elif isinstance(params, list):
            res = func(*params)
        else:
            res = func(params)

        if isinstance(res, Success):
            return json.dumps({
                "jsopn_rpc": "2.0",
                "result": res.result,
                "id": req_id
            })
        elif isinstance(res, Error):
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": res.code,
                    "message": res.message,
                    "data": res.data
                },
                "req_id": req_id
            })
        else:
            return json.dumps({"jsonrpc": "2.0", "result": res, "id": req_id})

    except Exception as e:
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e),
            },
            "id": req_id
        })


async def async_dispatch(request_str: str,
                         methods: Optional[ServerMethods] = None) -> str:
    """Dispatch a JSON-RPC request string to the appropiate method."""

    method_dict = methods if methods is not None else _methods

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
        })

    if not isinstance(req, dict):
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32600,
                "message": "Invalid Request"
            },
            "id": None
        })

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
        return json.dumps(err_response)

    func = method_dict[method_name]
    params = req.get("params", [])

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
            })
        elif isinstance(res, Error):
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": res.code,
                    "message": res.message,
                    "data": res.data
                },
                "id": req_id
            })
        else:
            return json.dumps({"jsonrpc": "2.0", "result": res, "id": req_id})

    except Exception as e:
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            },
            "id": req_id
        })


class Ok:

    def __init__(self, result: Any, id: Any):
        self.result = result
        self.id = id


class JsonRpcError:

    def __init__(self, code: int, message: str, data: Any, id: Any):
        self.code = code
        self.message = message
        self.data = data
        self.id = id


def request(method_name: str, params: Any = None) -> dict[str, Any]:
    """Builds a JOSN-RPC request payload."""
    req = {"jsonrpc": "2.0", "method": method_name, "id": str(uuid.uuid4())}
    if params is not None:
        req["params"] = params
    return req


def parse(response_dict: dict[str, Any]) -> Ok | JsonRpcError:
    """Parse a JSON-RPC request payload into an Ok or JsonRpcError"""
    if "error" in response_dict:
        err = response_dict["error"]
        return JsonRpcError(err.get("code"), err.get("message"),
                            err.get("data"), response_dict.get("id"))
    return Ok(response_dict.get("result"), response_dict.get("id"))
