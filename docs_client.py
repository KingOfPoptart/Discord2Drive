"""Writes transcript content to Google Docs tabs via the Docs API v1."""

from __future__ import annotations

from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from drive_client import get_credentials

_DOC_MIME = "application/vnd.google-apps.document"


class DocsClientError(Exception):
    pass


def build_docs_service(client_config: dict, token_cache: Path):
    """Authenticate and return a Google Docs API service object."""
    creds = get_credentials(client_config, token_cache)
    try:
        return build("docs", "v1", credentials=creds, cache_discovery=False)
    except HttpError as e:
        raise DocsClientError(f"Failed to connect to Google Docs API: {e}") from e


def find_or_create_doc(drive_service, doc_name: str, folder_id: str) -> str:
    """
    Find a Google Doc named doc_name in folder_id, or create it.
    Returns the document ID.
    """
    escaped = doc_name.replace("\\", "\\\\").replace("'", "\\'")
    query = (
        f"name = '{escaped}' "
        f"and '{folder_id}' in parents "
        f"and mimeType = '{_DOC_MIME}' "
        f"and trashed = false"
    )
    try:
        results = drive_service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])
        if files:
            return files[0]["id"]
        doc = drive_service.files().create(
            body={"name": doc_name, "mimeType": _DOC_MIME, "parents": [folder_id]},
            fields="id",
        ).execute()
        return doc["id"]
    except HttpError as e:
        raise DocsClientError(f"Drive API error for doc {doc_name!r}: {e}") from e


def upsert_tab(docs_service, doc_id: str, tab_name: str, content: str) -> str:
    """
    Create or overwrite a tab named tab_name in the given doc.
    - Tab exists, multiple tabs: delete and recreate for a clean slate.
    - Tab exists, only tab: clear content in place (can't delete the last tab).
    - New tab: create it, then delete Google's default "Tab 1" if present anywhere
      in the doc (catches both fresh docs and orphaned Tab 1s from earlier writes).
    Returns the doc's web URL.
    """
    try:
        doc = docs_service.documents().get(
            documentId=doc_id, includeTabsContent=True
        ).execute()
    except HttpError as e:
        raise DocsClientError(f"Could not read doc {doc_id!r}: {e}") from e

    tabs = doc.get("tabs", [])
    existing_tab = next(
        (t for t in tabs if t.get("tabProperties", {}).get("title") == tab_name),
        None,
    )

    if existing_tab is not None:
        old_tab_id = existing_tab["tabProperties"]["tabId"]
        if len(tabs) > 1:
            # Delete and recreate — cleanest overwrite
            _batch(docs_service, doc_id, [{"deleteTab": {"tabId": old_tab_id}}])
            reply = _batch(docs_service, doc_id, [
                {"addDocumentTab": {"tabProperties": {"title": tab_name}}}
            ])
            tab_id = reply["replies"][0]["addDocumentTab"]["tabProperties"]["tabId"]
        else:
            # Only tab — cannot delete it; clear content instead
            tab_id = old_tab_id
            body_content = (
                existing_tab.get("documentTab", {}).get("body", {}).get("content", [])
            )
            end_index = body_content[-1]["endIndex"] if body_content else 1
            if end_index > 1:
                _batch(docs_service, doc_id, [{
                    "deleteContentRange": {
                        "range": {
                            "startIndex": 1,
                            "endIndex": end_index - 1,
                            "tabId": tab_id,
                        }
                    }
                }])
    else:
        # New tab — create it, then delete Google's default "Tab 1" if still present.
        # We scan all tabs (not just sole tab) so orphaned Tab 1s get cleaned up too.
        reply = _batch(docs_service, doc_id, [
            {"addDocumentTab": {"tabProperties": {"title": tab_name}}}
        ])
        tab_id = reply["replies"][0]["addDocumentTab"]["tabProperties"]["tabId"]
        default_tab_id = _find_default_tab(tabs)
        if default_tab_id:
            _batch(docs_service, doc_id, [{"deleteTab": {"tabId": default_tab_id}}])

    _batch(docs_service, doc_id, [{
        "insertText": {
            "location": {"index": 1, "tabId": tab_id},
            "text": content,
        }
    }])

    return f"https://docs.google.com/document/d/{doc_id}/edit"


def _find_default_tab(tabs: list) -> str | None:
    """Return tabId of Google's default empty tab if present among tabs, else None.

    Google titles new-doc tabs "Tab 1" with a minimal body (endIndex ≤ 2).
    Checking both title and size avoids deleting a user-renamed or content-filled tab.
    """
    for tab in tabs:
        props = tab.get("tabProperties", {})
        if props.get("title") != "Tab 1":
            continue
        body_content = tab.get("documentTab", {}).get("body", {}).get("content", [])
        end_index = body_content[-1]["endIndex"] if body_content else 1
        if end_index <= 2:
            return props["tabId"]
    return None


def _batch(docs_service, doc_id: str, requests: list) -> dict:
    try:
        return docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests},
        ).execute()
    except HttpError as e:
        raise DocsClientError(f"Docs API error: {e}") from e
