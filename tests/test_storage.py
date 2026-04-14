import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.storage import (
    BackblazeB2StorageBackend,
    LocalStorageBackend,
    MinIOStorageBackend,
    StorageError,
    get_storage_backend,
)


# ---------------------------------------------------------------------------
# LocalStorageBackend Tests
# ---------------------------------------------------------------------------

class TestLocalStorageBackend:
    def test_save_creates_file(self, tmp_path):
        backend = LocalStorageBackend(upload_dir=str(tmp_path))
        content = b"test file content"
        storage_path = backend.save(content, "test.pdf")

        assert os.path.exists(storage_path)
        with open(storage_path, "rb") as f:
            assert f.read() == content

    def test_save_generates_unique_name(self, tmp_path):
        backend = LocalStorageBackend(upload_dir=str(tmp_path))
        path1 = backend.save(b"content1", "doc.pdf")
        path2 = backend.save(b"content2", "doc.pdf")

        assert path1 != path2

    def test_save_preserves_extension(self, tmp_path):
        backend = LocalStorageBackend(upload_dir=str(tmp_path))
        path = backend.save(b"content", "invoice.pdf")
        assert path.endswith(".pdf")

    def test_get_returns_content(self, tmp_path):
        backend = LocalStorageBackend(upload_dir=str(tmp_path))
        content = b"hello world"
        path = backend.save(content, "test.txt")

        retrieved = backend.get(path)
        assert retrieved == content

    def test_get_nonexistent_raises_error(self, tmp_path):
        backend = LocalStorageBackend(upload_dir=str(tmp_path))
        with pytest.raises(StorageError, match="File not found"):
            backend.get("/nonexistent/file.pdf")

    def test_delete_removes_file(self, tmp_path):
        backend = LocalStorageBackend(upload_dir=str(tmp_path))
        path = backend.save(b"content", "test.pdf")
        assert os.path.exists(path)

        backend.delete(path)
        assert not os.path.exists(path)

    def test_delete_nonexistent_no_error(self, tmp_path):
        backend = LocalStorageBackend(upload_dir=str(tmp_path))
        backend.delete("/nonexistent/file.pdf")  # Should not raise

    def test_get_local_path_returns_same_path(self, tmp_path):
        backend = LocalStorageBackend(upload_dir=str(tmp_path))
        path = backend.save(b"content", "test.pdf")

        local_path = backend.get_local_path(path)
        assert local_path == path

    def test_get_local_path_nonexistent_raises(self, tmp_path):
        backend = LocalStorageBackend(upload_dir=str(tmp_path))
        with pytest.raises(StorageError, match="File not found"):
            backend.get_local_path("/nonexistent/file.pdf")

    def test_creates_upload_dir_if_missing(self, tmp_path):
        new_dir = tmp_path / "nested" / "uploads"
        assert not new_dir.exists()

        backend = LocalStorageBackend(upload_dir=str(new_dir))
        assert new_dir.exists()

    def test_save_empty_content(self, tmp_path):
        backend = LocalStorageBackend(upload_dir=str(tmp_path))
        path = backend.save(b"", "empty.pdf")
        assert os.path.exists(path)
        assert os.path.getsize(path) == 0

    def test_save_large_content(self, tmp_path):
        backend = LocalStorageBackend(upload_dir=str(tmp_path))
        content = b"x" * (10 * 1024 * 1024)  # 10MB
        path = backend.save(content, "large.pdf")
        assert backend.get(path) == content


# ---------------------------------------------------------------------------
# MinIOStorageBackend Tests (mocked)
# ---------------------------------------------------------------------------

