"""Unit tests for docs_client.py — all Google API calls are mocked."""

from unittest.mock import MagicMock
import pytest

from googleapiclient.errors import HttpError

from docs_client import (
    find_or_create_doc,
    upsert_tab,
    DocsClientError,
)


def _http_error(status: int) -> HttpError:
    resp = MagicMock()
    resp.status = status
    return HttpError(resp=resp, content=b"error")


# --- helpers ---

def _tab(tab_id: str, title: str, end_index: int = 10) -> dict:
    return {
        "tabProperties": {"tabId": tab_id, "title": title},
        "documentTab": {"body": {"content": [{"endIndex": end_index}]}},
    }



def _empty_tab(tab_id: str, title: str = "Tab 1") -> dict:
    return {
        "tabProperties": {"tabId": tab_id, "title": title},
        "documentTab": {"body": {"content": [{"endIndex": 1}]}},
    }


def _create_tab_reply(tab_id: str) -> dict:
    return {"replies": [{"addDocumentTab": {"tabProperties": {"tabId": tab_id}}}]}


def _make_drive_service(existing_id: str | None = None, new_id: str = "new-doc-id"):
    service = MagicMock()
    if existing_id:
        service.files().list().execute.return_value = {"files": [{"id": existing_id}]}
    else:
        service.files().list().execute.return_value = {"files": []}
        service.files().create().execute.return_value = {"id": new_id}
    return service


def _make_docs_service(tabs: list, batch_replies: list | None = None):
    service = MagicMock()
    service.documents().get().execute.return_value = {"tabs": tabs}
    if batch_replies is not None:
        service.documents().batchUpdate().execute.side_effect = batch_replies
    else:
        service.documents().batchUpdate().execute.return_value = {"replies": [{}]}
    return service


# --- find_or_create_doc ---

def test_find_or_create_returns_existing_id():
    service = _make_drive_service(existing_id="doc-abc")
    assert find_or_create_doc(service, "My Doc", "folder-id") == "doc-abc"
    service.files().create.assert_not_called()


def test_find_or_create_creates_when_missing():
    service = _make_drive_service(new_id="created-doc-id")
    assert find_or_create_doc(service, "New Doc", "folder-id") == "created-doc-id"


def test_find_or_create_raises_on_http_error():
    service = MagicMock()
    service.files().list().execute.side_effect = _http_error(500)
    with pytest.raises(DocsClientError):
        find_or_create_doc(service, "Doc", "folder-id")


# --- upsert_tab ---

def test_upsert_new_tab_in_fresh_doc():
    """New tab in a doc with one empty default 'Tab 1': create tab, delete default, insert."""
    service = _make_docs_service(
        tabs=[_empty_tab("default-id")],
        batch_replies=[
            _create_tab_reply("new-tab-id"),  # addDocumentTab
            {"replies": [{}]},                 # deleteTab (default)
            {"replies": [{}]},                 # insertText
        ],
    )
    url = upsert_tab(service, "doc-id", "Scene 1", "content here")
    assert "docs.google.com" in url
    assert "doc-id" in url


def test_upsert_new_tab_cleans_up_orphaned_default_tab():
    """New tab added to doc that already has a content tab AND an orphaned 'Tab 1': delete Tab 1."""
    service = _make_docs_service(
        tabs=[
            _tab("content-tab", "Scene 1"),
            _empty_tab("orphan-id"),
        ],
        batch_replies=[
            _create_tab_reply("new-tab-id"),  # addDocumentTab
            {"replies": [{}]},                 # deleteTab (orphan)
            {"replies": [{}]},                 # insertText
        ],
    )
    url = upsert_tab(service, "doc-id", "Scene 2", "new content")
    assert "docs.google.com" in url


def test_upsert_new_tab_in_existing_doc():
    """New tab in a doc that has a non-empty tab (no 'Tab 1'): create tab, insert only."""
    service = _make_docs_service(
        tabs=[_tab("existing-tab", "Old Tab")],
        batch_replies=[
            _create_tab_reply("new-tab-id"),
            {"replies": [{}]},
        ],
    )
    url = upsert_tab(service, "doc-id", "Scene 2", "new content")
    assert "docs.google.com" in url


def test_upsert_existing_tab_multiple_tabs():
    """Existing tab with siblings: delete old, create fresh, insert."""
    service = _make_docs_service(
        tabs=[
            _tab("tab-a", "Scene 1"),
            _tab("tab-b", "Scene 2"),
        ],
        batch_replies=[
            {"replies": [{}]},
            _create_tab_reply("tab-a-new"),
            {"replies": [{}]},
        ],
    )
    url = upsert_tab(service, "doc-id", "Scene 1", "updated content")
    assert "docs.google.com" in url


def test_upsert_existing_tab_only_tab():
    """Existing tab that is the only tab: clear content, insert fresh."""
    service = _make_docs_service(
        tabs=[_tab("only-tab", "Scene 1", end_index=50)],
        batch_replies=[
            {"replies": [{}]},
            {"replies": [{}]},
        ],
    )
    url = upsert_tab(service, "doc-id", "Scene 1", "replaced content")
    assert "docs.google.com" in url


def test_upsert_raises_on_get_error():
    service = MagicMock()
    service.documents().get().execute.side_effect = _http_error(403)
    with pytest.raises(DocsClientError, match="Could not read"):
        upsert_tab(service, "bad-doc", "Tab", "content")


def test_upsert_raises_on_batch_error():
    service = _make_docs_service(
        tabs=[_empty_tab("default-id")],
        batch_replies=[_http_error(500)],
    )
    with pytest.raises(DocsClientError):
        upsert_tab(service, "doc-id", "Tab", "content")
