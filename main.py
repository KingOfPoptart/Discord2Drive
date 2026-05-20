"""CLI entry point for discord2drive."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import config
import discord_client
import docs_client
import drive_client
import formatter


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="discord2drive",
        description="Export a Discord thread transcript as a tab in a Google Doc. "
                    "By default, auto-detects PC characters by embed color and writes "
                    "to the configured folder and master doc.",
    )
    parser.add_argument(
        "thread_url",
        help="URL of the Discord thread (e.g. https://discord.com/channels/SERVER/THREAD)",
    )
    parser.add_argument(
        "drive_paths",
        nargs="*",
        metavar="drive_path",
        help="Drive path(s) in 'folder/doc-name' format. "
             "Requires --disable-parse-pcs.",
    )
    parser.add_argument(
        "--disable-parse-pcs",
        action="store_true",
        help="Disable auto PC detection. Use explicit drive_path arguments instead.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and format the transcript but do not write to Drive. "
             "Prints the transcript to stdout.",
    )
    parser.add_argument(
        "--output-local",
        metavar="dir",
        help="Save the transcript to this local directory.",
    )

    args = parser.parse_intermixed_args()

    if args.drive_paths and not args.disable_parse_pcs:
        parser.error(
            "explicit drive_paths require --disable-parse-pcs; "
            "by default the tool auto-detects PC characters from embed color"
        )

    if args.disable_parse_pcs and not args.drive_paths and not args.dry_run and not args.output_local:
        parser.error(
            "--disable-parse-pcs requires at least one drive_path, --output-local <dir>, or --dry-run"
        )

    for dp in args.drive_paths:
        if "/" not in dp.strip():
            parser.error(
                f"drive_path {dp!r} must include a folder component — "
                "use 'folder/doc-name' format (e.g. 'masquerade/master')"
            )

    auto_parse = not args.disable_parse_pcs
    needs_google = (auto_parse or bool(args.drive_paths)) and not args.dry_run
    require_auto_pc = auto_parse and not args.dry_run

    try:
        cfg = config.load(require_google=needs_google, require_auto_pc=require_auto_pc)
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

    # Determine Drive paths (folder/doc_name format)
    if auto_parse:
        pc_names = discord_client.extract_pc_names(messages, cfg.auto_pc.pc_color)
        if not pc_names:
            print("Error: no PC characters detected in this thread.", file=sys.stderr)
            sys.exit(1)
        print(f"  Found PCs: {', '.join(pc_names)}")
        folder = cfg.auto_pc.folder
        upload_paths = [f"{folder}/{cfg.auto_pc.master}"] + [f"{folder}/{name}" for name in pc_names]
    else:
        upload_paths = args.drive_paths

    if not upload_paths:
        return

    print("Connecting to Google ...")
    try:
        drive_service = drive_client.build_service(cfg.google_client_config, cfg.google_token_file)
        docs_service = docs_client.build_docs_service(cfg.google_client_config, cfg.google_token_file)
    except (drive_client.DriveClientError, docs_client.DocsClientError) as e:
        print(f"Google API error: {e}", file=sys.stderr)
        sys.exit(1)

    any_failed = False
    for drive_path in upload_paths:
        folder_path, doc_name = drive_path.strip().rsplit("/", 1)
        print(f"Writing tab '{thread_name}' → '{folder_path}/{doc_name}' ...")
        try:
            folder_id = drive_client.resolve_drive_path(drive_service, folder_path)
            doc_id = docs_client.find_or_create_doc(drive_service, doc_name, folder_id)
            url = docs_client.upsert_tab(docs_service, doc_id, thread_name, transcript)
            print(f"  Done: {url}")
        except (drive_client.DriveClientError, docs_client.DocsClientError) as e:
            print(f"  Failed: {e}", file=sys.stderr)
            any_failed = True

    print("Finished.")
    if any_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
