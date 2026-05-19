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
_FOLDER_MIME = "application/vnd.google-apps.folder"


def _find_folder(service, name: str, parent_id: str) -> str | None:
    results = (
        service.files()
        .list(
            q=f"name = '{name}' and '{parent_id}' in parents "
              f"and mimeType = '{_FOLDER_MIME}' and trashed = false",
            fields="files(id)",
        )
        .execute()
    )
    files = results.get("files", [])
    return files[0]["id"] if files else None


@pytest.fixture(scope="session", autouse=True)
def cleanup_e2e_folder(google_client_config, google_token_path):
    yield
    service = build_service(google_client_config, google_token_path)
    test_root_id = _find_folder(service, "discord2drive-test", "root")
    if not test_root_id:
        return
    e2e_id = _find_folder(service, "e2e", test_root_id)
    if e2e_id:
        service.files().delete(fileId=e2e_id).execute()
        print("\nCleaned up discord2drive-test/e2e")


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "main", *args],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )


def test_dry_run_prints_transcript(test_thread_url):
    result = _run(test_thread_url, "SomeFolder", "--dry-run")
    assert result.returncode == 0
    assert "# " in result.stdout       # markdown heading present
    assert "**" in result.stdout       # at least one attributed message


def test_dry_run_does_not_require_drive_path_to_be_valid(test_thread_url):
    result = _run(test_thread_url, "NonExistentFolder", "--dry-run")
    assert result.returncode == 0


def test_full_upload(test_thread_url):
    result = _run(test_thread_url, TEST_DRIVE_PATH)
    assert result.returncode == 0
    assert "Done:" in result.stdout
    assert "drive.google.com" in result.stdout
    print(result.stdout)


def test_output_local_saves_file(test_thread_url, tmp_path):
    result = _run(test_thread_url, "--output-local", str(tmp_path))
    assert result.returncode == 0
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].suffix == ".md"
    assert "# " in files[0].read_text()


def test_output_local_with_dry_run_also_prints(test_thread_url, tmp_path):
    result = _run(test_thread_url, "--output-local", str(tmp_path), "--dry-run")
    assert result.returncode == 0
    assert "# " in result.stdout       # printed to stdout
    files = list(tmp_path.iterdir())
    assert len(files) == 1             # and saved locally


def test_dry_run_without_drive_path(test_thread_url):
    result = _run(test_thread_url, "--dry-run")
    assert result.returncode == 0
    assert "# " in result.stdout
    assert "**" in result.stdout


def test_output_local_with_drive_path(test_thread_url, tmp_path):
    result = _run(test_thread_url, TEST_DRIVE_PATH, "--output-local", str(tmp_path))
    assert result.returncode == 0
    assert "drive.google.com" in result.stdout
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].suffix == ".md"


def test_missing_thread_url_exits_with_error():
    result = _run()
    assert result.returncode == 2


def test_no_destination_exits_with_error(discord_token, google_client_config):
    result = _run("https://discord.com/channels/111/222")
    assert result.returncode == 2


def test_invalid_url_exits_cleanly(discord_token, google_client_config):
    result = _run("https://example.com/not-discord", "SomeFolder")
    assert result.returncode == 1
    assert "Unrecognised" in result.stderr
