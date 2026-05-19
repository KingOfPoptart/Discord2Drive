# Discord2Drive

Export Discord thread transcripts to Google Drive. Point it at a thread URL and one or more Drive folder paths — it fetches every message, formats them into a readable markdown document, and uploads it. Folders are created automatically if they don't exist. Running it again on the same thread overwrites the file rather than creating a duplicate.

---

## Usage

```bash
uv run discord2drive <thread_url> <drive_path> [drive_path ...]
```

### Examples

Export a thread to a single folder:
```bash
uv run discord2drive \
  "https://discord.com/channels/1234567890/9876543210" \
  "Scenes/Act 1"
```

Export to multiple folders at once (e.g. a master file and a character file):
```bash
uv run discord2drive \
  "https://discord.com/channels/1234567890/9876543210" \
  "Scenes/Master" \
  "Scenes/Characters/Elara"
```

Preview the transcript without uploading anything:
```bash
uv run discord2drive \
  "https://discord.com/channels/1234567890/9876543210" \
  "Scenes/Master" \
  --dry-run
```

### Output format

Each thread is saved as a markdown file named `{thread-name}_{date}.md`:

```markdown
# Scene - Elara and Davan in the Market

**Exported:** 2026-05-19
**Messages:** 42

---

**ChrisWriter** — 2026-05-19 09:14 UTC
Elara moved through the stalls without looking at him.

---

**MattWriter** — 2026-05-19 09:15 UTC
Davan caught her sleeve. "You knew, didn't you."

---
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

3. Still on the Bot page, click **Reset Token**, then copy the token that appears. You will need this in the credentials step below. Treat it like a password.

4. In the left sidebar, click **OAuth2 → URL Generator**.
   - Under **Scopes**, check `bot`.
   - Under **Bot Permissions**, check `Read Messages/View Channels` and `Read Message History`.
   - Copy the generated URL at the bottom and open it in your browser.
   - Select your server and click **Authorize**.

The bot will now appear in your server's member list. It must be in any server whose threads you want to export.

---

### Set Up Google Drive Access

The tool uploads files via a Google OAuth app. This is a one-time setup.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project (top bar → project dropdown → **New Project**).

2. With your project selected, go to **APIs & Services → Enable APIs and Services**, search for **Google Drive API**, and click **Enable**.

3. Go to **APIs & Services → OAuth consent screen**:
   - User type: **External**
   - Fill in the app name and your email address, then click **Save and Continue** through the remaining steps.
   - On the **Scopes** step, click **Add or Remove Scopes** and add: `https://www.googleapis.com/auth/drive`
   - On the **Test users** step, add your Google account email address.

4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Desktop app**
   - Click **Create**.

5. In the credentials list, click the name of the client ID you just created. In the **Client secrets** section, click **Add secret**. When the new secret appears, click **Download JSON** — this is only available at this moment.

6. Save the downloaded file as described in the credentials section below.

> **First run:** The first time you run the tool, it will open a browser window asking you to sign in to Google and grant access. After you approve, a token is cached locally and you won't be prompted again.

---

### Storing Credentials

Create a `discord2drive` folder in your home directory and place both credential files inside it.

**macOS / Linux:** `~/discord2drive/`

```
~/discord2drive/
    discord_token           ← paste your Discord bot token here (plain text, no quotes)
    google_creds.json       ← the JSON file downloaded from Google Cloud Console
    google_token.json       ← auto-created on first run, do not create manually
    integ.json              ← integration test config (developers only, see Development section)
```

To create the folder and token file from the terminal:
```bash
mkdir -p ~/discord2drive
echo "your-bot-token-here" > ~/discord2drive/discord_token
# then move your downloaded JSON:
mv ~/Downloads/client_secret_*.json ~/discord2drive/google_creds.json
```

---

**Windows:** `C:\Users\YourName\discord2drive\`

```
C:\Users\YourName\discord2drive\
    discord_token           ← paste your Discord bot token here (plain text, no quotes)
    google_creds.json       ← the JSON file downloaded from Google Cloud Console
    google_token.json       ← auto-created on first run, do not create manually
    integ.json              ← integration test config (developers only, see Development section)
```

To create the folder and token file from PowerShell:
```powershell
New-Item -ItemType Directory -Path "$HOME\discord2drive" -Force
"your-bot-token-here" | Out-File -FilePath "$HOME\discord2drive\discord_token" -Encoding utf8
# then move your downloaded JSON (adjust the filename as needed):
Move-Item "$HOME\Downloads\client_secret_*.json" "$HOME\discord2drive\google_creds.json"
```

---

The file `google_token.json` will be created automatically in the same folder the first time you authorize with Google. You do not need to create it yourself.

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

The integration tests hit the real Discord and Google Drive APIs. If any required file is absent — `discord_token`, `google_creds.json`, or `integ.json` — the tests **fail** with a clear message explaining exactly what to create and where. Nothing silently passes or skips.

### Integration test config

The integration tests need a test thread to run against. Create `~/discord2drive/integ.json`:

```json
{
  "test_thread_url": "https://discord.com/channels/SERVER_ID/THREAD_ID"
}
```

Create any thread in a server where your bot is present, post a few messages in it, then paste its URL here. Right-click the thread in Discord and choose **Copy Link** to get the URL. The tests make no assumptions about the thread's content — they only verify that messages are returned, a transcript is produced, and the upload succeeds.

### Test layout

```
tests/
    test_config.py               # config loading and validation
    test_discord_client.py       # URL parsing and message fetching (mocked)
    test_drive_client.py         # folder resolution and file upload (mocked)
    test_formatter.py            # transcript formatting (pure, no I/O)
    integration/
        conftest.py              # all credential checks; provides discord_token, google_creds_path, test_thread_url fixtures
        test_discord_live.py     # fetches the test thread from integ.json
        test_drive_live.py       # creates a folder, uploads, and cleans up
        test_e2e.py              # runs the full pipeline via the CLI
```

### Project structure

```
Discord2Drive/
    main.py              # CLI entry point
    config.py            # loads credentials from ~/discord2drive/
    discord_client.py    # Discord REST API — fetches thread messages
    formatter.py         # converts messages to a markdown transcript
    drive_client.py      # Google Drive — folder resolution and file upload
    pyproject.toml       # dependencies and project metadata
    uv.lock              # locked dependency versions
```
