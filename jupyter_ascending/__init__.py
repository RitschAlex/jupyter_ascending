#!/usr/bin/env python
# coding: utf-8

# Copyright (c) tjdevries.
# Distributed under the terms of the Modified BSD License.

from jupyter_ascending._version import __version__
from jupyter_ascending.extension import load_ipython_extension
from jupyter_ascending.extension import load_jupyter_server_extension
from jupyter_ascending.nbextension import _jupyter_nbextension_paths
from jupyter_ascending.labextension import _jupyter_labextension_paths
from jupyter_ascending.extension import _load_jupyter_server_extension

# def _jupyter_server_extension_paths():
#     return [{
#         "module": "jupyter_ascending",
#     }]


def _jupyter_server_extension_points():
    return [{
        "module": "jupyter_ascending",
    }]


__all__ = [
    "__version__",
    "_jupyter_nbextension_paths",
    "_jupyter_labextension_paths",
    "load_ipython_extension",
    # "_jupyter_server_extension_paths",
    "_jupyter_server_extension_points",
    "load_jupyter_server_extension",
    "_load_jupyter_server_extension",
]
