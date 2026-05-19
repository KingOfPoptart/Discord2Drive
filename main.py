"""CLI entry point for discord2drive."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
        nargs="*",
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
    parser.add_argument(
        "--output-local",
        metavar="dir",
        help="Save the transcript to this local directory.",
    )
    parser.add_argument(
        "--auto-parse-pcs",
        action="store_true",
        help="Detect PC characters by embed color and upload to root/master and root/<PC name>/. "
             "Requires [drive] and [auto_pc] sections in ~/discord2drive/settings.toml.",
    )

    args = parser.parse_args()

    if args.auto_parse_pcs and args.drive_paths:
        parser.error("--auto-parse-pcs cannot be combined with explicit drive_paths")

    if not args.drive_paths and not args.dry_run and not args.output_local and not args.auto_parse_pcs:
        parser.error("specify at least one drive_path, --output-local <dir>, --auto-parse-pcs, or --dry-run")

    needs_google = (bool(args.drive_paths) or args.auto_parse_pcs) and not args.dry_run

    try:
        cfg = config.load(require_google=needs_google, require_auto_pc=args.auto_parse_pcs)
    except config.ConfigError as e:
        print(f"Configuration error:\n{e}", file=sys.stderr)
        sys.exit(1)

    try:
        _, thread_id = discord_client.parse_thread_url(args.thread_url)
    except discord_client.DiscordClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching thread {args.thread_url} ...")
    try:
        info = discord_client.fetch_thread_info(thread_id, cfg.discord_token)
        messages = discord_client.fetch_thread_messages(thread_id, cfg.discord_token)
    except discord_client.DiscordClientError as e:
        print(f"Discord error: {e}", file=sys.stderr)
        sys.exit(1)

    thread_name = info.get("name", "Untitled Thread")
    print(f"  Thread: {thread_name!r} — {len(messages)} messages")

    transcript = formatter.format_transcript(thread_name, messages)
    filename = formatter.make_filename(thread_name)

    if args.output_local:
        out_dir = Path(args.output_local)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        out_path.write_text(transcript, encoding="utf-8")
        print(f"  Saved locally: {out_path}")

    if args.dry_run:
        print(f"\n--- {filename} ---\n")
        print(transcript)
        return

    # Determine Drive upload paths
    if args.auto_parse_pcs:
        pc_names = discord_client.extract_pc_names(messages, cfg.auto_pc.pc_color)
        if not pc_names:
            print("Error: --auto-parse-pcs found no PC characters in this thread.", file=sys.stderr)
            sys.exit(1)
        print(f"  Found PCs: {', '.join(pc_names)}")
        root = cfg.auto_pc.drive_root
        upload_paths = [f"{root}/{cfg.auto_pc.master_dir}"] + [f"{root}/{name}" for name in pc_names]
    else:
        upload_paths = args.drive_paths

    if not upload_paths:
        return

    print("Connecting to Google Drive ...")
    try:
        service = drive_client.build_service(cfg.google_creds_file, cfg.google_token_file)
    except drive_client.DriveClientError as e:
        print(f"Google Drive error: {e}", file=sys.stderr)
        sys.exit(1)

    any_failed = False
    for drive_path in upload_paths:
        print(f"Uploading to '{drive_path}' ...")
        try:
            folder_id = drive_client.resolve_drive_path(service, drive_path)
            url = drive_client.upload_file(service, filename, transcript, folder_id)
            print(f"  Done: {url}")
        except drive_client.DriveClientError as e:
            print(f"  Upload failed: {e}", file=sys.stderr)
            any_failed = True

    print("Finished.")
    if any_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
