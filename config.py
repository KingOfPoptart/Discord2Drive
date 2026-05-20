"""
Loads and validates configuration from ~/discord2drive/settings.toml.

settings.toml layout:
    [discord]
    token = "your-bot-token"

    [google]
    client_id = "xxx.apps.googleusercontent.com"
    client_secret = "GOCSPX-..."

    [drive]                     # required for --auto-parse-pcs
    root = "masquerade"
    master = "master"

    [auto_pc]                   # required for --auto-parse-pcs
    color = "#4863A0"

    [test]                      # optional — only needed for integration tests
    thread_url = "https://discord.com/channels/SERVER_ID/THREAD_ID"
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR = Path.home() / "discord2drive"

_CONFIG_FILE = CONFIG_DIR / "settings.toml"
_GOOGLE_TOKEN_FILE = CONFIG_DIR / "google_token.json"

_GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class AutoPcConfig:
    folder: str     # Drive folder containing all character docs
    master: str     # name of the master Google Doc
    pc_color: str   # hex string e.g. "#4863A0"


@dataclass(frozen=True)
class Config:
    discord_token: str
    google_client_config: dict | None  # passed directly to InstalledAppFlow.from_client_config
    google_token_file: Path
    auto_pc: AutoPcConfig | None = None


def _read_toml(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(
            f"Config file not found: {path}\n"
            "Create it — see README for the full format."
        )
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML in {path}: {e}") from e


def _build_google_client_config(client_id: str, client_secret: str) -> dict:
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": _GOOGLE_AUTH_URI,
            "token_uri": _GOOGLE_TOKEN_URI,
            "redirect_uris": ["http://localhost"],
        }
    }


def load(require_google: bool = True, require_auto_pc: bool = False) -> Config:
    """
    Read configuration from ~/discord2drive/settings.toml.
    Raises ConfigError with a clear message if anything is missing.
    """
    data = _read_toml(_CONFIG_FILE)
    errors: list[str] = []

    token = data.get("discord", {}).get("token", "").strip()
    if not token:
        errors.append(
            f"[discord] token missing from {_CONFIG_FILE}. Add:\n"
            "    [discord]\n"
            "    token = \"your-bot-token\""
        )

    google_section = data.get("google", {})
    client_id = google_section.get("client_id", "").strip()
    client_secret = google_section.get("client_secret", "").strip()
    google_client_config: dict | None = None

    if client_id and client_secret:
        google_client_config = _build_google_client_config(client_id, client_secret)
    elif require_google:
        errors.append(
            f"[google] client_id and client_secret missing from {_CONFIG_FILE}. Add:\n"
            "    [google]\n"
            "    client_id = \"xxx.apps.googleusercontent.com\"\n"
            "    client_secret = \"GOCSPX-...\""
        )

    apc = data.get("auto_pc", {})
    auto_pc: AutoPcConfig | None = None
    if apc:
        try:
            auto_pc = AutoPcConfig(
                folder=apc["folder"],
                master=apc["master"],
                pc_color=apc["color"],
            )
        except KeyError as e:
            errors.append(f"settings.toml missing required key in [auto_pc]: {e.args[0]}")

    if require_auto_pc and auto_pc is None:
        errors.append(
            f"--auto-parse-pcs requires an [auto_pc] section in {_CONFIG_FILE}:\n"
            "    [auto_pc]\n"
            "    folder = \"your-drive-folder\"\n"
            "    master = \"master\"\n"
            "    color = \"#4863A0\""
        )

    if errors:
        raise ConfigError(
            "Missing configuration:\n" + "\n".join(f"  • {e}" for e in errors)
        )

    return Config(
        discord_token=token,
        google_client_config=google_client_config,
        google_token_file=_GOOGLE_TOKEN_FILE,
        auto_pc=auto_pc,
    )
