"""Shared fixtures for integration tests. Loads ~/discord2drive/settings.toml."""

import os
import tomllib
import pytest
from pathlib import Path

_CONFIG_DIR = Path.home() / "discord2drive"
_CONFIG_FILE = _CONFIG_DIR / "settings.toml"
_GOOGLE_TOKEN_FILE = _CONFIG_DIR / "google_token.json"

_GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _load_settings() -> dict:
    if not _CONFIG_FILE.exists():
        pytest.fail(
            f"\n\nConfig file not found: {_CONFIG_FILE}\n"
            "Create it — see README for the full format."
        )
    return tomllib.loads(_CONFIG_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def discord_token() -> str:
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if token:
        return token
    data = _load_settings()
    token = data.get("discord", {}).get("token", "").strip()
    if not token:
        pytest.fail(
            f"\n\n[discord] token missing from {_CONFIG_FILE}\n"
            "Add:\n  [discord]\n  token = \"your-bot-token\""
        )
    return token


@pytest.fixture(scope="session")
def google_client_config(discord_token) -> dict:
    data = _load_settings()
    g = data.get("google", {})
    client_id = g.get("client_id", "").strip()
    client_secret = g.get("client_secret", "").strip()
    if not client_id or not client_secret:
        pytest.fail(
            f"\n\n[google] client_id / client_secret missing from {_CONFIG_FILE}\n"
            "Add:\n  [google]\n  client_id = \"...\"\n  client_secret = \"...\""
        )
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": _GOOGLE_AUTH_URI,
            "token_uri": _GOOGLE_TOKEN_URI,
            "redirect_uris": ["http://localhost"],
        }
    }


@pytest.fixture(scope="session")
def google_token_path() -> Path:
    return _GOOGLE_TOKEN_FILE


@pytest.fixture(scope="session")
def test_thread_url(discord_token, google_client_config) -> str:
    data = _load_settings()
    url = data.get("test", {}).get("thread_url", "").strip()
    if not url:
        pytest.fail(
            f"\n\n[test] thread_url missing from {_CONFIG_FILE}\n"
            "Add:\n  [test]\n  thread_url = \"https://discord.com/channels/SERVER_ID/THREAD_ID\"\n\n"
            "Right-click any thread in Discord → Copy Link to get the URL."
        )
    return url
