# Discord2Drive — Claude Steering

## What this project is

CLI tool that exports Discord thread transcripts to Google Docs. Given a thread URL and one or more `folder/doc-name` paths, it fetches all messages, formats them as markdown, and writes the transcript as a **tab** inside the target Google Doc. The doc and folder are created automatically if absent. Running it again on the same thread/doc overwrites the tab rather than duplicating it.

## How to run the tool

```bash
# Default: auto-detects PCs and writes to configured folder/docs
uv run discord2drive "<thread_url>"

# Dry run (print only, no Drive write)
uv run discord2drive "<thread_url>" --dry-run

# Save locally (combine with --dry-run to skip Drive upload)
uv run discord2drive "<thread_url>" --output-local "<dir>" [--dry-run]

# Explicit paths (disables PC auto-detection)
uv run discord2drive "<thread_url>" --disable-parse-pcs "<folder/doc-name>" ["<folder/doc-name>" ...]
```

Drive paths must include a folder component — `folder/doc-name` format. Single-segment paths error immediately. Explicit paths require `--disable-parse-pcs`.

## How to run tests

```bash
# Unit tests only — no credentials needed, always safe to run
uv run pytest tests/ --ignore=tests/integration

# Full suite including live API calls
uv run pytest tests/

# Single file
uv run pytest tests/test_formatter.py -v
```

## Project structure

| File | Role |
|---|---|
| `main.py` | CLI entry point (argparse), wires all modules together |
| `config.py` | Loads credentials from `~/discord2drive/settings.toml`, raises `ConfigError` with clear messages |
| `discord_client.py` | Discord REST API — parses thread URLs, fetches all messages (paginated) |
| `formatter.py` | Pure function: message list → markdown transcript string |
| `drive_client.py` | Google OAuth2 and folder path resolution |
| `docs_client.py` | Google Docs API — finds/creates docs and upserts tabs |

## Credentials

All credentials live in `~/discord2drive/settings.toml` — never in the project directory.

| File | Contents |
|---|---|
| `~/discord2drive/settings.toml` | All configuration — Discord token, Google OAuth credentials, Drive paths, PC color, test thread URL |
| `~/discord2drive/google_token.json` | OAuth token cache — auto-created on first run, never edit manually |

### settings.toml sections

| Section | Keys | Required |
|---|---|---|
| `[discord]` | `token` | Always |
| `[google]` | `client_id`, `client_secret` | When uploading to Drive/Docs |
| `[auto_pc]` | `folder`, `master`, `color` | Default auto-PC mode (omit only when always using `--disable-parse-pcs`) |
| `[test]` | `thread_url` | Integration tests only |

## Integration tests

Integration tests require `~/discord2drive/settings.toml` with all sections populated and hit real APIs. If any required key is absent the tests **fail** with a clear message — nothing silently skips. All credential checks live in `conftest.py` as session-scoped fixtures.

- `tests/integration/test_discord_live.py` — fetches the thread in `[test] thread_url`, verifies messages and transcript
- `tests/integration/test_drive_live.py` — creates `discord2drive-test/` in Drive, resolves paths, then **deletes the folder on cleanup**
- `tests/integration/test_docs_live.py` — creates a doc, writes tabs, overwrites, then **deletes the doc on cleanup**
- `tests/integration/test_e2e.py` — runs the full CLI pipeline; writes to `discord2drive-test/e2e` doc
- `tests/integration/conftest.py` — owns all credential loading; provides `discord_token`, `google_client_config`, `google_token_path`, and `test_thread_url` as session-scoped fixtures

### [test] thread_url

Add to `settings.toml`:
```toml
[test]
thread_url = "https://discord.com/channels/SERVER_ID/THREAD_ID"
```

The tests make no assumptions about content — they only assert that messages are returned, a transcript is produced, and the tab write succeeds.

## Discord API notes

- Thread URLs: `https://discord.com/channels/{server_id}/{thread_id}` — both `discord.com` and `discordapp.com` are supported
- Messages are returned newest-first by the API; `discord_client.py` reverses them
- Message type 21 = thread starter — real content is in `referenced_message`, not the message body itself
- Message type 4 = channel rename system event — skip it
- Empty messages (no content, no attachments) are skipped
- Webhook/bot messages carry text in `embeds[0].description` (character narration) or `embeds[0].title` + `fields` (dice rolls); `content` is empty or just custom emoji
- `Message.embed_color` holds the integer from `embeds[0].color` — used by `extract_pc_names()` to identify PC characters by their embed left-border color

## PC auto-detection (default behavior)

PC characters in roleplay threads are identified by their embed color (`embeds[0].color`). The GM sets a distinct color per character in the bot; PCs share one color and NPCs share another. `extract_pc_names(messages, pc_color_hex)` returns character names (in first-appearance order) whose embed color matches the configured hex value.

Auto-detection is the default. Use `--disable-parse-pcs` to write to explicit paths instead. Requires `~/discord2drive/settings.toml` with an `[auto_pc]` section containing `folder` (Drive folder name), `master` (master doc name), and `color` (PC embed color hex).

## Google Docs notes (docs_client.py)

- Uses Google Docs API v1 tabs feature
- `find_or_create_doc(drive_service, doc_name, folder_id)` — queries Drive for a doc with the given name in the given folder; creates it if absent
- `upsert_tab(docs_service, doc_id, tab_name, content)` — four cases:
  1. Tab exists + multiple tabs → delete old tab, create fresh, insert text
  2. Tab exists + only tab → `deleteContentRange` to clear, insert at index 1
  3. New tab + Google's default "Tab 1" present anywhere in doc → create tab, delete "Tab 1", insert text
  4. New tab + no "Tab 1" → create tab, insert text
  - "Tab 1" detection: title == "Tab 1" and body endIndex ≤ 2 (empty/default content). Handles both fresh docs and orphaned Tab 1s left by earlier buggy writes.
- Returns the doc's web URL: `https://docs.google.com/document/d/{doc_id}/edit`
- Requires the Google Docs API to be enabled in Google Cloud Console (separate from Drive API)

## Google Drive notes

- Scope used: `https://www.googleapis.com/auth/drive` (full access — needed to find existing folders/docs the app didn't create)
- `resolve_drive_path` walks a slash-separated folder path, creating any missing folders
- `get_credentials` is public — shared between `drive_client` and `docs_client`

## After changing pyproject.toml

If you add or remove modules from `[tool.setuptools] py-modules`, re-run the editable install or the `discord2drive` command won't reflect the change:

```bash
uv pip install -e .
```

## Dependencies

Managed by `uv`. To add a package: `uv add <package>`. To install everything including the CLI entry point: `uv pip install -e .`.
Do not use plain `pip` (without `uv`) — it bypasses the lockfile.

## Known gotchas

- `uv run discord2drive` only works after `uv pip install -e .` has been run at least once. `uv run python main.py` always works without it.
- Google OAuth scope must be `drive` (not `drive.file`) — the narrower scope can't see folders/docs the app didn't create, which silently creates duplicates instead of resolving existing paths.
- The Google Cloud OAuth consent screen must have the user added as a test user or the auth flow will be blocked.
- Both **Google Drive API** and **Google Docs API** must be enabled in the Cloud project — they are separate toggles.
- When adding a new Google client secret in Cloud Console, the secret value is only shown immediately after clicking **Add secret** — copy it right away into `settings.toml`.
- Discord's `discordapp.com` domain is a legacy alias for `discord.com` — both are handled by the URL parser.
- drive_paths must use `folder/doc-name` format (at least one `/`). Single-segment paths cause an immediate error from argparse.
