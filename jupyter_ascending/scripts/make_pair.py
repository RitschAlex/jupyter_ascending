"""
Make a pair of empty .<SYNC_EXTENSION>.py and .<SYNC_EXTENSION>.ipynb files.
"""
import argparse
from pathlib import Path

import jupytext

from jupyter_ascending._environment import SYNC_EXTENSION
from jupyter_ascending.scripts._metadata import METADATA_HEADER

_STARTER_CONTENTS = METADATA_HEADER + "\n# %%\n"


def create_new_file(base: str, force: bool):
    sync_extension = SYNC_EXTENSION
    assert not base.endswith(".py"), "base: Cannot end with '.py'"
    assert not base.endswith(
        f".{sync_extension}.py"
    ), f"base: Cannot end with '{sync_extension}.py' -- we're adding that!"
    assert not base.endswith(".ipynb"), "base: Cannot end with '.ipynb'"
    assert not base.endswith(
        f".{sync_extension}.ipynb"
    ), "base: Cannot end with '.ipynb' -- we're adding that!"
    assert not base.endswith(
        f".{sync_extension}"), f"we're going to add '.{sync_extension}'"

    py_path = base + f".{sync_extension}.py"
    ipynb_path = base + f".{sync_extension}.ipynb"

    if not force and Path(py_path).exists():
        print(
            f"Path '{py_path}' already exists. Call with --force to override.")
        return

    if not force and Path(ipynb_path).exists():
        print(
            f"Path '{ipynb_path}' already exists. Call with --force to override."
        )
        return

    with open(py_path, "w") as f:
        print("Writing :", py_path)
        f.write(_STARTER_CONTENTS)

    print("Writing :", ipynb_path)
    jupytext.write(jupytext.reads(_STARTER_CONTENTS, "py:percent"), ipynb_path)

    print("Success!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base",
        help="Base filename to add (do not include .py or .ipynb)",
        required=True)
    parser.add_argument("-f",
                        "--force",
                        help="Override existing files if passed.",
                        default=False,
                        action="store_true",
                        required=False)

    arguments = parser.parse_args()

    create_new_file(arguments.base, arguments.force)
