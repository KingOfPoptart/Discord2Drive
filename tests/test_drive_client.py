"""Unit tests for drive_client.py — all Google API calls are mocked."""

from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from drive_client import (
    resolve_drive_path,
    upload_file,
    DriveClientError,
)


def _make_service(list_results: list[list[dict]] = None, create_ids: list[str] = None):
    """
    Build a mock Drive service.
    list_results: successive return values for files().list().execute()
    create_ids: successive folder IDs returned by files().create().execute()
    """
    service = MagicMock()
    list_results = list_results or []
    create_ids = create_ids or []

    list_call_count = 0
    create_call_count = 0

    def list_execute():
        nonlocal list_call_count
        result = list_results[min(list_call_count, len(list_results) - 1)]
        list_call_count += 1
        return {"files": result}

    def create_execute():
        nonlocal create_call_count
        fid = create_ids[min(create_call_count, len(create_ids) - 1)]
        create_call_count += 1
        return {"id": fid, "webViewLink": f"https://drive.google.com/file/d/{fid}/view"}

    service.files().list().execute.side_effect = list_execute
    service.files().create().execute.side_effect = create_execute
    service.files().update().execute.return_value = {
        "id": "existing-id",
        "webViewLink": "https://drive.google.com/file/d/existing-id/view",
    }

    return service


# --- resolve_drive_path ---

def test_empty_path_returns_root():
    service = _make_service()
    assert resolve_drive_path(service, "", "root") == "root"
    assert resolve_drive_path(service, "/", "root") == "root"


def test_single_folder_found():
    service = _make_service(list_results=[[{"id": "folder-abc", "name": "Scenes"}]])
    result = resolve_drive_path(service, "Scenes")
    assert result == "folder-abc"


def test_single_folder_created_when_missing():
    service = _make_service(list_results=[[]], create_ids=["new-folder-id"])
    result = resolve_drive_path(service, "Scenes")
    assert result == "new-folder-id"


def test_nested_path_resolves_each_level():
    service = _make_service(
        list_results=[
            [{"id": "id-scenes", "name": "Scenes"}],
            [{"id": "id-chars", "name": "Characters"}],
            [{"id": "id-elara", "name": "Elara"}],
        ]
    )
    result = resolve_drive_path(service, "Scenes/Characters/Elara")
    assert result == "id-elara"


def test_nested_path_creates_missing_levels():
    # Scenes exists, Characters and Elara do not
    service = _make_service(
        list_results=[
            [{"id": "id-scenes", "name": "Scenes"}],
            [],
            [],
        ],
        create_ids=["id-new-chars", "id-new-elara"],
    )
    result = resolve_drive_path(service, "Scenes/Characters/Elara")
    assert result == "id-new-elara"


def test_leading_and_trailing_slashes_ignored():
    service = _make_service(list_results=[[{"id": "folder-abc", "name": "Scenes"}]])
    result = resolve_drive_path(service, "/Scenes/")
    assert result == "folder-abc"


# --- upload_file ---

def test_upload_creates_new_file_when_none_exists():
    service = _make_service(list_results=[[]], create_ids=["new-file-id"])
    url = upload_file(service, "transcript.md", "# Hello", "folder-id")
    assert "new-file-id" in url
    service.files().create.assert_called()


def test_upload_updates_existing_file():
    service = MagicMock()
    service.files().list().execute.return_value = {"files": [{"id": "existing-id"}]}
    service.files().update().execute.return_value = {
        "id": "existing-id",
        "webViewLink": "https://drive.google.com/file/d/existing-id/view",
    }
    url = upload_file(service, "transcript.md", "# Updated", "folder-id")
    assert "existing-id" in url
    service.files().update.assert_called()


def test_upload_returns_web_view_link():
    service = _make_service(list_results=[[]], create_ids=["file-xyz"])
    url = upload_file(service, "transcript.md", "content", "folder-id")
    assert url.startswith("https://drive.google.com")


def test_upload_falls_back_to_constructed_url_if_no_link():
    service = MagicMock()
    service.files().list().execute.return_value = {"files": []}
    service.files().create().execute.return_value = {"id": "file-xyz"}
    url = upload_file(service, "transcript.md", "content", "folder-id")
    assert "file-xyz" in url
