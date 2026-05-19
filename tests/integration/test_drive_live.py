"""
Integration test: hits the real Google Drive API.

Fails with setup instructions if any required config is absent.
Creates a test folder, uploads a file, verifies it, then cleans up.
"""

import pytest
from pathlib import Path

from drive_client import build_service, resolve_drive_path, upload_file

TEST_FOLDER = "discord2drive-test"
TEST_FILENAME = "test-transcript.md"
TEST_CONTENT = "# Test Thread\n\n**TestUser** — 2026-05-19 12:00 UTC\nThis is a test upload.\n"


@pytest.fixture(scope="module")
def service(google_client_config, google_token_path):
    return build_service(google_client_config, google_token_path)


@pytest.fixture(scope="module")
def test_folder_id(service):
    """Create the test folder and clean it up after all tests in this module."""
    folder_id = resolve_drive_path(service, TEST_FOLDER)
    yield folder_id
    service.files().delete(fileId=folder_id).execute()
    print(f"\nCleaned up test folder: {TEST_FOLDER}")


def test_authenticate(service):
    assert service is not None


def test_resolve_creates_folder(test_folder_id):
    assert test_folder_id is not None
    assert len(test_folder_id) > 0


def test_resolve_nested_path(service, test_folder_id):
    nested_id = resolve_drive_path(service, f"{TEST_FOLDER}/SubFolder")
    assert nested_id != test_folder_id


def test_upload_file(service, test_folder_id):
    url = upload_file(service, TEST_FILENAME, TEST_CONTENT, test_folder_id)
    assert url.startswith("https://")
    print(f"\nUploaded file URL: {url}")


def test_upload_overwrites_existing(service, test_folder_id):
    updated_content = TEST_CONTENT + "\n**TestUser** — 2026-05-19 12:01 UTC\nUpdated message.\n"
    url = upload_file(service, TEST_FILENAME, updated_content, test_folder_id)
    assert url.startswith("https://")

    results = (
        service.files()
        .list(
            q=f"name = '{TEST_FILENAME}' and '{test_folder_id}' in parents and trashed = false",
            fields="files(id)",
        )
        .execute()
    )
    assert len(results.get("files", [])) == 1
