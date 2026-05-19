# Discord2Drive — Claude Steering

## What this project is

CLI tool that exports Discord thread transcripts to Google Drive. Given a thread URL and one or more Drive folder paths, it fetches all messages, formats them as markdown, and uploads the file. Folders are created automatically. Re-running overwrites rather than duplicating.

## How to run the tool

```bash
uv run discord2drive "<thread_url>" "<drive_path>" ["<drive_path>" ...]
uv run discord2drive "<thread_url>" "<drive_path>" --dry-run
uv run discord2drive "<thread_url>" "<drive_path>" --output-local "<dir>"
```

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
| `config.py` | Loads credentials from `~/discord2drive/`, raises `ConfigError` with clear messages |
| `discord_client.py` | Discord REST API — parses thread URLs, fetches all messages (paginated) |
| `formatter.py` | Pure function: message list → markdown transcript string |
| `drive_client.py` | Google OAuth2, folder path resolution, file upload/overwrite |

## Credentials

All credentials live in `~/discord2drive/` — never in the project directory.

| File | Contents |
|---|---|
| `~/discord2drive/discord_token` | Discord bot token (plain text) |
| `~/discord2drive/google_creds.json` | OAuth client credentials (from Google Cloud Console) |
| `~/discord2drive/google_token.json` | OAuth token cache — auto-created on first run |
| `~/discord2drive/integ.json` | Integration test config — test thread URL (see below) |

## Integration tests

Integration tests require credentials in `~/discord2drive/` and hit real APIs. If any required file is absent (`discord_token`, `google_creds.json`, `integ.json`), the tests **fail** with a clear message — nothing silently skips. All credential checks live in `conftest.py` as session-scoped fixtures.

- `tests/integration/test_discord_live.py` — fetches the thread in `integ.json`, verifies messages and transcript
- `tests/integration/test_drive_live.py` — creates `discord2drive-test/` in Drive, uploads, verifies, then **deletes the folder on cleanup**
- `tests/integration/test_e2e.py` — runs the full CLI pipeline; uploads to `discord2drive-test/e2e`
- `tests/integration/conftest.py` — owns all credential loading; provides `discord_token`, `google_creds_path`, `google_token_path`, `integ_config`, and `test_thread_url` as session-scoped fixtures; fails with setup instructions if any file is missing

### integ.json format

```json
{
  "test_thread_url": "https://discord.com/channels/SERVER_ID/THREAD_ID"
}
```

Create a thread in any server the bot is in, paste a few messages, and drop its URL here. The tests make no assumptions about content — they only assert that messages are returned, a transcript is produced, and the upload succeeds.

## Discord API notes

- Thread URLs: `https://discord.com/channels/{server_id}/{thread_id}` — both `discord.com` and `discordapp.com` are supported
- Messages are returned newest-first by the API; `discord_client.py` reverses them
- Message type 21 = thread starter — real content is in `referenced_message`, not the message body itself
- Message type 4 = channel rename system event — skip it
- Empty messages (no content, no attachments) are skipped

## Google Drive notes

- Scope used: `https://www.googleapis.com/auth/drive` (full access — needed to find existing folders the app didn't create)
- `resolve_drive_path` walks a slash-separated path, creating any missing folders
- `upload_file` checks for an existing file with the same name in the target folder and updates it rather than creating a duplicate

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
- Google OAuth scope must be `drive` (not `drive.file`) — the narrower scope can't see folders the app didn't create, which silently creates duplicates instead of resolving existing paths.
- The Google Cloud OAuth consent screen must have the user added as a test user or the auth flow will be blocked.
- When adding a new Google client secret in Cloud Console, the JSON download is only available immediately after clicking **Add secret** — it's not accessible from the credentials list later.
- Discord's `discordapp.com` domain is a legacy alias for `discord.com` — both are handled by the URL parser.
