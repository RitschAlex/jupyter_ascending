import subprocess
import sys
from pathlib import Path

import jupytext
import pytest

from jupyter_ascending.scripts.to_py import convert_to_py

REPO_ROOT = Path(__file__).resolve().parents[2]

SOURCE = "# %%\nprint('Hello, world!')\n\n# %%\nprint('Goodbye, world!')\n"


def _write_ipynb_file(path: Path, text: str) -> None:
    notebook = jupytext.reads(text, fmt="py:percent")
    jupytext.write(notebook, path, fmt="ipynb")


def _read_cells(path: Path) -> list[str]:
    return [cell.source.strip() for cell in jupytext.read(path).cells]


def _run_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "jupyter_ascending.scripts.to_py", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_convert_to_py_unpaired_ipynb(tmp_path):
    ipynb_path = tmp_path / "example.ipynb"
    _write_ipynb_file(ipynb_path, SOURCE)
    convert_to_py(str(ipynb_path), True, True)

    assert not ipynb_path.exists()
    assert (tmp_path / "example.sync.ipynb").exists()
    assert _read_cells(tmp_path / "example.sync.py") == [
        "print('Hello, world!')", "print('Goodbye, world!')"
    ]


def test_convert_to_py_no_sync_keeps_filename(tmp_path):
    ipynb_path = tmp_path / "example.ipynb"
    _write_ipynb_file(ipynb_path, SOURCE)
    convert_to_py(str(ipynb_path), False, False)

    assert ipynb_path.exists()
    assert _read_cells(tmp_path / "example.py") == [
        "print('Hello, world!')", "print('Goodbye, world!')"
    ]


def test_convert_to_py_already_paired_ipynb(tmp_path):
    ipynb_path = tmp_path / "example.ipynb"
    _write_ipynb_file(ipynb_path, SOURCE)
    convert_to_py(str(ipynb_path), True, False)

    assert ipynb_path.exists()
    assert (tmp_path / "example.sync.py").exists()
    assert not (tmp_path / "example.ipynb").exists()


def test_convert_to_py_existing_output_without_force(tmp_path):
    ipynb_path = tmp_path / "example.ipynb"
    _write_ipynb_file(ipynb_path, SOURCE)
    output_path = tmp_path / "example.sync.py"
    output_path.write_text("SENTINEL = 1\n")
    convert_to_py(str(ipynb_path), True, False)

    assert ipynb_path.exists()
    assert output_path.read_text() == "SENTINEL = 1\n"


def test_convert_to_py_existing_output_with_force(tmp_path):
    ipynb_path = tmp_path / "example.ipynb"
    _write_ipynb_file(ipynb_path, SOURCE)
    output_path = tmp_path / "example.sync.py"
    output_path.write_text("SENTINEL = 1\n")
    convert_to_py(str(ipynb_path), True, False)

    assert not ipynb_path.exists()
    assert (tmp_path / "example.sync.ipynb").exists()
    assert _read_cells(output_path) == [
        "print('Hello, world!')", "print('Goodbye, world!')"
    ]


def test_convert_to_py_custom_sync_extension(tmp_path, monkeypatch):
    monkeypatch.setattr("jupyter_ascending.scripts.to_py.SYNC_EXTENSION",
                        ".custom")
    ipynb_path = tmp_path / "example.ipynb"
    _write_ipynb_file(ipynb_path, SOURCE)
    convert_to_py(str(ipynb_path), True, False)

    assert not ipynb_path.exists()
    assert (tmp_path / "example.custom.py").exists()
    assert (tmp_path / "example.custom.ipynb").exists()


def test_convert_to_py_non_ipynb_file(tmp_path):
    with pytest.raises(AssertionError):
        convert_to_py(str(tmp_path / "example.py"), True, False)


def test_convert_to_py_nonexistent_file(tmp_path):
    with pytest.raises(AssertionError):
        convert_to_py(str(tmp_path / "missing.ipynb"), True, False)


def test_convert_to_py_cli_default(tmp_path):
    ipynb_path = tmp_path / "example.ipynb"
    _write_ipynb_file(ipynb_path, SOURCE)
    result = _run_cli(tmp_path, str(ipynb_path))

    assert result.returncode == 0
    assert "Successfully converted" in result.stdout
    assert not ipynb_path.exists()
    assert (tmp_path / "example.sync.ipynb").exists()
    assert _read_cells(tmp_path / "example.sync.py") == [
        "print('Hello, world!')", "print('Goodbye, world!')"
    ]


def test_convert_to_py_cli_no_sync(tmp_path):
    ipynb_path = tmp_path / "example.ipynb"
    _write_ipynb_file(ipynb_path, SOURCE)
    result = _run_cli(tmp_path, str(ipynb_path), "--no-sync")

    assert result.returncode == 0
    assert ipynb_path.exists()
    assert (tmp_path / "example.py").exists()


def test_convert_to_py_cli_force_overrides(tmp_path):
    ipynb_path = tmp_path / "example.ipynb"
    _write_ipynb_file(ipynb_path, SOURCE)
    output_path = tmp_path / "example.sync.py"
    output_path.write_text("SENTINEL = 1\n")

    first_result = _run_cli(tmp_path, str(ipynb_path))
    assert first_result.returncode == 0
    assert "already exists" in first_result.stdout
    assert output_path.read_text() == "SENTINEL = 1\n"

    second_result = _run_cli(tmp_path, str(ipynb_path), "--force")
    assert second_result.returncode == 0
    assert _read_cells(output_path) == [
        "print('Hello, world!')", "print('Goodbye, world!')"
    ]


def test_convert_to_py_cli_no_sync_existing_output(tmp_path):
    ipynb_path = tmp_path / "example.ipynb"
    _write_ipynb_file(ipynb_path, SOURCE)
    output_path = tmp_path / "example.py"
    output_path.write_text("SENTINEL = 1\n")

    result = _run_cli(tmp_path, str(ipynb_path), "--no-sync")
    assert result.returncode == 0
    assert "already exists" in result.stdout
    assert output_path.read_text() == "SENTINEL = 1\n"
