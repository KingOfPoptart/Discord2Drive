"""Live integration tests for docs_client.py — hits real Google APIs."""

import pytest

from docs_client import build_docs_service, find_or_create_doc, upsert_tab
from drive_client import build_service, resolve_drive_path

TEST_FOLDER = "discord2drive-test"
TEST_DOC = "docs-client-live-test"


@pytest.fixture(scope="module")
def drive_service(google_client_config, google_token_path):
    return build_service(google_client_config, google_token_path)


@pytest.fixture(scope="module")
def docs_service(google_client_config, google_token_path):
    return build_docs_service(google_client_config, google_token_path)


@pytest.fixture(scope="module")
def folder_id(drive_service):
    return resolve_drive_path(drive_service, TEST_FOLDER)


@pytest.fixture(scope="module")
def doc_id(drive_service, folder_id):
    return find_or_create_doc(drive_service, TEST_DOC, folder_id)


@pytest.fixture(scope="module", autouse=True)
def cleanup(drive_service, doc_id):
    yield
    drive_service.files().delete(fileId=doc_id).execute()
    print(f"\nCleaned up doc {TEST_DOC!r}")


def test_find_or_create_returns_id(doc_id):
    assert doc_id


def test_find_or_create_is_idempotent(drive_service, folder_id, doc_id):
    second_id = find_or_create_doc(drive_service, TEST_DOC, folder_id)
    assert second_id == doc_id


def test_upsert_tab_returns_docs_url(docs_service, doc_id):
    url = upsert_tab(docs_service, doc_id, "First Tab", "Hello, World!")
    assert "docs.google.com" in url
    assert doc_id in url


def test_upsert_tab_overwrites_content(docs_service, doc_id):
    upsert_tab(docs_service, doc_id, "First Tab", "First version")
    url = upsert_tab(docs_service, doc_id, "First Tab", "Second version")
    assert "docs.google.com" in url


def test_upsert_second_tab(docs_service, doc_id):
    url = upsert_tab(docs_service, doc_id, "Second Tab", "Different content")
    assert "docs.google.com" in url
