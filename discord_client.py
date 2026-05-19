"""Fetches all messages from a Discord thread via the REST API."""

import re
import requests
from dataclasses import dataclass, field
from typing import Optional

DISCORD_API = "https://discord.com/api/v10"

# Matches both discord.com and discordapp.com URLs
_THREAD_URL_RE = re.compile(
    r"https?://(?:www\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)"
)


@dataclass
class Attachment:
    filename: str
    url: str
    content_type: Optional[str] = None


@dataclass
class Message:
    id: str
    author: str
    timestamp: str
    content: str
    attachments: list[Attachment] = field(default_factory=list)


class DiscordClientError(Exception):
    pass


def parse_thread_url(url: str) -> tuple[str, str]:
    """Return (server_id, thread_id) from a Discord thread URL."""
    match = _THREAD_URL_RE.match(url.strip())
    if not match:
        raise DiscordClientError(f"Unrecognised Discord thread URL: {url!r}")
    return match.group(1), match.group(2)


def fetch_thread_messages(thread_id: str, bot_token: str) -> list[Message]:
    """
    Fetch every message in a thread, oldest-first.
    Handles pagination transparently (Discord returns max 100 per request).
    """
    headers = {"Authorization": f"Bot {bot_token}"}
    messages: list[Message] = []
    before: Optional[str] = None

    while True:
        params: dict = {"limit": 100}
        if before:
            params["before"] = before

        resp = requests.get(
            f"{DISCORD_API}/channels/{thread_id}/messages",
            headers=headers,
            params=params,
            timeout=30,
        )

        if resp.status_code == 401:
            raise DiscordClientError("Invalid bot token — check your credentials.")
        if resp.status_code == 403:
            raise DiscordClientError(
                "Bot lacks permission to read this thread. "
                "Ensure it has Read Message History in the server."
            )
        if resp.status_code == 404:
            raise DiscordClientError(
                f"Thread {thread_id!r} not found. "
                "Check the URL and confirm the bot is in the server."
            )
        if not resp.ok:
            raise DiscordClientError(
                f"Discord API error {resp.status_code}: {resp.text}"
            )

        batch = resp.json()
        if not batch:
            break

        for raw in batch:
            msg_type = raw.get("type", 0)

            # Type 4 = channel name change — system event, not a real message
            if msg_type == 4:
                continue

            # Type 21 = thread starter — the real content lives in referenced_message
            if msg_type == 21:
                ref = raw.get("referenced_message")
                if ref:
                    raw = ref
                else:
                    continue

            if not raw.get("content") and not raw.get("attachments"):
                continue

            messages.append(
                Message(
                    id=raw["id"],
                    author=raw["author"]["global_name"] or raw["author"]["username"],
                    timestamp=raw["timestamp"],
                    content=raw.get("content", ""),
                    attachments=[
                        Attachment(
                            filename=a["filename"],
                            url=a["url"],
                            content_type=a.get("content_type"),
                        )
                        for a in raw.get("attachments", [])
                    ],
                )
            )

        if len(batch) < 100:
            break

        before = batch[-1]["id"]

    # Discord returns newest-first; reverse to get chronological order
    messages.reverse()
    return messages


def fetch_thread_info(thread_id: str, bot_token: str) -> dict:
    """Return channel/thread metadata (name, type, etc.)."""
    headers = {"Authorization": f"Bot {bot_token}"}
    resp = requests.get(
        f"{DISCORD_API}/channels/{thread_id}",
        headers=headers,
        timeout=30,
    )
    if not resp.ok:
        raise DiscordClientError(
            f"Could not fetch thread info: {resp.status_code} {resp.text}"
        )
    return resp.json()
