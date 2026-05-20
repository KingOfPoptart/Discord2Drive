"""
End-to-end integration test: runs the full pipeline via main.py.

Fails with setup instructions if any required config is absent.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from drive_client import build_service

TEST_DRIVE_PATH = "discord2drive-test/e2e"
_DOC_MIME = "application/vnd.google-apps.document"
_FOLDER_MIME = "application/vnd.google-apps.folder"


def _find_file(service, name: str, parent_id: str, mime: str) -> str | None:
    results = (
        service.files()
        .list(
            q=f"name = '{name}' and '{parent_id}' in parents "
              f"and mimeType = '{mime}' and trashed = false",
            fields="files(id)",
        )
        .execute()
    )
    files = results.get("files", [])
    return files[0]["id"] if files else None


@pytest.fixture(scope="session", autouse=True)
def cleanup_e2e_doc(google_client_config, google_token_path):
    yield
    service = build_service(google_client_config, google_token_path)
    test_root_id = _find_file(service, "discord2drive-test", "root", _FOLDER_MIME)
    if not test_root_id:
        return
    doc_id = _find_file(service, "e2e", test_root_id, _DOC_MIME)
    if doc_id:
        service.files().delete(fileId=doc_id).execute()
        print("\nCleaned up discord2drive-test/e2e doc")


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "main", *args],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )


# --- default auto-parse-pcs behavior ---

def test_default_auto_parse(test_thread_url):
    result = _run(test_thread_url)
    assert result.returncode == 0, result.stderr
    assert "Found PCs:" in result.stdout
    assert "docs.google.com" in result.stdout


def test_rerun_overwrites_tab(test_thread_url):
    first = _run(test_thread_url)
    assert first.returncode == 0, first.stderr
    second = _run(test_thread_url)
    assert second.returncode == 0, second.stderr
    assert "docs.google.com" in second.stdout


# --- --disable-parse-pcs with explicit paths ---

def test_explicit_path_upload(test_thread_url):
    result = _run(test_thread_url, "--disable-parse-pcs", TEST_DRIVE_PATH)
    assert result.returncode == 0, result.stderr
    assert "docs.google.com" in result.stdout


def test_output_local_with_drive_path(test_thread_url, tmp_path):
    result = _run(test_thread_url, "--disable-parse-pcs", TEST_DRIVE_PATH,
                  "--output-local", str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "docs.google.com" in result.stdout
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].suffix == ".md"


# --- dry run and local output ---

def test_dry_run_prints_transcript(test_thread_url):
    result = _run(test_thread_url, "--dry-run")
    assert result.returncode == 0
    assert "# " in result.stdout
    assert "**" in result.stdout


def test_output_local_saves_file(test_thread_url, tmp_path):
    result = _run(test_thread_url, "--output-local", str(tmp_path), "--dry-run")
    assert result.returncode == 0
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].suffix == ".md"
    assert "# " in files[0].read_text()


def test_output_local_with_dry_run_also_prints(test_thread_url, tmp_path):
    result = _run(test_thread_url, "--output-local", str(tmp_path), "--dry-run")
    assert result.returncode == 0
    assert "# " in result.stdout
    assert len(list(tmp_path.iterdir())) == 1


# --- error cases ---

def test_explicit_path_without_disable_flag_errors(test_thread_url):
    result = _run(test_thread_url, "some/path")
    assert result.returncode == 2
    assert "disable-parse-pcs" in result.stderr


def test_single_segment_path_errors(test_thread_url):
    result = _run(test_thread_url, "--disable-parse-pcs", "NoSlashHere")
    assert result.returncode == 2
    assert "folder" in result.stderr.lower()


def test_disable_parse_without_destination_errors(test_thread_url):
    result = _run(test_thread_url, "--disable-parse-pcs")
    assert result.returncode == 2


def test_missing_thread_url_exits_with_error():
    result = _run()
    assert result.returncode == 2


def test_invalid_url_exits_cleanly():
    result = _run("https://example.com/not-discord", "--dry-run")
    assert result.returncode == 1
    assert "Unrecognised" in result.stderr
