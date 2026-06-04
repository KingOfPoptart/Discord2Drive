"""
Integration test: hits the real Google Drive API.

Fails with setup instructions if any required config is absent.
Creates a test folder, verifies resolution, then cleans up.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from google.oauth2.credentials import Credentials

from drive_client import SCOPES, build_service, get_credentials, resolve_drive_path

TEST_FOLDER = "discord2drive-test"


@pytest.fixture(scope="module")
def service(google_client_config, google_token_path):
    return build_service(google_client_config, google_token_path)


@pytest.fixture(scope="module")
def test_folder_id(service):
    folder_id = resolve_drive_path(service, TEST_FOLDER)
    yield folder_id
    service.files().delete(fileId=folder_id).execute()
    print(f"\nCleaned up test folder: {TEST_FOLDER}")


def test_authenticate(service):
    assert service is not None


def test_resolve_creates_folder(test_folder_id):
    assert test_folder_id
    assert len(test_folder_id) > 0


def test_resolve_is_idempotent(service, test_folder_id):
    second_id = resolve_drive_path(service, TEST_FOLDER)
    assert second_id == test_folder_id


def test_resolve_nested_path(service, test_folder_id):
    nested_id = resolve_drive_path(service, f"{TEST_FOLDER}/SubFolder")
    assert nested_id != test_folder_id


def test_get_credentials_reauths_on_invalid_grant(google_client_config, google_token_path, tmp_path):
    """
    Real invalid_grant from Google's token endpoint: verify the stale token file
    is deleted and the OAuth flow is re-run (browser mocked to avoid interaction).
    """
    fake_token = tmp_path / "stale_token.json"
    fake_token.write_text(
        json.dumps({
            "token": "ya29.fake-access-token",
            "refresh_token": "1//fake-refresh-token-that-is-expired",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": google_client_config["installed"]["client_id"],
            "client_secret": google_client_config["installed"]["client_secret"],
            "scopes": ["https://www.googleapis.com/auth/drive"],
            "expiry": "2020-01-01T00:00:00Z",
        }),
        encoding="utf-8",
    )

    real_creds = Credentials.from_authorized_user_file(str(google_token_path), SCOPES)

    with patch("drive_client.InstalledAppFlow") as mock_flow:
        mock_flow.from_client_config.return_value.run_local_server.return_value = real_creds
        result = get_credentials(google_client_config, fake_token)

    assert result is real_creds
    mock_flow.from_client_config.assert_called_once()
    saved = json.loads(fake_token.read_text(encoding="utf-8"))
    assert saved.get("refresh_token") != "1//fake-refresh-token-that-is-expired"
