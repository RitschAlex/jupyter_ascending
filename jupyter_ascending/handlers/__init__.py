from loguru import logger  # type: ignore
from http.server import BaseHTTPRequestHandler

from ..jsonrpc_utils import ServerMethods
from ..jsonrpc_utils import dispatch


def generate_request_handler(
        name: str, methods: ServerMethods) -> type[BaseHTTPRequestHandler]:
    """Build a handler to respond to HTTP POST requests containing JSON-RPC messages.

    Will call jsonrpcserver.dispatch to dispatch the request to the appropriate handler.

    TODO: why this weird construction vs a simple subclass?
        - to be able to specify a custom class name, i think. but why do we need that?
    """

    @logger.catch
    def do_POST(self):
        # Process request
        request = self.rfile.read(int(self.headers["Content-Length"])).decode()
        logger.info("{} processing request:\n\t\t{}", name, request)

        # Dispatch the RPC request to the right function and get the function's response.
        response = dispatch(request, methods=methods)

        logger.info("Got Response:\n\t\t{}", response)

        # Return response
        self.send_response(200 if response else 204)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(str(response).encode())

    def log_message(self, format, *args):
        logger.debug(args)

    return type(
        f"{name}RequestHandler",
        (BaseHTTPRequestHandler, ),
        {
            "allow_reuse_address": True,
            "do_POST": do_POST,
            "log_message": log_message
        },
    )
