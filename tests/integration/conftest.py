"""Shared fixtures for integration tests. Loads ~/discord2drive/ credentials."""

import json
import os
import pytest
from pathlib import Path

_CONFIG_DIR = Path.home() / "discord2drive"
_DISCORD_TOKEN_FILE = _CONFIG_DIR / "discord_token"
_GOOGLE_CREDS_FILE = _CONFIG_DIR / "google_creds.json"
_GOOGLE_TOKEN_FILE = _CONFIG_DIR / "google_token.json"
_INTEG_FILE = _CONFIG_DIR / "integ.json"


@pytest.fixture(scope="session")
def discord_token() -> str:
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if token:
        return token
    if not _DISCORD_TOKEN_FILE.exists():
        pytest.fail(
            f"\n\nDiscord bot token not found: {_DISCORD_TOKEN_FILE}\n"
            "Create it containing your bot token, or set the DISCORD_BOT_TOKEN env var."
        )
    token = _DISCORD_TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        pytest.fail(f"\n\n{_DISCORD_TOKEN_FILE} is empty — paste your bot token in it.")
    return token


@pytest.fixture(scope="session")
def google_creds_path() -> Path:
    if not _GOOGLE_CREDS_FILE.exists():
        pytest.fail(
            f"\n\nGoogle credentials not found: {_GOOGLE_CREDS_FILE}\n"
            "Download the OAuth client JSON from Google Cloud Console and save it there."
        )
    return _GOOGLE_CREDS_FILE


@pytest.fixture(scope="session")
def google_token_path() -> Path:
    return _GOOGLE_TOKEN_FILE


@pytest.fixture(scope="session")
def integ_config(discord_token, google_creds_path) -> dict:
    if not _INTEG_FILE.exists():
        pytest.fail(
            f"\n\nIntegration config not found: {_INTEG_FILE}\n"
            "Create it with the URL of a thread your bot can access:\n\n"
            '  {\n    "test_thread_url": "https://discord.com/channels/SERVER_ID/THREAD_ID"\n  }\n\n'
            "Right-click any thread in Discord → Copy Link to get the URL."
        )
    try:
        return json.loads(_INTEG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        pytest.fail(f"\n\nCould not parse {_INTEG_FILE}: {e}\nCheck the file contains valid JSON.")


@pytest.fixture(scope="session")
def test_thread_url(integ_config) -> str:
    url = integ_config.get("test_thread_url", "").strip()
    if not url:
        pytest.fail(
            f"\n\n'test_thread_url' key missing from {_INTEG_FILE}\n"
            "Add it:\n\n"
            '  {\n    "test_thread_url": "https://discord.com/channels/SERVER_ID/THREAD_ID"\n  }'
        )
    return url
