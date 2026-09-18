"""
Convert a .py (or .<SYNC_EXTENSION>.py) file to its paird .ipynb notebook.

If the file lacks the sync extension (e.g. example.py) it is renamed to
add it (example.sync.py) and the notebook is written as example.sync.ipynb.
Pass --no-sync to keep the original filename (example.py -> example.ipynb).

Equivalent to running `jupytext --to ipynb <file>`.
"""

import argparse
from pathlib import Path

import jupytext

from jupyter_ascending._environment import SYNC_EXTENSION
from jupyter_ascending.scripts._metadata import METADATA_HEADER


def convert_to_ipynb(filename: str, add_sync_extension: bool, force: bool):
    path = Path(filename)
    assert path.suffix == ".py", "filename must end with .py"
    assert path.exists(), f"File '{filename}' does not exist"

    is_paired = path.name.endswith(f".{SYNC_EXTENSION}.py")
    py_path = path if (is_paired or not add_sync_extension
                       ) else path.with_name(path.stem +
                                             f".{SYNC_EXTENSION}.py")
    output_path = py_path.with_suffix(".ipynb")

    if not force and output_path.exists():
        print(
            f"Path '{output_path}' already exists. Call with --force to override"
        )
        return

    if not is_paired and add_sync_extension:
        if not force and py_path.exists():
            print(
                f"Path '{py_path}' already exists. Call with --force to override"
            )
            return
        print(f"Renaming '{path}' to '{py_path}'")
        path.rename(py_path)

    content = py_path.read_text()
    if not content.startswith("# ---"):
        print(f"Adding jupytext metadata header to '{py_path}'")
        py_path.write_text(METADATA_HEADER + "\n# %%\n" + content)

    notebook = jupytext.read(py_path)
    print(f"Writing notebook to '{output_path}'")
    jupytext.write(notebook, output_path, fmt="ipynb")
    print("Successfully converted to .ipynb")


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
        "Keep the original filename (e.g. example.py -> example.ipynb) instead of renaming to add the sync extension "
        f"'.{SYNC_EXTENSION}'")
    parser.add_argument("-f",
                        "--force",
                        default=False,
                        action="store_true",
                        help="Override existing files if passed.")

    arguments = parser.parse_args()
    convert_to_ipynb(arguments.filename, not arguments.no_sync,
                     arguments.force)
