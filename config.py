"""
Loads and validates configuration from ~/discord2drive/.

Config directory layout:
    ~/discord2drive/
        discord_token       plain text, just the bot token
        google_creds.json   OAuth client credentials (from Google Cloud Console)
        google_token.json   OAuth token cache (auto-created on first run)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR = Path.home() / "discord2drive"

_DISCORD_TOKEN_FILE = CONFIG_DIR / "discord_token"
_GOOGLE_CREDS_FILE = CONFIG_DIR / "google_creds.json"
_GOOGLE_TOKEN_FILE = CONFIG_DIR / "google_token.json"


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    discord_token: str
    google_creds_file: Path | None
    google_token_file: Path


def load(require_google: bool = True) -> Config:
    """
    Read configuration from ~/discord2drive/.
    Raises ConfigError with a clear message if anything is missing.
    Pass require_google=False to skip Google credential validation (e.g. for --dry-run).
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
    )
