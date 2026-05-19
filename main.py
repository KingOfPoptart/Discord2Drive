"""CLI entry point for discord2drive."""

from __future__ import annotations

import argparse
import sys

import config
import discord_client
import drive_client
import formatter


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="discord2drive",
        description="Export a Discord thread transcript to one or more Google Drive folders.",
    )
    parser.add_argument(
        "thread_url",
        help="URL of the Discord thread (e.g. https://discord.com/channels/SERVER/THREAD)",
    )
    parser.add_argument(
        "drive_paths",
        nargs="+",
        metavar="drive_path",
        help="Google Drive folder path(s) to upload to (e.g. 'Scenes/Act 1'). "
             "Folders are created if they don't exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and format the transcript but do not upload to Drive. "
             "Prints the transcript to stdout.",
    )

    args = parser.parse_args()

    # Load config — exits with a clear message if anything is missing
    try:
        cfg = config.load()
    except config.ConfigError as e:
        print(f"Configuration error:\n{e}", file=sys.stderr)
        sys.exit(1)

    # Parse thread URL
    try:
        _, thread_id = discord_client.parse_thread_url(args.thread_url)
    except discord_client.DiscordClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Fetch thread
    print(f"Fetching thread {args.thread_url} ...")
    try:
        info = discord_client.fetch_thread_info(thread_id, cfg.discord_token)
        messages = discord_client.fetch_thread_messages(thread_id, cfg.discord_token)
    except discord_client.DiscordClientError as e:
        print(f"Discord error: {e}", file=sys.stderr)
        sys.exit(1)

    thread_name = info.get("name", "Untitled Thread")
    print(f"  Thread: {thread_name!r} — {len(messages)} messages")

    # Format transcript
    transcript = formatter.format_transcript(thread_name, messages)
    filename = formatter.make_filename(thread_name)

    if args.dry_run:
        print(f"\n--- {filename} ---\n")
        print(transcript)
        return

    # Upload to each Drive path
    print("Connecting to Google Drive ...")
    try:
        service = drive_client.build_service(cfg.google_creds_file, cfg.google_token_file)
    except drive_client.DriveClientError as e:
        print(f"Google Drive error: {e}", file=sys.stderr)
        sys.exit(1)

    for drive_path in args.drive_paths:
        print(f"Uploading to '{drive_path}' ...")
        try:
            folder_id = drive_client.resolve_drive_path(service, drive_path)
            url = drive_client.upload_file(service, filename, transcript, folder_id)
            print(f"  Done: {url}")
        except drive_client.DriveClientError as e:
            print(f"  Upload failed: {e}", file=sys.stderr)

    print("Finished.")


if __name__ == "__main__":
    main()
