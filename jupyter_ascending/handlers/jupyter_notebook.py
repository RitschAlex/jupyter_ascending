"""
This file contains code for the JSON-RPC server we run alongside each .sync.ipynb notebook.

It receives messages from `jupyter_server.py` and takes the appropriate action in the notebook.
"""

import queue
import threading
from http.server import HTTPServer
from inspect import signature
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

import jupytext  # type: ignore
import requests  # type: ignore
from ipykernel.comm import Comm  # type: ignore
from ..jsonrpc_utils import Success, Result
from ..jsonrpc_utils import request
from loguru import logger  # type: ignore

from jupyter_ascending._environment import EXECUTE_HOST_URL
from jupyter_ascending.handlers import ServerMethods
from jupyter_ascending.handlers import generate_request_handler
from jupyter_ascending.handlers.server_extension import register_notebook_server
from jupyter_ascending.json_requests import ExecuteAllRequest
from jupyter_ascending.json_requests import ExecuteRequest
from jupyter_ascending.json_requests import FocusCellRequest
from jupyter_ascending.json_requests import GetStatusRequest
from jupyter_ascending.json_requests import RestartRequest
from jupyter_ascending.json_requests import SyncRequest
from jupyter_ascending.notebook.data_types import JupyterCell
from jupyter_ascending.notebook.data_types import NotebookContents
from jupyter_ascending.notebook.merge import OpCodeAction
from jupyter_ascending.notebook.merge import OpCodes
from jupyter_ascending.notebook.merge import opcode_merge_cell_contents
from jupyter_ascending.utils import find_free_port

COMM_NAME = "AUTO_SYNC::notebook"

merge_complete = threading.Event()
lock = threading.Lock()

notebook_server_methods = ServerMethods("JupyterNotebook Start",
                                        "JupyterNotebook Close")

notebook_start_locks = {}
notebook_start_locks_guard = threading.Lock()
active_notebook_servers = {}


class ReadyHTTPServer(HTTPServer):
    """HTTPServer that sets a threading.Event when it is ready to accept requests."""

    def __init__(self, server_address, request_handler, ready_event):
        self.ready_event = ready_event
        super().__init__(server_address, request_handler)

    def serve_forever(self, poll_interval=0.5):
        self.ready_event.set()  # Signal that the server is ready
        return super().serve_forever(poll_interval)


def _get_notebook_start_lock(notebook_path: Path):
    with notebook_start_locks_guard:
        lock_test = notebook_start_locks.get(notebook_path)
        if lock_test is None:
            lock_test = threading.Lock()
            notebook_start_locks[notebook_path] = lock
        return lock


def _close_notebook_server(server, server_thread):
    try:
        if server_thread is not None and server_thread.is_alive():
            server.shutdown()
            server_thread.join()  # Wait for the server thread to finish
    finally:
        server.server_close()


@logger.catch
def start_notebook_server_in_thread(notebook_name: str):
    """
    Args:
        notebook_name: The name of the notebook you want to be syncing in this process.
    """

    logger.info("IPYTHON: Starting notebook server for {}...", notebook_name)
    print("IPYTHON: Starting notebook server for {}...", notebook_name)

    notebook_path = Path(notebook_name).absolute()
    start_lock = _get_notebook_start_lock(notebook_path)

    with start_lock:
        existing = active_notebook_servers.get(notebook_path)
        if existing is not None:
            existing_server, existing_thread = existing

            if existing_thread.is_alive():
                logger.info(
                    "IPYTHON: Notebook server for {} is already running.",
                    notebook_path)
                return

            # The old serving thread exited, so discard its stale state.
            active_notebook_servers.pop(notebook_path, None)
            existing_server.server_close()

        ready_event = threading.Event()
        serve_errors = queue.Queue(maxsize=1)

        notebook_executor = ReadyHTTPServer(
            ("localhost", 0), NotebookKernelRequestHandler, ready_event)
        notebook_server_port = notebook_executor.server_address[1]

        def serve():
            try:
                notebook_executor.serve_forever()
            except BaseException as e:
                serve_errors.put(e)
                ready_event.set()
                raise

        notebook_executor_thread = threading.Thread(
            target=serve, name=f"notebook-server-{notebook_path.name}")

        try:
            notebook_executor_thread.start()

            # Registration of the notebook server with the main server should happen
            # after the server is ready to accept requests.
            ready_event.wait()

            try:
                serve_error = serve_errors.get_nowait()
            except queue.Empty:
                serve_error = None

            if serve_error is not None:
                raise serve_error

            server_state = (notebook_executor, notebook_executor_thread)

            logger.info("IPYTHON: Notebook server for {} started on port {}.",
                        notebook_path, notebook_server_port)
            print(
                f"IPYTHON: Notebook server for {notebook_path} started on port {notebook_server_port}."
            )

            registration_json = request(register_notebook_server.__name__,
                                        params={
                                            "notebook_path":
                                            str(notebook_path),
                                            "port_number": notebook_server_port
                                        })

            logger.info(
                "Registering notebook path={!r}, port={}, url={!r}",
                str(notebook_path),
                notebook_server_port,
                EXECUTE_HOST_URL,
            )

            response = requests.post(
                EXECUTE_HOST_URL,
                json=registration_json,
                timeout=10,
            )

            logger.info(
                "Registration response: status={}, body={!r}",
                response.status_code,
                response.text,
            )

            response.raise_for_status()

            logger.info("==> Success")

            active_notebook_servers[notebook_path] = server_state

        except BaseException:
            state = active_notebook_servers.get(notebook_path)
            if state is not None and state[0] is notebook_executor:
                active_notebook_servers.pop(notebook_path, None)

            _close_notebook_server(notebook_executor, notebook_executor_thread)
            raise


