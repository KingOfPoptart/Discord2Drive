"""
Loads and validates configuration from ~/discord2drive/.

Config directory layout:
    ~/discord2drive/
        discord_token       plain text, just the bot token
        google_creds.json   OAuth client credentials (from Google Cloud Console)
        google_token.json   OAuth token cache (auto-created on first run)
        settings.toml       optional — required for --auto-parse-pcs

settings.toml format:
    [drive]
    root = "masquerade"
    master = "master"

    [auto_pc]
    color = "#4863A0"
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR = Path.home() / "discord2drive"

_DISCORD_TOKEN_FILE = CONFIG_DIR / "discord_token"
_GOOGLE_CREDS_FILE = CONFIG_DIR / "google_creds.json"
_GOOGLE_TOKEN_FILE = CONFIG_DIR / "google_token.json"
_SETTINGS_FILE = CONFIG_DIR / "settings.toml"


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class AutoPcConfig:
    drive_root: str
    master_dir: str
    pc_color: str  # hex string e.g. "#4863A0"


@dataclass(frozen=True)
class Config:
    discord_token: str
    google_creds_file: Path | None
    google_token_file: Path
    auto_pc: AutoPcConfig | None = None


def _load_auto_pc_config(settings_file: Path) -> AutoPcConfig | None:
    if not settings_file.exists():
        return None
    try:
        data = tomllib.loads(settings_file.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML in {settings_file}: {e}") from e
    drive = data.get("drive", {})
    apc = data.get("auto_pc", {})
    if not drive or not apc:
        return None
    try:
        return AutoPcConfig(
            drive_root=drive["root"],
            master_dir=drive["master"],
            pc_color=apc["color"],
        )
    except KeyError as e:
        raise ConfigError(f"settings.toml is missing required key: {e}") from e


def load(require_google: bool = True, require_auto_pc: bool = False) -> Config:
    """
    Read configuration from ~/discord2drive/.
    Raises ConfigError with a clear message if anything is missing.
    Pass require_google=False to skip Google credential validation (e.g. for --dry-run).
    Pass require_auto_pc=True to require settings.toml with [drive] and [auto_pc] sections.
    """
    errors: list[str] = []

    if not _DISCORD_TOKEN_FILE.exists():
        errors.append(
            f"Discord token not found. Create {_DISCORD_TOKEN_FILE} "
            "containing your bot token."
        )

    if require_google and not _GOOGLE_CREDS_FILE.exists():
        errors.append(
            f"Google credentials not found. Download your OAuth client JSON "
            f"from Google Cloud Console and save it to {_GOOGLE_CREDS_FILE}"
        )

    auto_pc = _load_auto_pc_config(_SETTINGS_FILE)

    if require_auto_pc and auto_pc is None:
        errors.append(
            f"--auto-parse-pcs requires {_SETTINGS_FILE}. Create it with:\n"
            "    [drive]\n"
            "    root = \"your-root-folder\"\n"
            "    master = \"master\"\n\n"
            "    [auto_pc]\n"
            "    color = \"#4863A0\""
        )

    if errors:
        raise ConfigError(
            "Missing configuration:\n" + "\n".join(f"  • {e}" for e in errors)
        )

    token = _DISCORD_TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        raise ConfigError(f"{_DISCORD_TOKEN_FILE} is empty — paste your bot token in it.")

    google_creds = _GOOGLE_CREDS_FILE if _GOOGLE_CREDS_FILE.exists() else None

    return Config(
        discord_token=token,
        google_creds_file=google_creds,
        google_token_file=_GOOGLE_TOKEN_FILE,
        auto_pc=auto_pc,
    )
