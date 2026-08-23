import os
from unittest import mock

import pytest

from jupyter_ascending._environment import _get_sync_extension
from jupyter_ascending.errors import UnableToFindNotebookException
from jupyter_ascending.handlers.server_extension import _clear_registered_servers
from jupyter_ascending.handlers.server_extension import _make_url
from jupyter_ascending.handlers.server_extension import get_server_for_notebook
from jupyter_ascending.handlers.server_extension import register_notebook_server


@pytest.mark.parametrize(
    "env_value, expected",
    [
        (None, "sync"),
        ("custom", "custom"),
        ("my-ext_1", "my-ext_1"),
        ("", "sync"),
        ("foo.bar", "sync"),
        ("foo bar", "sync"),
        ("foo/bar", "sync"),
    ],
)
def test_get_sync_extension(env_value, expected):
    with mock.patch.dict(os.environ, {}, clear=True):
        if env_value is not None:
            os.environ["JUPYTER_ASCENDING_SYNC_EXTENSION"] = env_value
        assert _get_sync_extension() == expected


@pytest.mark.asyncio
async def test_custom_sync_extension_server_matching(monkeypatch):
    monkeypatch.setattr(
        "jupyter_ascending.handlers.server_extension.SYNC_EXTENSION", "custom")
    _clear_registered_servers()
    await register_notebook_server("/home/tj/git/notebook.custom.ipynb", 1234)
    assert (get_server_for_notebook("/home/tj/git/notebook.custom.py") ==
            _make_url(1234))
    with pytest.raises(UnableToFindNotebookException):
        get_server_for_notebook("/home/tj/git/notebook.sync.py")
