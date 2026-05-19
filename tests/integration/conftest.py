"""Shared fixtures for integration tests. Loads ~/discord2drive/integ.json."""

import json
import pytest
from pathlib import Path

_INTEG_FILE = Path.home() / "discord2drive" / "integ.json"


def _load() -> dict | None:
    if not _INTEG_FILE.exists():
        return None
    try:
        return json.loads(_INTEG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        pytest.fail(f"\n\nCould not parse {_INTEG_FILE}: {e}\nCheck the file contains valid JSON.")


@pytest.fixture(scope="session")
def integ_config():
    cfg = _load()
    if cfg is None:
        pytest.fail(
            f"\n\nIntegration config not found: {_INTEG_FILE}\n"
            "Create it with the URL of a thread your bot can access:\n\n"
            '  {\n    "test_thread_url": "https://discord.com/channels/SERVER_ID/THREAD_ID"\n  }\n\n'
            "Right-click any thread in Discord → Copy Link to get the URL."
        )
    return cfg


@pytest.fixture(scope="session")
def test_thread_url(integ_config) -> str:
    url = integ_config.get("test_thread_url")
    if not url:
        pytest.fail(
            f"\n\n'test_thread_url' key missing from {_INTEG_FILE}\n"
            "Add it:\n\n"
            '  {\n    "test_thread_url": "https://discord.com/channels/SERVER_ID/THREAD_ID"\n  }'
        )
    return url
