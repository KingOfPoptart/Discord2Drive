"""
Integration test: hits the real Discord API against the test thread
defined in ~/discord2drive/integ.json.

Fails with setup instructions if any required config is absent.
"""

import pytest
from discord_client import fetch_thread_messages, fetch_thread_info, parse_thread_url
from formatter import format_transcript, make_filename


def test_parse_test_thread_url(test_thread_url):
    server_id, thread_id = parse_thread_url(test_thread_url)
    assert server_id.isdigit()
    assert thread_id.isdigit()


def test_fetch_thread_info(test_thread_url, discord_token):
    _, thread_id = parse_thread_url(test_thread_url)
    info = fetch_thread_info(thread_id, discord_token)
    assert "name" in info
    print(f"\nThread name: {info['name']}")
    print(f"Thread type: {info.get('type')}")


def test_fetch_messages_returns_results(test_thread_url, discord_token):
    _, thread_id = parse_thread_url(test_thread_url)
    messages = fetch_thread_messages(thread_id, discord_token)
    assert len(messages) > 0, "Expected at least one message in the test thread"
    print(f"\nFetched {len(messages)} messages")
    for msg in messages[:3]:
        print(f"  [{msg.timestamp}] {msg.author}: {msg.content[:60]!r}")


def test_full_pipeline_produces_transcript(test_thread_url, discord_token):
    _, thread_id = parse_thread_url(test_thread_url)
    info = fetch_thread_info(thread_id, discord_token)
    messages = fetch_thread_messages(thread_id, discord_token)

    thread_name = info.get("name", "Unknown Thread")
    transcript = format_transcript(thread_name, messages)
    filename = make_filename(thread_name)

    assert f"# {thread_name}" in transcript
    assert len(transcript) > 100
    print(f"\nFilename: {filename}")
    print(f"Transcript length: {len(transcript)} chars")
    print("\n--- Full transcript ---")
    print(transcript)
