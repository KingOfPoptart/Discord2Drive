"""Unit tests for config.py."""

import pytest
from pathlib import Path
from unittest.mock import patch
from config import load, ConfigError, AutoPcConfig

_MINIMAL_TOML = """\
[discord]
token = "fake-token"

[google]
client_id = "test-client-id.apps.googleusercontent.com"
client_secret = "test-secret"
"""

_FULL_TOML = _MINIMAL_TOML + """
[auto_pc]
folder = "masquerade"
master = "master"
color = "#4863A0"
"""


def _write_toml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "settings.toml"
    p.write_text(content)
    return p


def _patches(tmp_path: Path):
    return (
        patch("config._CONFIG_FILE", tmp_path / "settings.toml"),
        patch("config._GOOGLE_TOKEN_FILE", tmp_path / "google_token.json"),
    )


def test_load_succeeds_with_valid_config(tmp_path):
    _write_toml(tmp_path, _MINIMAL_TOML)
    with _patches(tmp_path)[0], _patches(tmp_path)[1]:
        cfg = load()
    assert cfg.discord_token == "fake-token"
    assert cfg.google_client_config is not None
    assert cfg.google_client_config["installed"]["client_id"] == "test-client-id.apps.googleusercontent.com"
    assert cfg.google_token_file == tmp_path / "google_token.json"


def test_load_strips_whitespace_from_token(tmp_path):
    _write_toml(tmp_path, "[discord]\ntoken = \"  my-token  \"\n[google]\nclient_id = \"x\"\nclient_secret = \"y\"\n")
    with _patches(tmp_path)[0], _patches(tmp_path)[1]:
        cfg = load()
    assert cfg.discord_token == "my-token"


def test_load_raises_if_config_file_missing(tmp_path):
    with patch("config._CONFIG_FILE", tmp_path / "settings.toml"), \
         patch("config._GOOGLE_TOKEN_FILE", tmp_path / "google_token.json"):
        with pytest.raises(ConfigError, match="not found"):
            load()


def test_load_raises_if_discord_token_missing(tmp_path):
    _write_toml(tmp_path, "[google]\nclient_id = \"x\"\nclient_secret = \"y\"\n")
    with _patches(tmp_path)[0], _patches(tmp_path)[1]:
        with pytest.raises(ConfigError, match="discord"):
            load()


def test_load_raises_if_google_creds_missing(tmp_path):
    _write_toml(tmp_path, "[discord]\ntoken = \"tok\"\n")
    with _patches(tmp_path)[0], _patches(tmp_path)[1]:
        with pytest.raises(ConfigError, match="client_id"):
            load()


def test_load_raises_if_both_missing(tmp_path):
    _write_toml(tmp_path, "# empty\n")
    with _patches(tmp_path)[0], _patches(tmp_path)[1]:
        with pytest.raises(ConfigError) as exc_info:
            load()
    assert "discord" in str(exc_info.value).lower()
    assert "client_id" in str(exc_info.value)


def test_load_skips_google_check_when_not_required(tmp_path):
    _write_toml(tmp_path, "[discord]\ntoken = \"tok\"\n")
    with _patches(tmp_path)[0], _patches(tmp_path)[1]:
        cfg = load(require_google=False)
    assert cfg.discord_token == "tok"
    assert cfg.google_client_config is None


def test_load_raises_if_token_empty(tmp_path):
    _write_toml(tmp_path, "[discord]\ntoken = \"   \"\n[google]\nclient_id = \"x\"\nclient_secret = \"y\"\n")
    with _patches(tmp_path)[0], _patches(tmp_path)[1]:
        with pytest.raises(ConfigError, match="discord"):
            load()


def test_load_raises_on_invalid_toml(tmp_path):
    (tmp_path / "settings.toml").write_text("this is not [ valid toml !!!")
    with _patches(tmp_path)[0], _patches(tmp_path)[1]:
        with pytest.raises(ConfigError, match="Invalid TOML"):
            load()


# --- auto_pc config ---

def test_load_auto_pc_parsed_from_settings(tmp_path):
    _write_toml(tmp_path, _FULL_TOML)
    with _patches(tmp_path)[0], _patches(tmp_path)[1]:
        cfg = load()
    assert isinstance(cfg.auto_pc, AutoPcConfig)
    assert cfg.auto_pc.folder == "masquerade"
    assert cfg.auto_pc.master == "master"
    assert cfg.auto_pc.pc_color == "#4863A0"


def test_load_auto_pc_none_when_sections_absent(tmp_path):
    _write_toml(tmp_path, _MINIMAL_TOML)
    with _patches(tmp_path)[0], _patches(tmp_path)[1]:
        cfg = load()
    assert cfg.auto_pc is None


def test_load_raises_if_require_auto_pc_and_sections_absent(tmp_path):
    _write_toml(tmp_path, _MINIMAL_TOML)
    with _patches(tmp_path)[0], _patches(tmp_path)[1]:
        with pytest.raises(ConfigError, match="auto_pc"):
            load(require_auto_pc=True)
