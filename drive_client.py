"""Uploads files to Google Drive via OAuth2."""

from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive"]

# Mime type used when creating folders in Drive
_FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveClientError(Exception):
    pass


def get_credentials(client_config: dict, token_cache: Path) -> Credentials:
    """
    Return valid OAuth2 credentials, refreshing or re-authorising as needed.
    On first run this opens a browser tab to complete the OAuth flow.
    The resulting token is cached at token_cache for subsequent runs.
    """
    creds: Credentials | None = None

    if token_cache.exists():
        creds = Credentials.from_authorized_user_file(str(token_cache), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

        token_cache.write_text(creds.to_json(), encoding="utf-8")

    return creds


def _drive_escape(value: str) -> str:
    """Escape a string for use in a Drive API query (single-quote delimiter)."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _resolve_or_create_folder(service, name: str, parent_id: str) -> str:
    """Return the Drive folder ID for `name` under `parent_id`, creating it if absent."""
    query = (
        f"name = '{_drive_escape(name)}' "
        f"and '{parent_id}' in parents "
        f"and mimeType = '{_FOLDER_MIME}' "
        f"and trashed = false"
    )
    try:
        results = (
            service.files()
            .list(q=query, fields="files(id, name)", spaces="drive")
            .execute()
        )
        files = results.get("files", [])
        if files:
            return files[0]["id"]

        folder = (
            service.files()
            .create(
                body={"name": name, "mimeType": _FOLDER_MIME, "parents": [parent_id]},
                fields="id",
            )
            .execute()
        )
        return folder["id"]
    except HttpError as e:
        raise DriveClientError(f"Drive API error resolving folder {name!r}: {e}") from e


def resolve_drive_path(service, path: str, root_id: str = "root") -> str:
    """
    Walk a slash-separated Drive folder path, creating any missing folders.
    Returns the ID of the final folder.

    Example: "Scenes/Characters/Elara" → ID of Elara folder (created if needed)
    """
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return root_id

    current_id = root_id
    for part in parts:
        current_id = _resolve_or_create_folder(service, part, current_id)
    return current_id



def build_service(client_config: dict, token_cache: Path):
    """Authenticate and return a Drive API service object."""
    creds = get_credentials(client_config, token_cache)
    try:
        return build("drive", "v3", credentials=creds)
    except HttpError as e:
        raise DriveClientError(f"Failed to connect to Google Drive API: {e}") from e
