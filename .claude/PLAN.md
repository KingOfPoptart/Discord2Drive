# Discord2Drive — Implementation Plan

## Goal
CLI tool: takes a Discord thread URL + one or more Google Drive folder paths, exports the full thread as a formatted markdown transcript, uploads to each destination.

## Workspace
~/Discord2Drive — all work happens here.

## Credentials
- Discord bot token: ~/.sceneexporterauthtoken
- Google OAuth credentials: ~/.discord2drive_google_creds.json
- Google token cache (auto-created on first run): ~/.discord2drive_google_token.json
- Test thread: https://discordapp.com/channels/1309606609080811531/1506288385826885632

## Project Structure
```
Discord2Drive/
├── PLAN.md
├── main.py                  # CLI entry point
├── config.py                # Credential loading and validation
├── discord_client.py        # Discord REST API — fetch thread messages
├── formatter.py             # Message list → markdown transcript
├── drive_client.py          # Google Drive upload
├── .env.example
└── tests/
    ├── test_formatter.py        # Pure unit tests
    ├── test_discord_client.py   # Mocked HTTP tests
    ├── test_drive_client.py     # Mocked Google API tests
    └── integration/
        └── test_e2e.py          # Live end-to-end test
```

## Phases

### Phase 1 — Discord ✅
- [x] Project scaffold (uv, pyproject.toml, .venv)
- [x] discord_client.py — parse URL, fetch all messages (paginated), handle message types
- [x] formatter.py — messages → markdown
- [x] tests/test_formatter.py
- [x] tests/test_discord_client.py (mocked)
- [x] Integration: hit real test thread, verified transcript matches Discord

### Phase 2 — Google Drive (current)
- [x] drive_client.py — OAuth2, folder resolution, file upload
- [x] tests/test_drive_client.py (mocked)
- [ ] Integration: upload test transcript, verify via Drive API

### Phase 3 — CLI + Config
- [ ] config.py — load creds from file or env vars
- [ ] main.py — argparse CLI, wire all modules
- [ ] .env.example
- [ ] End-to-end integration test

## Discord URL Format
https://discord.com/channels/{SERVER_ID}/{THREAD_ID}
https://discordapp.com/channels/{SERVER_ID}/{THREAD_ID}  ← legacy, same IDs

Test:
- Server ID:  1309606609080811531
- Thread ID:  1506288385826885632

## Key Technical Notes
- Discord REST API: GET /channels/{thread_id}/messages?limit=100&before={last_id}
- Pagination: loop until response has < 100 messages
- Bot must be in the server with READ_MESSAGE_HISTORY permission
- Message type 21 = thread starter; real content is in referenced_message
- Message type 4 = channel rename system event; skip it
- Google OAuth scope: https://www.googleapis.com/auth/drive (full access needed to find existing folders)

## One-Time Setup

### Discord Bot
1. Go to discord.com/developers/applications → New Application
2. Bot tab → Add Bot
3. Enable **Message Content Intent** and **Server Members Intent** under Privileged Gateway Intents
4. Copy the bot token → save to ~/.sceneexporterauthtoken
5. OAuth2 → URL Generator → scope: `bot`, permission: `Read Message History`
6. Open the generated URL → invite bot to your server

### Google Drive
1. Go to console.cloud.google.com → create a project
2. APIs & Services → Enable APIs → search **Google Drive API** → Enable
3. APIs & Services → OAuth consent screen:
   - User type: External
   - Fill in app name and your email
   - Scopes → Add: `https://www.googleapis.com/auth/drive`
   - Test users → add your Google account email
4. APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Desktop app**
5. On the credentials list page, click the name of your new client ID
6. In the Client secrets section, click **Add secret**
7. When the new secret appears, click **Download JSON** (only available at this moment)
8. Move the downloaded file: `mv ~/Downloads/client_secret_*.json ~/.discord2drive_google_creds.json`
9. First run will open a browser to complete OAuth — token is cached automatically after that
