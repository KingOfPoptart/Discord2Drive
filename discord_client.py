"""Fetches all messages from a Discord thread via the REST API."""

import re
import time
import requests
import requests.exceptions
from dataclasses import dataclass, field
from typing import Optional

DISCORD_API = "https://discord.com/api/v10"

# Matches both discord.com and discordapp.com URLs
_THREAD_URL_RE = re.compile(
    r"https?://(?:www\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)"
)

# Discord custom emoji: <:name:id> or animated <a:name:id> — not meaningful as text
_CUSTOM_EMOJI_RE = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
# ANSI escape codes used by dice bots in code blocks
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
# Opening code fence with optional language tag (```ansi, ```py, etc.)
_CODE_FENCE_OPEN_RE = re.compile(r"```[a-z]*")
# Markdown links [text](url) — strip the whole thing, they're noise in plain text
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)")
# Discord user/member mentions: <@USER_ID> or <@!USER_ID>
_MENTION_RE = re.compile(r"<@!?(\d+)>")


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
    embed_color: int | None = None


class DiscordClientError(Exception):
    pass


def _resolve_mentions(content: str, mentions: list) -> str:
    """Replace <@USER_ID> with @DisplayName using the message's mentions array."""
    if "<@" not in content:
        return content
    lookup = {m["id"]: m.get("global_name") or m["username"] for m in mentions}
    return _MENTION_RE.sub(lambda m: f"@{lookup.get(m.group(1), m.group(1))}", content)


def _text_from_embeds(embeds: list) -> str:
    """
    Extract readable text from Discord embed objects.

    Character/narration bot embeds use description. Dice bot embeds use title + fields.
    """
    if not embeds:
        return ""
    e = embeds[0]
    if e.get("description"):
        return e["description"]
    parts = []
    if e.get("title"):
        parts.append(e["title"])
    for f in e.get("fields", []):
        value = f.get("value", "")
        value = _ANSI_RE.sub("", value)
        value = _CODE_FENCE_OPEN_RE.sub("", value)  # strip ```lang opening markers
        value = value.replace("```", "")             # strip bare closing markers
        value = _MARKDOWN_LINK_RE.sub("", value)
        value = re.sub(r"[\s|]+", " ", value).strip()
        if value:
            name = f.get("name", "")
            parts.append(f"{name}: {value}" if name else value)
    return "\n".join(parts)


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

        try:
            resp = requests.get(
                f"{DISCORD_API}/channels/{thread_id}/messages",
                headers=headers,
                params=params,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise DiscordClientError(f"Network error fetching messages: {e}") from e

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "1"))
            time.sleep(retry_after)
            continue

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

            embeds = raw.get("embeds", [])
            embed_color = embeds[0].get("color") if embeds else None

            content = _CUSTOM_EMOJI_RE.sub("", raw.get("content", "")).strip()
            if not content:
                content = _text_from_embeds(embeds)
            content = _resolve_mentions(content, raw.get("mentions", []))

            if not content and not raw.get("attachments"):
                continue

            messages.append(
                Message(
                    id=raw["id"],
                    author=raw["author"]["global_name"] or raw["author"]["username"],
                    timestamp=raw["timestamp"],
                    content=content,
                    embed_color=embed_color,
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


def extract_pc_names(messages: list[Message], pc_color_hex: str) -> list[str]:
    """Return unique PC character names in first-appearance order, identified by embed color."""
    pc_color = int(pc_color_hex.lstrip("#"), 16)
    seen: set[str] = set()
    result: list[str] = []
    for msg in messages:
        if msg.embed_color == pc_color and msg.author not in seen:
            seen.add(msg.author)
            result.append(msg.author)
    return result


def fetch_thread_info(thread_id: str, bot_token: str) -> dict:
    """Return channel/thread metadata (name, type, etc.)."""
    headers = {"Authorization": f"Bot {bot_token}"}
    while True:
        try:
            resp = requests.get(
                f"{DISCORD_API}/channels/{thread_id}",
                headers=headers,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise DiscordClientError(f"Network error fetching thread info: {e}") from e
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "1"))
            time.sleep(retry_after)
            continue
        if not resp.ok:
            raise DiscordClientError(
                f"Could not fetch thread info: {resp.status_code} {resp.text}"
            )
        return resp.json()
