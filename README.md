# Discord2Drive

Export Discord thread transcripts to Google Docs. Point it at a thread URL — it fetches every message, formats them as a readable markdown transcript, auto-detects PC characters by embed color, and writes it as a **tab** inside each character's Google Doc. Running it again on the same thread updates the tab in place rather than creating a duplicate.

---

## Usage

```bash
uv run discord2drive <thread_url> [--dry-run] [--output-local <dir>]
uv run discord2drive <thread_url> --disable-parse-pcs <drive_path> [<drive_path> ...]
```

By default the tool auto-detects PCs and writes to the folder and docs configured in `settings.toml`. Use `--disable-parse-pcs` to write to explicit paths instead.

### Examples

Export a thread (auto-detects PCs, writes to configured folder):
```bash
uv run discord2drive "https://discord.com/channels/1234567890/9876543210"
```

This detects which characters in the thread are PCs (by their embed color), then writes the transcript to `folder/master` and to a doc for each PC — e.g. `masquerade/master`, `masquerade/Emilio Lopez`, `masquerade/Eva Kozlov`. The thread name becomes the tab name inside each doc.

Preview the transcript without writing anything:
```bash
uv run discord2drive \
  "https://discord.com/channels/1234567890/9876543210" \
  --dry-run
```

Save the transcript to a local file (use `--dry-run` to skip the Drive upload):
```bash
uv run discord2drive \
  "https://discord.com/channels/1234567890/9876543210" \
  --output-local ~/transcripts \
  --dry-run
```

Write to explicit Drive paths instead of auto-detecting PCs:
```bash
uv run discord2drive \
  "https://discord.com/channels/1234567890/9876543210" \
  --disable-parse-pcs \
  "masquerade/master" \
  "masquerade/Elara"
```

Drive paths use the format `folder/doc-name` — the folder is created if it doesn't exist, and the doc is created inside it if absent.

### Output format

Each transcript is written as a tab in the target Google Doc. Tab name = thread name. Content is markdown:

```markdown
# Scene - Elara and Davan in the Market

**Exported:** 2026-05-19
**Messages:** 42

---

**ChrisWriter** [2026-05-19 09:14 UTC]: Elara moved through the stalls without looking at him.

**MattWriter** [2026-05-19 09:15 UTC]: Davan caught her sleeve. "You knew, didn't you."
```

---

## Getting Started

### Prerequisites

**Python** — version 3.12 or higher is required.

