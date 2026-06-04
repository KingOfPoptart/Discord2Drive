"""Unit tests for drive_client.py — all Google API calls are mocked."""

from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest
from google.auth.exceptions import RefreshError

from drive_client import (
    get_credentials,
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


# --- get_credentials ---

CLIENT_CONFIG = {"installed": {"client_id": "x", "client_secret": "y"}}


@patch("drive_client.InstalledAppFlow")
@patch("drive_client.Request")
@patch("drive_client.Credentials")
def test_get_credentials_valid_uses_cached_creds(mock_creds_cls, mock_request, mock_flow, tmp_path):
    token_file = tmp_path / "token.json"
    token_file.write_text("{}")

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds_cls.from_authorized_user_file.return_value = mock_creds

    result = get_credentials(CLIENT_CONFIG, token_file)

    assert result is mock_creds
    mock_creds.refresh.assert_not_called()
    mock_flow.from_client_config.assert_not_called()


@patch("drive_client.InstalledAppFlow")
@patch("drive_client.Request")
@patch("drive_client.Credentials")
def test_get_credentials_expired_refreshes_successfully(mock_creds_cls, mock_request, mock_flow, tmp_path):
    token_file = tmp_path / "token.json"
    token_file.write_text("{}")

    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "rtoken"
    mock_creds.to_json.return_value = '{"refreshed": true}'

    def _refresh(_req):
        mock_creds.valid = True

    mock_creds.refresh.side_effect = _refresh
    mock_creds_cls.from_authorized_user_file.return_value = mock_creds

    result = get_credentials(CLIENT_CONFIG, token_file)

    assert result is mock_creds
    mock_creds.refresh.assert_called_once()
    mock_flow.from_client_config.assert_not_called()
    assert token_file.read_text() == '{"refreshed": true}'


@patch("drive_client.InstalledAppFlow")
@patch("drive_client.Request")
@patch("drive_client.Credentials")
def test_get_credentials_invalid_grant_reauths(mock_creds_cls, mock_request, mock_flow, tmp_path):
    token_file = tmp_path / "token.json"
    token_file.write_text("{}")

    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "rtoken"
    mock_creds.refresh.side_effect = RefreshError("invalid_grant: Token has been expired or revoked.")
    mock_creds_cls.from_authorized_user_file.return_value = mock_creds

    new_creds = MagicMock()
    new_creds.to_json.return_value = '{"new": true}'
    mock_flow.from_client_config.return_value.run_local_server.return_value = new_creds

    result = get_credentials(CLIENT_CONFIG, token_file)

    assert result is new_creds
    assert not token_file.exists() or token_file.read_text() == '{"new": true}'
    mock_flow.from_client_config.assert_called_once_with(CLIENT_CONFIG, ["https://www.googleapis.com/auth/drive"])
    mock_flow.from_client_config.return_value.run_local_server.assert_called_once_with(port=0)
    assert token_file.read_text() == '{"new": true}'
