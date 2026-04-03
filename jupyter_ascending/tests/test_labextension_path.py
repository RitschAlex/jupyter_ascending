#!/usr/bin/env python
# coding: utf-8


def test_labextension_path():
    from jupyter_ascending.labextension import _jupyter_labextension_paths

    path = _jupyter_labextension_paths()

    assert len(path) == 1
    assert isinstance(path[0], dict)

    entry = path[0]
    assert entry["section"] == "notebook"
    assert entry["src"] == "labextension/dist"
    assert entry["dest"] == "jupyter_ascending"
    assert entry["require"] == "jupyter_ascending/extension"