- **macOS/Linux:** Python 3.12 is likely already installed. Check with `python3 --version`. If not, install via [python.org](https://www.python.org/downloads/) or your system package manager.
- **Windows:** Download and install from [python.org](https://www.python.org/downloads/). Check "Add Python to PATH" during installation.

**uv** — the package manager used to run the tool.

- **macOS/Linux:**
  ```bash
  curl -Ls https://astral.sh/uv/install.sh | sh
  ```
- **Windows (PowerShell):**
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

After installing uv, restart your terminal, then clone or download this repository and run the following inside it to install dependencies and register the `discord2drive` command:

```bash
cd Discord2Drive
uv pip install -e .
```

---

### Set Up the Discord Bot

The tool reads Discord threads via a bot. This is a one-time setup.

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications) and click **New Application**. Give it any name (e.g. `scene-exporter`).

2. In the left sidebar, click **Bot**.
   - Under **Privileged Gateway Intents**, enable **Server Members Intent** and **Message Content Intent**.
   - Click **Save Changes**.

3. Still on the Bot page, click **Reset Token**, then copy the token that appears. Paste it as `token` under `[discord]` in your `settings.toml`. Treat it like a password.

4. In the left sidebar, click **OAuth2 → URL Generator**.
   - Under **Scopes**, check `bot`.
   - Under **Bot Permissions**, check `Read Messages/View Channels` and `Read Message History`.
   - Copy the generated URL at the bottom and open it in your browser.
   - Select your server and click **Authorize**.

The bot will now appear in your server's member list. It must be in any server whose threads you want to export.

---

### Set Up Google Drive and Docs Access

The tool writes to Google Docs via a Google OAuth app. This is a one-time setup.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project (top bar → project dropdown → **New Project**).

2. With your project selected, go to **APIs & Services → Enable APIs and Services** and enable both:
   - **Google Drive API**
   - **Google Docs API**

3. Go to **APIs & Services → OAuth consent screen**:
   - User type: **External**
   - Fill in the app name and your email address, then click **Save and Continue** through the remaining steps.
   - On the **Scopes** step, click **Add or Remove Scopes** and add: `https://www.googleapis.com/auth/drive`
   - On the **Test users** step, add your Google account email address.

4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Desktop app**
   - Click **Create**.

5. In the credentials list, click the name of the client ID you just created. In the **Client secrets** section, click **Add secret**. When the new secret appears, note the **Client ID** and **Client secret** values — copy them into the `[google]` section of your `settings.toml`.

> **First run:** The first time you run the tool, it will open a browser window asking you to sign in to Google and grant access. After you approve, a token is cached locally and you won't be prompted again.

---

### Storing Credentials

Create a `discord2drive` folder in your home directory containing a single `settings.toml` file.

**macOS / Linux:** `~/discord2drive/`

**Windows:** `C:\Users\YourName\discord2drive\`

```
discord2drive/
    settings.toml       ← all configuration (see below)
    google_token.json   ← auto-created on first run, do not create manually
```

### settings.toml

Create `~/discord2drive/settings.toml` with the following content:

```toml
[discord]
token = "your-bot-token"

[google]
client_id = "xxx.apps.googleusercontent.com"
client_secret = "GOCSPX-..."

[auto_pc]                   # required for default auto-PC mode
folder = "masquerade"       # Drive folder containing all character docs
master = "master"           # name of the master Google Doc
color = "#4863A0"           # embed color that identifies PC characters
```

- `[discord] token` — your Discord bot token (from the Bot page in the developer portal)
- `[google] client_id` / `client_secret` — from the OAuth client you created in Google Cloud Console
- `[auto_pc]` — required for the default auto-PC mode; omit only if you always use `--disable-parse-pcs`

The `color` value is the hex embed color that identifies PC characters in Discord. PCs and NPCs typically have different colors set by the GM in the character bot.

The file `google_token.json` is created automatically the first time you authorize with Google. You do not need to create it yourself.

---

## Development

### Install dependencies

```bash
uv pip install -e .
```

This creates `.venv`, installs all dependencies, and registers the `discord2drive` command.

### Run the tests

```bash
# Unit tests only — no credentials needed
uv run pytest tests/ --ignore=tests/integration

# Full suite including live API calls (requires credentials in ~/discord2drive/)
uv run pytest tests/
```

The integration tests hit the real Discord, Google Drive, and Google Docs APIs. If any required config is absent, the tests **fail** with a clear message explaining exactly what to add. Nothing silently passes or skips.

### Integration test config

The integration tests need a test thread to run against. Add it to `~/discord2drive/settings.toml`:

```toml
[test]
thread_url = "https://discord.com/channels/SERVER_ID/THREAD_ID"
```

Create any thread in a server where your bot is present, post a few messages, then paste its URL here. Right-click the thread in Discord and choose **Copy Link** to get the URL. The tests make no assumptions about the thread's content.

### Test layout

```
tests/
    test_config.py               # config loading and validation
    test_discord_client.py       # URL parsing and message fetching (mocked)
    test_docs_client.py          # doc and tab operations (mocked)
    test_drive_client.py         # folder resolution (mocked)
    test_formatter.py            # transcript formatting (pure, no I/O)
    integration/
        conftest.py              # credential checks; discord_token, google_client_config, etc.
        test_discord_live.py     # fetches the test thread via real API
        test_docs_live.py        # creates a doc, writes tabs, and cleans up
        test_drive_live.py       # creates a folder, resolves paths, and cleans up
        test_e2e.py              # runs the full pipeline via the CLI
```

### Project structure

```
Discord2Drive/
    main.py              # CLI entry point
    config.py            # loads credentials from ~/discord2drive/settings.toml
    discord_client.py    # Discord REST API — fetches thread messages
    formatter.py         # converts messages to a markdown transcript
    drive_client.py      # Google Drive — folder resolution
    docs_client.py       # Google Docs — doc and tab management
    pyproject.toml       # dependencies and project metadata
    uv.lock              # locked dependency versions
    CLAUDE.md            # developer steering notes for Claude Code
```
