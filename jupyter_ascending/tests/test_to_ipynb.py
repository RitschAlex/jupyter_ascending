import subprocess
import sys
from pathlib import Path

import jupytext
import pytest

from jupyter_ascending.scripts._metadata import METADATA_HEADER
from jupyter_ascending.scripts.to_ipynb import convert_to_ipynb

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = "x = 1\ny = 2\n"


def _read_cells(path: Path) -> list[str]:
    return [cell.source.strip() for cell in jupytext.read(path).cells]


def _run_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "jupyter_ascending.scripts.to_ipynb", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True)


def test_convert_to_ipynb_unpaired_py_without_header(tmp_path):
    py_path = tmp_path / "example.py"
    py_path.write_text(SOURCE)

    convert_to_ipynb(str(py_path), True, False)

    assert not py_path.exists()
    paired_py = tmp_path / "example.sync.py"
    assert paired_py.exists()
    assert paired_py.read_text().startswith(METADATA_HEADER)
    assert SOURCE in paired_py.read_text()
    assert _read_cells(tmp_path / "example.sync.ipynb") == ["x = 1\ny = 2"]


def test_convert_to_ipynb_py_with_header_not_duplicated(tmp_path):
    content_with_header = METADATA_HEADER + "# %%\nprint(1)\n"
    py_path = tmp_path / "example.py"
    py_path.write_text(content_with_header)

    convert_to_ipynb(str(py_path), True, False)

    paired_py = tmp_path / "example.sync.py"
    assert paired_py.read_text().count("jupytext:") == 1
    assert _read_cells(tmp_path / "example.sync.ipynb") == ["print(1)"]


def test_convert_to_ipynb_no_sync_keeps_filename(tmp_path):
    py_path = tmp_path / "example.py"
    py_path.write_text(SOURCE)

    convert_to_ipynb(str(py_path), False, False)

    assert py_path.exists()
    assert py_path.read_text().startswith(METADATA_HEADER)
    assert _read_cells(tmp_path / "example.ipynb") == ["x = 1\ny = 2"]


def test_convert_to_ipynb_already_paired_py(tmp_path):
    content_with_header = METADATA_HEADER + "# %%\nprint(1)\n"
    py_path = tmp_path / "example.sync.py"
    py_path.write_text(content_with_header)

    convert_to_ipynb(str(py_path), True, False)

    assert py_path.exists()
    assert not (tmp_path / "example.py").exists()
    assert _read_cells(tmp_path / "example.sync.ipynb") == ["print(1)"]


def test_convert_to_ipynb_existing_output_without_force(tmp_path):
    py_path = tmp_path / "example.py"
    py_path.write_text(SOURCE)
    output_path = tmp_path / "example.sync.ipynb"
    output_path.write_text("SENTINEL")

    convert_to_ipynb(str(py_path), True, False)

    assert py_path.exists()
    assert py_path.read_text() == SOURCE
    assert output_path.read_text() == "SENTINEL"


def test_convert_to_ipynb_existing_output_with_force(tmp_path):
    py_path = tmp_path / "example.py"
    py_path.write_text(SOURCE)
    output_path = tmp_path / "example.sync.ipynb"
    output_path.write_text("SENTINEL")

    convert_to_ipynb(str(py_path), True, True)

    assert not py_path.exists()
    assert _read_cells(output_path) == ["x = 1\ny = 2"]


def test_convert_to_ipynb_custom_sync_extension(tmp_path, monkeypatch):
    monkeypatch.setattr("jupyter_ascending.scripts.to_ipynb.SYNC_EXTENSION",
                        "custom")
    py_path = tmp_path / "example.py"
    py_path.write_text(SOURCE)

    convert_to_ipynb(str(py_path), True, False)

    assert not py_path.exists()
    assert (tmp_path / "example.custom.py").exists()
    assert (tmp_path / "example.custom.ipynb").exists()


def test_convert_to_ipynb_non_py_filename(tmp_path):
    with pytest.raises(AssertionError):
        convert_to_ipynb(str(tmp_path / "example.ipynb"), True, False)


def test_convert_to_ipynb_nonexistent_file(tmp_path):
    with pytest.raises(AssertionError):
        convert_to_ipynb(str(tmp_path / "missing.py"), True, False)


def test_convert_to_ipynb_cli_default(tmp_path):
    py_path = tmp_path / "example.py"
    py_path.write_text(SOURCE)

    result = _run_cli(tmp_path, str(py_path))

    assert result.returncode == 0
    assert "Successfully converted" in result.stdout
    assert not py_path.exists()
    paired_py = tmp_path / "example.sync.py"
    assert paired_py.read_text().startswith(METADATA_HEADER)
    assert _read_cells(tmp_path / "example.sync.ipynb") == ["x = 1\ny = 2"]


def test_convert_to_ipynb_cli_no_sync(tmp_path):
    py_path = tmp_path / "example.py"
    py_path.write_text(SOURCE)

    result = _run_cli(tmp_path, str(py_path), "--no-sync")

    assert result.returncode == 0
    assert py_path.exists()
    assert py_path.read_text().startswith(METADATA_HEADER)
    assert (tmp_path / "example.ipynb").exists()


def test_convert_to_ipynb_cli_force_override(tmp_path):
    py_path = tmp_path / "example.py"
    py_path.write_text(SOURCE)
    output_path = tmp_path / "example.sync.ipynb"
    output_path.write_text("SENTINEL")

    result = _run_cli(tmp_path, str(py_path))
    assert result.returncode == 0
    assert "already exists" in result.stdout
    assert output_path.read_text() == "SENTINEL"

    result_force = _run_cli(tmp_path, str(py_path), "--force")
    assert result.returncode == 0
    assert _read_cells(output_path) == ["x = 1\ny = 2"]


def test_convert_to_ipynb_cli_no_sync_existing_output(tmp_path):
    py_path = tmp_path / "example.py"
    py_path.write_text(SOURCE)
    output_path = tmp_path / "example.ipynb"
    output_path.write_text("SENTINEL")

    result = _run_cli(tmp_path, str(py_path), "--no-sync")
    assert result.returncode == 0
    assert "already exists" in result.stdout
    assert output_path.read_text() == "SENTINEL"