class TestMinIOStorageBackend:
    @patch("app.services.storage.Minio")
    def _make_backend(self, mock_minio_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_client

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.MINIO_ENDPOINT = "localhost:9000"
            mock_settings.MINIO_ACCESS_KEY = "test"
            mock_settings.MINIO_SECRET_KEY = "test"
            mock_settings.MINIO_BUCKET = "test-bucket"
            mock_settings.MINIO_SECURE = False
            mock_settings.UPLOAD_DIR = str(tmp_path)

            backend = MinIOStorageBackend(
                endpoint="localhost:9000",
                access_key="test",
                secret_key="test",
                bucket="test-bucket",
                secure=False,
            )
        return backend, mock_client

    @patch("app.services.storage.Minio")
    def test_creates_bucket_if_missing(self, mock_minio_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_minio_cls.return_value = mock_client

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            MinIOStorageBackend(
                endpoint="localhost:9000",
                access_key="test",
                secret_key="test",
                bucket="my-bucket",
                secure=False,
            )

        mock_client.make_bucket.assert_called_once_with("my-bucket")

    def test_save_calls_put_object(self, tmp_path):
        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        content = b"file data"

        key = backend.save(content, "invoice.pdf")

        mock_client.put_object.assert_called_once()
        call_args = mock_client.put_object.call_args
        assert call_args[0][0] == "test-bucket"  # bucket
        assert key.endswith(".pdf")
        assert call_args[1]["length"] == len(content)

    def test_save_raises_storage_error_on_failure(self, tmp_path):
        from minio.error import S3Error

        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_client.put_object.side_effect = S3Error(
            "PutObject", "test-bucket", "", "", "", "", ""
        )

        with pytest.raises(StorageError, match="Failed to upload"):
            backend.save(b"data", "test.pdf")

    def test_get_returns_content(self, tmp_path):
        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_response = MagicMock()
        mock_response.read.return_value = b"file content"
        mock_client.get_object.return_value = mock_response

        data = backend.get("some-key.pdf")

        assert data == b"file content"
        mock_client.get_object.assert_called_once_with("test-bucket", "some-key.pdf")
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()

    def test_get_raises_storage_error_on_failure(self, tmp_path):
        from minio.error import S3Error

        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_client.get_object.side_effect = S3Error(
            "GetObject", "test-bucket", "", "", "", "", ""
        )

        with pytest.raises(StorageError, match="Failed to retrieve"):
            backend.get("missing-key.pdf")

    def test_delete_calls_remove_object(self, tmp_path):
        backend, mock_client = self._make_backend(tmp_path=tmp_path)

        backend.delete("some-key.pdf")

        mock_client.remove_object.assert_called_once_with("test-bucket", "some-key.pdf")

    def test_delete_raises_storage_error_on_failure(self, tmp_path):
        from minio.error import S3Error

        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_client.remove_object.side_effect = S3Error(
            "RemoveObject", "test-bucket", "", "", "", "", ""
        )

        with pytest.raises(StorageError, match="Failed to delete"):
            backend.delete("some-key.pdf")

    def test_get_local_path_downloads_to_temp(self, tmp_path):
        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_response = MagicMock()
        mock_response.read.return_value = b"pdf content"
        mock_client.get_object.return_value = mock_response

        local_path = backend.get_local_path("doc.pdf")

        assert os.path.exists(local_path)
        with open(local_path, "rb") as f:
            assert f.read() == b"pdf content"

    def test_get_local_path_uses_cache(self, tmp_path):
        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_response = MagicMock()
        mock_response.read.return_value = b"pdf content"
        mock_client.get_object.return_value = mock_response

        path1 = backend.get_local_path("doc.pdf")
        path2 = backend.get_local_path("doc.pdf")

        assert path1 == path2
        # Only one download call because second is cached
        mock_client.get_object.assert_called_once()

    def test_guess_content_type(self, tmp_path):
        assert MinIOStorageBackend._guess_content_type(".pdf") == "application/pdf"
        assert MinIOStorageBackend._guess_content_type(".png") == "image/png"
        assert MinIOStorageBackend._guess_content_type(".jpg") == "image/jpeg"
        assert MinIOStorageBackend._guess_content_type(".docx") == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert MinIOStorageBackend._guess_content_type(".xyz") == "application/octet-stream"


# ---------------------------------------------------------------------------
# BackblazeB2StorageBackend Tests (mocked)
# ---------------------------------------------------------------------------

class TestBackblazeB2StorageBackend:
    @patch("app.services.storage.Minio")
    def _make_backend(self, mock_minio_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_client

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.B2_ENDPOINT = "s3.us-east-005.backblazeb2.com"
            mock_settings.B2_KEY_ID = "test-key-id"
            mock_settings.B2_APPLICATION_KEY = "test-app-key"
            mock_settings.B2_BUCKET = "DP-B01"
            mock_settings.B2_SECURE = True
            mock_settings.UPLOAD_DIR = str(tmp_path)

            backend = BackblazeB2StorageBackend(
                endpoint="s3.us-east-005.backblazeb2.com",
                key_id="test-key-id",
                application_key="test-app-key",
                bucket="DP-B01",
                secure=True,
            )
        return backend, mock_client

    @patch("app.services.storage.Minio")
    def test_verify_bucket_exists(self, mock_minio_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_client

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            backend = BackblazeB2StorageBackend(
                endpoint="s3.us-east-005.backblazeb2.com",
                key_id="test-key-id",
                application_key="test-app-key",
                bucket="DP-B01",
                secure=True,
            )

        mock_client.bucket_exists.assert_called_once_with("DP-B01")

    @patch("app.services.storage.Minio")
    def test_verify_bucket_missing_raises_error(self, mock_minio_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_minio_cls.return_value = mock_client

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            with pytest.raises(StorageError, match="does not exist"):
                BackblazeB2StorageBackend(
                    endpoint="s3.us-east-005.backblazeb2.com",
                    key_id="test-key-id",
                    application_key="test-app-key",
                    bucket="DP-B01",
                    secure=True,
                )

    def test_save_calls_put_object(self, tmp_path):
        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        content = b"file data"

        key = backend.save(content, "invoice.pdf")

        mock_client.put_object.assert_called_once()
        call_args = mock_client.put_object.call_args
        assert call_args[0][0] == "DP-B01"
        assert key.endswith(".pdf")
        assert call_args[1]["length"] == len(content)

    def test_save_raises_storage_error_on_failure(self, tmp_path):
        from minio.error import S3Error

        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_client.put_object.side_effect = S3Error(
            "PutObject", "DP-B01", "", "", "", "", ""
        )

        with pytest.raises(StorageError, match="Failed to upload to B2"):
            backend.save(b"data", "test.pdf")

    def test_get_returns_content(self, tmp_path):
        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_response = MagicMock()
        mock_response.read.return_value = b"file content"
        mock_client.get_object.return_value = mock_response

        data = backend.get("some-key.pdf")

        assert data == b"file content"
        mock_client.get_object.assert_called_once_with("DP-B01", "some-key.pdf")
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()

    def test_get_raises_storage_error_on_failure(self, tmp_path):
        from minio.error import S3Error

        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_client.get_object.side_effect = S3Error(
            "GetObject", "DP-B01", "", "", "", "", ""
        )

        with pytest.raises(StorageError, match="Failed to retrieve from B2"):
            backend.get("missing-key.pdf")

    def test_delete_calls_remove_object(self, tmp_path):
        backend, mock_client = self._make_backend(tmp_path=tmp_path)

        backend.delete("some-key.pdf")

        mock_client.remove_object.assert_called_once_with("DP-B01", "some-key.pdf")

    def test_delete_raises_storage_error_on_failure(self, tmp_path):
        from minio.error import S3Error

        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_client.remove_object.side_effect = S3Error(
            "RemoveObject", "DP-B01", "", "", "", "", ""
        )

        with pytest.raises(StorageError, match="Failed to delete from B2"):
            backend.delete("some-key.pdf")

    def test_get_local_path_downloads_to_temp(self, tmp_path):
        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_response = MagicMock()
        mock_response.read.return_value = b"pdf content"
        mock_client.get_object.return_value = mock_response

        local_path = backend.get_local_path("doc.pdf")

        assert os.path.exists(local_path)
        with open(local_path, "rb") as f:
            assert f.read() == b"pdf content"

    def test_get_local_path_uses_cache(self, tmp_path):
        backend, mock_client = self._make_backend(tmp_path=tmp_path)
        mock_response = MagicMock()
        mock_response.read.return_value = b"pdf content"
        mock_client.get_object.return_value = mock_response

        path1 = backend.get_local_path("doc.pdf")
        path2 = backend.get_local_path("doc.pdf")

        assert path1 == path2
        mock_client.get_object.assert_called_once()

    @patch("app.services.storage.Minio")
    def test_uses_secure_connection(self, mock_minio_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_client

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            BackblazeB2StorageBackend(
                endpoint="s3.us-east-005.backblazeb2.com",
                key_id="test-key-id",
                application_key="test-app-key",
                bucket="DP-B01",
                secure=True,
            )

        mock_minio_cls.assert_called_once_with(
            "s3.us-east-005.backblazeb2.com",
            access_key="test-key-id",
            secret_key="test-app-key",
            secure=True,
        )


# ---------------------------------------------------------------------------
# get_storage_backend factory tests
# ---------------------------------------------------------------------------

class TestGetStorageBackend:
    @patch("app.services.storage.settings")
    def test_returns_local_by_default(self, mock_settings):
        mock_settings.STORAGE_BACKEND = "local"
        mock_settings.UPLOAD_DIR = "/tmp/test-uploads"
        backend = get_storage_backend()
        assert isinstance(backend, LocalStorageBackend)

    @patch("app.services.storage.Minio")
    @patch("app.services.storage.settings")
    def test_returns_minio_when_configured(self, mock_settings, mock_minio_cls):
        mock_settings.STORAGE_BACKEND = "minio"
        mock_settings.MINIO_ENDPOINT = "localhost:9000"
        mock_settings.MINIO_ACCESS_KEY = "test"
        mock_settings.MINIO_SECRET_KEY = "test"
        mock_settings.MINIO_BUCKET = "test"
        mock_settings.MINIO_SECURE = False
        mock_settings.UPLOAD_DIR = "/tmp/test-uploads"

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_client

        backend = get_storage_backend()
        assert isinstance(backend, MinIOStorageBackend)

    @patch("app.services.storage.Minio")
    @patch("app.services.storage.settings")
    def test_returns_b2_when_configured(self, mock_settings, mock_minio_cls):
        mock_settings.STORAGE_BACKEND = "b2"
        mock_settings.B2_ENDPOINT = "s3.us-east-005.backblazeb2.com"
        mock_settings.B2_KEY_ID = "test-key-id"
        mock_settings.B2_APPLICATION_KEY = "test-app-key"
        mock_settings.B2_BUCKET = "DP-B01"
        mock_settings.B2_SECURE = True
        mock_settings.UPLOAD_DIR = "/tmp/test-uploads"

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_client

        backend = get_storage_backend()
        assert isinstance(backend, BackblazeB2StorageBackend)
