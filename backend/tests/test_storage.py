import os
import pytest
from unittest.mock import patch


@pytest.fixture
def local_storage(tmp_path):
    with patch("app.services.storage.settings") as mock_settings:
        mock_settings.storage_backend = "local"
        mock_settings.storage_local_root = str(tmp_path)
        mock_settings.s3_bucket = ""
        mock_settings.s3_endpoint_url = ""
        mock_settings.s3_access_key = ""
        mock_settings.s3_secret_key = ""
        from app.services.storage import StorageService
        yield StorageService()


def test_local_save_and_read(local_storage, tmp_path):
    content = b"hello world"
    key = "test/file.txt"
    local_storage.save(key, content)
    assert local_storage.exists(key)


def test_local_delete(local_storage):
    content = b"data"
    key = "test/delete.txt"
    local_storage.save(key, content)
    local_storage.delete(key)
    assert not local_storage.exists(key)


def test_local_url(local_storage):
    key = "test/url.txt"
    local_storage.save(key, b"x")
    url = local_storage.url(key)
    assert key in url
