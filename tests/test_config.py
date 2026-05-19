"""Unit tests for config.py."""

import pytest
from pathlib import Path
from unittest.mock import patch
from config import load, ConfigError, CONFIG_DIR


def _mock_dir(tmp_path: Path, discord_token: str | None = "fake-token", google_creds: bool = True):
    """Patch CONFIG_DIR to a temp directory with the specified files present."""
    if discord_token is not None:
        (tmp_path / "discord_token").write_text(discord_token)
    if google_creds:
        (tmp_path / "google_creds.json").write_text("{}")
    return tmp_path


def test_load_succeeds_with_valid_config(tmp_path):
    _mock_dir(tmp_path)
    with patch("config._DISCORD_TOKEN_FILE", tmp_path / "discord_token"), \
         patch("config._GOOGLE_CREDS_FILE", tmp_path / "google_creds.json"), \
         patch("config._GOOGLE_TOKEN_FILE", tmp_path / "google_token.json"):
        cfg = load()
    assert cfg.discord_token == "fake-token"
    assert cfg.google_creds_file == tmp_path / "google_creds.json"
    assert cfg.google_token_file == tmp_path / "google_token.json"


def test_load_strips_whitespace_from_token(tmp_path):
    (tmp_path / "discord_token").write_text("  my-token\n")
    (tmp_path / "google_creds.json").write_text("{}")
    with patch("config._DISCORD_TOKEN_FILE", tmp_path / "discord_token"), \
         patch("config._GOOGLE_CREDS_FILE", tmp_path / "google_creds.json"), \
         patch("config._GOOGLE_TOKEN_FILE", tmp_path / "google_token.json"):
        cfg = load()
    assert cfg.discord_token == "my-token"


def test_load_raises_if_discord_token_missing(tmp_path):
    _mock_dir(tmp_path, discord_token=None)
    with patch("config._DISCORD_TOKEN_FILE", tmp_path / "discord_token"), \
         patch("config._GOOGLE_CREDS_FILE", tmp_path / "google_creds.json"), \
         patch("config._GOOGLE_TOKEN_FILE", tmp_path / "google_token.json"):
        with pytest.raises(ConfigError, match="Discord token"):
            load()


def test_load_raises_if_google_creds_missing(tmp_path):
    _mock_dir(tmp_path, google_creds=False)
    with patch("config._DISCORD_TOKEN_FILE", tmp_path / "discord_token"), \
         patch("config._GOOGLE_CREDS_FILE", tmp_path / "google_creds.json"), \
         patch("config._GOOGLE_TOKEN_FILE", tmp_path / "google_token.json"):
        with pytest.raises(ConfigError, match="Google credentials"):
            load()


def test_load_raises_if_both_missing(tmp_path):
    _mock_dir(tmp_path, discord_token=None, google_creds=False)
    with patch("config._DISCORD_TOKEN_FILE", tmp_path / "discord_token"), \
         patch("config._GOOGLE_CREDS_FILE", tmp_path / "google_creds.json"), \
         patch("config._GOOGLE_TOKEN_FILE", tmp_path / "google_token.json"):
        with pytest.raises(ConfigError) as exc_info:
            load()
    assert "Discord token" in str(exc_info.value)
    assert "Google credentials" in str(exc_info.value)


def test_load_skips_google_check_when_not_required(tmp_path):
    _mock_dir(tmp_path, google_creds=False)
    with patch("config._DISCORD_TOKEN_FILE", tmp_path / "discord_token"), \
         patch("config._GOOGLE_CREDS_FILE", tmp_path / "google_creds.json"), \
         patch("config._GOOGLE_TOKEN_FILE", tmp_path / "google_token.json"):
        cfg = load(require_google=False)
    assert cfg.discord_token == "fake-token"
    assert cfg.google_creds_file is None


def test_load_raises_if_token_file_empty(tmp_path):
    (tmp_path / "discord_token").write_text("   ")
    (tmp_path / "google_creds.json").write_text("{}")
    with patch("config._DISCORD_TOKEN_FILE", tmp_path / "discord_token"), \
         patch("config._GOOGLE_CREDS_FILE", tmp_path / "google_creds.json"), \
         patch("config._GOOGLE_TOKEN_FILE", tmp_path / "google_token.json"):
        with pytest.raises(ConfigError, match="empty"):
            load()
