"""
Integration test: hits the real Google Drive API.

Fails with setup instructions if any required config is absent.
Creates a test folder, verifies resolution, then cleans up.
"""

import pytest

from drive_client import build_service, resolve_drive_path

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
