"""Unit tests for formatter.py — no credentials or network needed."""

import pytest
from discord_client import Attachment, Message
from formatter import format_transcript, make_filename, _slugify


SAMPLE_MESSAGES = [
    Message(
        id="111",
        author="ChrisWriter",
        timestamp="2026-05-19T09:14:00.000000+00:00",
        content="Elara moved through the stalls without looking at him.",
        attachments=[],
    ),
    Message(
        id="222",
        author="MattWriter",
        timestamp="2026-05-19T09:15:30.000000+00:00",
        content='Davan caught her sleeve. "You knew, didn\'t you."',
        attachments=[],
    ),
    Message(
        id="333",
        author="ChrisWriter",
        timestamp="2026-05-19T09:16:00.000000+00:00",
        content="",
        attachments=[
            Attachment(
                filename="scene-notes.png",
                url="https://cdn.discordapp.com/attachments/123/scene-notes.png",
                content_type="image/png",
            )
        ],
    ),
]


def test_transcript_contains_thread_name():
    out = format_transcript("Scene - Market", SAMPLE_MESSAGES)
    assert "# Scene - Market" in out


def test_transcript_contains_authors():
    out = format_transcript("Scene", SAMPLE_MESSAGES)
    assert "**ChrisWriter**" in out
    assert "**MattWriter**" in out


def test_transcript_contains_content():
    out = format_transcript("Scene", SAMPLE_MESSAGES)
    assert "Elara moved through the stalls" in out
    assert "Davan caught her sleeve" in out


def test_transcript_timestamps_formatted():
    out = format_transcript("Scene", SAMPLE_MESSAGES)
    assert "2026-05-19 09:14 UTC" in out
    assert "2026-05-19 09:15 UTC" in out


def test_transcript_message_format():
    out = format_transcript("Scene", SAMPLE_MESSAGES)
    assert "**ChrisWriter** [2026-05-19 09:14 UTC]:" in out
    assert "**MattWriter** [2026-05-19 09:15 UTC]:" in out


def test_transcript_attachment_rendered():
    out = format_transcript("Scene", SAMPLE_MESSAGES)
    assert "scene-notes.png" in out
    assert "Attachment" in out


def test_transcript_message_count():
    out = format_transcript("Scene", SAMPLE_MESSAGES)
    assert "**Messages:** 3" in out


def test_empty_thread():
    out = format_transcript("Empty Thread", [])
    assert "# Empty Thread" in out
    assert "**Messages:** 0" in out


def test_make_filename_slugifies():
    name = make_filename("Scene - Elara & Davan: Market!")
    assert name.endswith(".md")
    assert " " not in name
    assert ":" not in name


def test_slugify_basic():
    assert _slugify("Hello World") == "hello-world"


def test_slugify_special_chars():
    assert _slugify("Elara & Davan: The Market!") == "elara-davan-the-market"


def test_slugify_non_ascii():
    assert _slugify("Café au Lait") == "cafe-au-lait"
    assert _slugify("Ünïcödé") == "unicode"


def test_slugify_truncates():
    long_name = "a" * 200
    assert len(_slugify(long_name)) <= 80
