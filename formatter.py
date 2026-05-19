"""Converts a list of Discord messages into a readable markdown transcript."""

import re
import unicodedata
from datetime import datetime, timezone
from discord_client import Message


def _format_timestamp(iso: str) -> str:
    """Convert ISO 8601 timestamp to a clean UTC string."""
    # Discord timestamps look like: 2026-05-19T09:14:00.000000+00:00
    dt = datetime.fromisoformat(iso).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def _slugify(text: str) -> str:
    """Convert thread name to a safe cross-platform filename."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:80]


def format_transcript(thread_name: str, messages: list[Message]) -> str:
    """Return a markdown string of the full thread transcript."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# {thread_name}",
        "",
        f"**Exported:** {today}",
        f"**Messages:** {len(messages)}",
        "",
        "---",
        "",
    ]

    for msg in messages:
        ts = _format_timestamp(msg.timestamp)
        prefix = f"**{msg.author}** [{ts}]:"
        content_parts = []
        if msg.content:
            content_parts.append(msg.content)
        for att in msg.attachments:
            content_parts.append(f"*[Attachment: {att.filename}]({att.url})*")
        lines.append(f"{prefix} " + "\n\n".join(content_parts) if content_parts else prefix)
        lines.append("")  # blank line so each message is its own markdown paragraph

    return "\n".join(lines)


def make_filename(thread_name: str) -> str:
    """Return a safe filename for the transcript."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = _slugify(thread_name)
    return f"{slug}_{today}.md"
