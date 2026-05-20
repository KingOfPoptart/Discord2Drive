"""Unit tests for drive_client.py — all Google API calls are mocked."""

from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from drive_client import (
    resolve_drive_path,
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
        return {"id": fid}

    service.files().list().execute.side_effect = list_execute
    service.files().create().execute.side_effect = create_execute

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


def test_folder_name_with_single_quote():
    service = _make_service(list_results=[[{"id": "folder-id", "name": "Chris's Notes"}]])
    result = resolve_drive_path(service, "Chris's Notes")
    assert result == "folder-id"