def dispatch_json_request(f):
    """
    A kinda weird decorator attempting to remove some boilerplate in the following funcs.
    Automatically dispatch a json request based on the request_type.

    Adds it to notebook_server_methods
    """

    # Get the type from the first argument of the function.
    #   This will define the name that we use to generate the method handling.
    request_type = signature(
        f).parameters["request_type"].annotation.__args__[0]

    def wrapped(data: Dict) -> Result:
        return Success(f(request_type, data))

    wrapped.__name__ = request_type.__name__

    return notebook_server_methods.add(wrapped)


@dispatch_json_request
def handle_execute_request(request_type: Type[ExecuteRequest],
                           data: dict) -> str:
    """JSON-RPC request handler for 'execute cell'"""
    request = request_type(**data)

    comm = make_comm()
    execute_cell_contents(comm, request.cell_index)

    return f"Executing cell `{request.cell_index}`"


@dispatch_json_request
def handle_execute_all_request(request_type: Type[ExecuteAllRequest],
                               data: dict) -> str:
    """JSON-RPC request handler for 'execute all cells'"""
    request = request_type(**data)

    # TODO: Remind myself why I don't need to say the filename here...
    with lock:
        comm = make_comm()
        execute_all_cells(comm)

    return f"Executing all cells in {request.file_name}"


@dispatch_json_request
def handle_sync_request(request_type: Type[SyncRequest], data: dict) -> str:
    """JSON-RPC request handler for 'sync'"""

    request = request_type(**data)

    # We lock here because updating the notebook isn't threadsafe.
    # If we got two sync requests simultaneously without a lock,
    # bad things might happen (eg duplicated inserts/deletes).
    with lock:
        merge_complete.clear()
        comm = make_comm()

        result = jupytext.reads(request.contents, fmt="py:percent")
        update_cell_contents(comm, result)

    return "Syncing all cells"


@dispatch_json_request
def handle_focus_cell_request(request_type: Type[FocusCellRequest],
                              data: dict) -> str:
    """JSON-RPC request handler for 'focus cell'"""
    request = request_type(**data)

    print(request)
    raise NotImplementedError


@dispatch_json_request
def handle_get_status_request(request_type: Type[GetStatusRequest],
                              data: dict) -> str:
    """JSON-RPC request handler for 'get status'"""
    logger.info("Attempting get_status")

    comm = make_comm()
    comm.send({"command": "get_status"})

    logger.info("Sent get_status")

    return f"Updating status"


@dispatch_json_request
def handle_restart_request(request_type: Type[RestartRequest],
                           data: dict) -> str:
    """JSON-RPC request handler for 'restart'"""
    request = request_type(**data)

    comm = make_comm()
    comm.send({"command": "restart_kernel"})
    logger.info("Sent restart_kernel")

    return f"Restarting kernel in {request.file_name}"


NotebookKernelRequestHandler = generate_request_handler(
    "NotebookKernel", notebook_server_methods)


def make_comm():
    """A comm is a Jupyter object for communicating between a notebook and kernel.

    Set up this object with event handlers."""

    logger.info("IPYTHON: Registering Comms")

    comm_target_name = COMM_NAME

    jupyter_comm = Comm(target_name=comm_target_name)

    def _get_command(msg) -> Optional[str]:
        return msg["content"]["data"].get("command", None)

    @jupyter_comm.on_msg
    def _recv(msg):
        if _get_command(msg) == "merge_notebooks":
            logger.info("GOT UPDATE STATUS")
            merge_notebooks(jupyter_comm, msg["content"]["data"])
            return

        if _get_command(msg) == "merge_complete":
            logger.info("GOT MERGE COMPLETE")
            merge_complete.set()
            return

        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        logger.info(msg)
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    logger.info("==> Success")

    return jupyter_comm


def update_cell_contents(comm: Comm, result: Dict[str, Any]) -> None:
    # logger.info(Javascript("Jupyter.notebook.get_cells()"))
    def _transform_jupytext_cells(jupytext_cells) -> List[Dict[str, Any]]:
        """TODO: what does this do?"""
        return [{
            "index": i,
            "output": [],
            **{
                k: v
                for (k, v) in x.items() if k not in {"outputs", "metadata"}
            }
        } for i, x in enumerate(result["cells"])]

    comm.send({
        "command": "start_sync_notebook",
        "cells": _transform_jupytext_cells(result["cells"])
    })

    # Wait for the merge_complete flag to get set in the callback.
    # This way we don't release the lock before syncing is done.
    if not merge_complete.wait(timeout=5.0):
        logger.warning("Timed out waiting for syncing to complete.")


