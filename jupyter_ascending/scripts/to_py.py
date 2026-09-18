"""
Convert a .ipynb (or .<SYNC_EXTENSION>.ipynb) file to its paird .py file.

If the file lacks the sync extension (e.g. example.ipynb) it is renamed to
add it (example.sync.ipynb) and the file is written as example.sync.py.
Pass --no-sync to keep the original filename (example.ipynb -> example.py).

Equivalent to running `jupytext --to py:percent <file>`.
"""

import argparse
from pathlib import Path

import jupytext

from jupyter_ascending._environment import SYNC_EXTENSION


def convert_to_py(filename: str, add_sync_extension: bool, force: bool):
    path = Path(filename)
    assert path.suffix == ".ipynb", "filename must end with .ipynb"
    assert path.exists(), f"File '{filename}' does not exist"

    is_paired = path.name.endswith(f".{SYNC_EXTENSION}.ipynb")
    ipynb_path = path if (is_paired or not add_sync_extension
                          ) else path.with_name(path.stem +
                                                f".{SYNC_EXTENSION}.ipynb")
    output_path = ipynb_path.with_suffix(".py")

    if not force and output_path.exists():
        print(
            f"Path '{output_path}' already exists. Call with --force to override"
        )
        return

    if not is_paired and add_sync_extension:
        if not force and ipynb_path.exists():
            print(
                f"Path '{ipynb_path}' already exists. Call with --force to override"
            )
            return
        print(f"Renaming '{path}' to '{ipynb_path}'")
        path.rename(ipynb_path)

    notebook = jupytext.read(ipynb_path)
    print(f"Writing notebook to '{output_path}'")
    jupytext.write(notebook, output_path, fmt="py:percent")
    print("Successfully converted to .py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filename",
        help="Path to the .py file to convert to .ipynb",
    )
    parser.add_argument(
        "--no-sync",
        default=False,
        action="store_true",
        help=
        "Keep the original filename (e.g. example.ipynb -> example.py) instead of renaming to add the sync extension "
        f"'.{SYNC_EXTENSION}'")
    parser.add_argument("-f",
                        "--force",
                        default=False,
                        action="store_true",
                        help="Override existing files if passed.")

    arguments = parser.parse_args()
    convert_to_py(arguments.filename, not arguments.no_sync, arguments.force)
