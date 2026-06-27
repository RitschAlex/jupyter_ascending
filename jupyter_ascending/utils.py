import json
import os
import socket
import urllib.request
import urllib.error
from contextlib import closing

import ipykernel  # type: ignore
from loguru import logger
from jupyter_server import serverapp as notebookapp  # type: ignore


def get_name_from_python():
    """
    Returns the absolute path of the Notebook or None if it cannot be determined

    NOTE: works only when the security is token-based or there is also no password
    """
    connection_file = os.path.basename(ipykernel.get_connection_file())
    kernel_id = connection_file.split("-", 1)[1].split(".")[0]

    for srv in notebookapp.list_running_servers():
        is_abs_root = os.path.isabs(srv["root_dir"])
        if not is_abs_root:
            logger.warning("Skipping server %s: root_dir is not absolute (%s)",
                           srv.get("url"), srv.get("root_dir"))
            continue
        try:
            params = {"token": srv.get("token", "")}
            url = srv["url"] + "api/sessions?" + urllib.parse.urlencode(params)
            with urllib.request.urlopen(url) as req:
                sessions = json.load(req)

            for sess in sessions:
                if sess["kernel"]["id"] == kernel_id:
                    return os.path.join(srv["root_dir"],
                                        sess["notebook"]["path"])

        except (urllib.error.URLError, ValueError, KeyError) as e:
            logger.warning("Skipping server %s: %s", srv.get("url"), e)

    return None


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("localhost", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