def get_output_text(javascript_cell) -> Optional[str]:
    """Get cell output or return None if no output?"""
    output_tuple = javascript_cell.get("outputs", tuple())
    if not output_tuple:
        return None

    output = output_tuple[0]

    if output.get("data", None):
        data = output["data"]

        if isinstance(data, dict):
            if data.get("text/plain", None):
                return data["text/plain"]

    if output.get("text", None):
        return output["text"]

    return None


@logger.catch(reraise=True)
def merge_notebooks(comm: Comm, result: Dict[str, Any]) -> None:
    javascript_cells = result["javascript_cells"]
    current_notebook = NotebookContents(cells=[
        JupyterCell(
            index=i,
            cell_type=x["cell_type"],
            source=x["source"],
            output=get_output_text(x),
            # metadata=x["metadata"],
        ) for i, x in enumerate(javascript_cells)
    ])

    new_notebook = NotebookContents(
        cells=[JupyterCell(**x) for x in result["new_notebook"]])

    opcodes = opcode_merge_cell_contents(current_notebook, new_notebook)
    logger.info("Performing Opcodes...")
    logger.info(opcodes)

    net_shift = 0
    for op_action in opcodes:
        net_shift = perform_op_code(comm, op_action, current_notebook,
                                    new_notebook, net_shift)

    logger.info("sending finish_merge command")
    comm.send({"command": "finish_merge"})


def perform_op_code(
    comm: Comm,
    op_action: OpCodeAction,
    current_notebook: NotebookContents,
    updated_notebook: NotebookContents,
    net_shift: int,
) -> int:
    """
    net_shift (int): Tracks the net shift of previous op codes since we can't apply all the operations at the same time to jupyter,
                        since it does not have that kind of editting model.

                        So what we do is make sure that as we delete and insert, we keep track of the shifts that have happened thus far.
                        Given this shift, we will shift the actions that we tell Jupyter notebook to do.
    """

    if op_action.op_code == OpCodes.EQUAL:
        pass

    elif op_action.op_code == OpCodes.DELETE:
        logger.info(f"Performing Delete: {op_action}")

        # Since deletion is a bit goofy for jupyter, so it has to be adjusted by net shift thus far.
        cells_to_delete = [x + net_shift for x in range(*op_action.current)]
        comm.send({
            "command": "op_code__delete_cells",
            "cell_indices": cells_to_delete
        })

        net_shift = net_shift - len(cells_to_delete)

    elif op_action.op_code == OpCodes.INSERT:
        logger.info(f"Performing Insert: {op_action}")

        cells_to_insert = list(range(*op_action.updated))
        for cell_number in cells_to_insert:
            comm.send({
                "command":
                "op_code__insert_cell",
                "cell_number":
                cell_number,
                "cell_type":
                updated_notebook.cells[cell_number].cell_type,
                "cell_contents":
                updated_notebook.cells[cell_number].joined_source,
            })

        net_shift = net_shift + len(cells_to_insert)

    elif op_action.op_code == OpCodes.REPLACE:
        # Keep track of what the current cells looked like before.
        current_cells = list(range(*op_action.current))
        updated_cells = list(range(*op_action.updated))

        for cell_number in updated_cells:
            # If we have current cells we're replacing, do that.
            if current_cells:
                current_cells.pop(0)

                comm.send({
                    "command":
                    "op_code__replace_cell",
                    "cell_number":
                    cell_number,
                    "cell_type":
                    updated_notebook.cells[cell_number].cell_type,
                    "cell_contents":
                    updated_notebook.cells[cell_number].joined_source,
                })
            # Otherwise, we have new cells to insert so we don't overwrite existing cells
            else:
                net_shift = perform_op_code(
                    comm,
                    OpCodeAction(
                        op_code=OpCodes.INSERT,
                        # NOTE: This is intentionally the last index for both of these
                        current_start_idx=op_action.current_final_idx,
                        current_final_idx=op_action.current_final_idx,
                        updated_start_idx=cell_number,
                        updated_final_idx=cell_number + 1,
                    ),
                    current_notebook,
                    updated_notebook,
                    net_shift,
                )

        # If we have cells left over from the replace (i.e. 1-4 replaced with 1-2),
        #   then we need to delete the rest of them.
        if current_cells:
            net_shift = perform_op_code(
                comm,
                OpCodeAction(
                    op_code=OpCodes.DELETE,
                    current_start_idx=current_cells[0],
                    current_final_idx=current_cells[-1] + 1,
                    # NOTE: This is intentionally the last index for both of these
                    updated_start_idx=op_action.updated_final_idx,
                    updated_final_idx=op_action.updated_final_idx,
                ),
                current_notebook,
                updated_notebook,
                net_shift,
            )

    else:
        raise NotImplementedError

    return net_shift


def execute_cell_contents(comm: Comm, cell_number: int) -> None:
    comm.send({"command": "execute", "cell_number": cell_number})


def execute_all_cells(comm: Comm) -> None:
    comm.send({"command": "execute_all"})
