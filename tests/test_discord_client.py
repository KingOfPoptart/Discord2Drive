"""Unit tests for discord_client.py — all HTTP calls are mocked."""

import pytest
from pytest_httpx import HTTPXMock
import httpx
import json

# We test the logic by patching requests; use a fixture approach
from unittest.mock import patch, MagicMock

from discord_client import (
    parse_thread_url,
    fetch_thread_messages,
    fetch_thread_info,
    DiscordClientError,
    Message,
)

FAKE_TOKEN = "Bot test-token-abc"
THREAD_ID = "1506288385826885632"
BASE = "https://discord.com/api/v10"


# --- parse_thread_url ---

def test_parse_standard_url():
    server, thread = parse_thread_url(
        "https://discord.com/channels/1309606609080811531/1506288385826885632"
    )
    assert server == "1309606609080811531"
    assert thread == "1506288385826885632"


def test_parse_discordapp_url():
    server, thread = parse_thread_url(
        "https://discordapp.com/channels/1309606609080811531/1506288385826885632"
    )
    assert server == "1309606609080811531"
    assert thread == "1506288385826885632"


def test_parse_url_with_trailing_whitespace():
    server, thread = parse_thread_url(
        "  https://discord.com/channels/111/222  "
    )
    assert server == "111"
    assert thread == "222"


def test_parse_invalid_url_raises():
    with pytest.raises(DiscordClientError, match="Unrecognised"):
        parse_thread_url("https://example.com/not-discord")


def test_parse_empty_string_raises():
    with pytest.raises(DiscordClientError):
        parse_thread_url("")


# --- fetch_thread_messages (mocked via unittest.mock) ---

def _make_raw_message(msg_id: str, author: str, content: str) -> dict:
    return {
        "id": msg_id,
        "author": {"username": author, "global_name": author},
        "timestamp": "2026-05-19T09:14:00.000000+00:00",
        "content": content,
        "attachments": [],
    }


def _mock_get(responses: list[list[dict]]):
    """Return a mock requests.get that yields successive response batches."""
    call_count = 0

    def mock_get(url, headers=None, params=None, timeout=None):
        nonlocal call_count
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return mock_resp

    return mock_get


def test_fetch_returns_messages_in_chronological_order():
    # Discord returns newest-first; client must reverse
    raw = [
        _make_raw_message("300", "Charlie", "third"),
        _make_raw_message("200", "Bob", "second"),
        _make_raw_message("100", "Alice", "first"),
    ]
    with patch("discord_client.requests.get", side_effect=_mock_get([raw, []])):
        msgs = fetch_thread_messages(THREAD_ID, "fake-token")
    assert [m.content for m in msgs] == ["first", "second", "third"]


def test_fetch_uses_global_name_over_username():
    raw = [{
        "id": "1",
        "author": {"username": "old_handle", "global_name": "Display Name"},
        "timestamp": "2026-05-19T09:00:00.000000+00:00",
        "content": "hi",
        "attachments": [],
    }]
    with patch("discord_client.requests.get", side_effect=_mock_get([raw, []])):
        msgs = fetch_thread_messages(THREAD_ID, "fake-token")
    assert msgs[0].author == "Display Name"


def test_fetch_handles_attachments():
    raw = [{
        "id": "1",
        "author": {"username": "alice", "global_name": "Alice"},
        "timestamp": "2026-05-19T09:00:00.000000+00:00",
        "content": "",
        "attachments": [
            {"filename": "photo.png", "url": "https://cdn.discord.com/photo.png", "content_type": "image/png"}
        ],
    }]
    with patch("discord_client.requests.get", side_effect=_mock_get([raw, []])):
        msgs = fetch_thread_messages(THREAD_ID, "fake-token")
    assert len(msgs[0].attachments) == 1
    assert msgs[0].attachments[0].filename == "photo.png"


def test_fetch_401_raises_clear_error():
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 401
    with patch("discord_client.requests.get", return_value=mock_resp):
        with pytest.raises(DiscordClientError, match="Invalid bot token"):
            fetch_thread_messages(THREAD_ID, "bad-token")


def test_fetch_403_raises_clear_error():
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 403
    with patch("discord_client.requests.get", return_value=mock_resp):
        with pytest.raises(DiscordClientError, match="permission"):
            fetch_thread_messages(THREAD_ID, "fake-token")


def test_fetch_404_raises_clear_error():
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 404
    with patch("discord_client.requests.get", return_value=mock_resp):
        with pytest.raises(DiscordClientError, match="not found"):
            fetch_thread_messages(THREAD_ID, "fake-token")


def test_fetch_paginates_when_full_batch():
    """When a batch has 100 messages, it should request the next page."""
    page1 = [_make_raw_message(str(i), "user", f"msg {i}") for i in range(100, 0, -1)]
    page2 = [_make_raw_message("0", "user", "msg 0")]

    call_args = []

    def mock_get(url, headers=None, params=None, timeout=None):
        call_args.append(params.copy() if params else {})
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = page1 if len(call_args) == 1 else page2
        return mock_resp

    with patch("discord_client.requests.get", side_effect=mock_get):
        msgs = fetch_thread_messages(THREAD_ID, "fake-token")

    assert len(call_args) == 2
    assert "before" in call_args[1]
    assert len(msgs) == 101
