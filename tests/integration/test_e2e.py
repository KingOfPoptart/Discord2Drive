"""
End-to-end integration test: runs the full pipeline via main.py.
Skipped if either credential file is missing.
"""

import subprocess
import sys
from pathlib import Path

import pytest

CREDS = Path.home() / "discord2drive" / "google_creds.json"
TOKEN = Path.home() / "discord2drive" / "discord_token"
TEST_THREAD = "https://discordapp.com/channels/1309606609080811531/1506288385826885632"
TEST_DRIVE_PATH = "discord2drive-test/e2e"

pytestmark = pytest.mark.skipif(
    not CREDS.exists() or not TOKEN.exists(),
    reason="Credentials missing from ~/discord2drive/",
)


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "main", *args],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )


def test_dry_run_prints_transcript():
    result = _run(TEST_THREAD, "SomeFolder", "--dry-run")
    assert result.returncode == 0
    assert "thread name" in result.stdout
    assert "KingOfPoptart" in result.stdout
    assert "this is a thread" in result.stdout


def test_dry_run_does_not_require_drive_path_to_be_valid():
    result = _run(TEST_THREAD, "NonExistentFolder", "--dry-run")
    assert result.returncode == 0


def test_full_upload():
    result = _run(TEST_THREAD, TEST_DRIVE_PATH)
    assert result.returncode == 0
    assert "Done:" in result.stdout
    assert "drive.google.com" in result.stdout
    print(result.stdout)


def test_invalid_url_exits_cleanly():
    result = _run("https://example.com/not-discord", "SomeFolder")
    assert result.returncode == 1
    assert "Unrecognised" in result.stderr
