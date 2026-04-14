import io
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import structlog
from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = structlog.get_logger(__name__)

_CONTENT_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tiff": "image/tiff",
}


def _guess_content_type(ext: str) -> str:
    return _CONTENT_TYPE_MAP.get(ext.lower(), "application/octet-stream")


class StorageError(Exception):
    pass


class StorageBackend(ABC):
    @abstractmethod
    def save(self, content: bytes, filename: str) -> str:
        """Save file content. Returns the storage key/path."""

    @abstractmethod
    def get(self, storage_path: str) -> bytes:
        """Retrieve file content by storage key/path."""

    @abstractmethod
    def delete(self, storage_path: str) -> None:
        """Delete file by storage key/path."""

    @abstractmethod
    def get_local_path(self, storage_path: str) -> str:
        """Get a local file path for parsing. May download to a temp location."""


class LocalStorageBackend(StorageBackend):
    def __init__(self, upload_dir: str | None = None):
        self.upload_dir = Path(upload_dir or settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, filename: str) -> str:
        ext = Path(filename).suffix
        stored_name = f"{uuid.uuid4()}{ext}"
        storage_path = str(self.upload_dir / stored_name)

        with open(storage_path, "wb") as f:
            f.write(content)

        logger.info("file_saved_local", path=storage_path, size=len(content))
        return storage_path

    def get(self, storage_path: str) -> bytes:
        if not os.path.exists(storage_path):
            raise StorageError(f"File not found: {storage_path}")
        with open(storage_path, "rb") as f:
            return f.read()

    def delete(self, storage_path: str) -> None:
        if os.path.exists(storage_path):
            os.remove(storage_path)
            logger.info("file_deleted_local", path=storage_path)

    def get_local_path(self, storage_path: str) -> str:
        if not os.path.exists(storage_path):
            raise StorageError(f"File not found: {storage_path}")
        return storage_path


class MinIOStorageBackend(StorageBackend):
    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
    ):
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket = bucket or settings.MINIO_BUCKET
        self.secure = secure if secure is not None else settings.MINIO_SECURE

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

        self._ensure_bucket()

        # Temp dir for parser file access
        self._temp_dir = Path(settings.UPLOAD_DIR) / ".minio_temp"
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info("minio_bucket_created", bucket=self.bucket)
        except S3Error as e:
            raise StorageError(f"Failed to initialize MinIO bucket: {e}") from e

    def save(self, content: bytes, filename: str) -> str:
        ext = Path(filename).suffix
        object_name = f"{uuid.uuid4()}{ext}"

        try:
            self.client.put_object(
                self.bucket,
                object_name,
                io.BytesIO(content),
                length=len(content),
                content_type=self._guess_content_type(ext),
            )
        except S3Error as e:
            raise StorageError(f"Failed to upload to MinIO: {e}") from e

        logger.info(
            "file_saved_minio",
            bucket=self.bucket,
            object=object_name,
            size=len(content),
        )
        return object_name

    def get(self, storage_path: str) -> bytes:
        try:
            response = self.client.get_object(self.bucket, storage_path)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            raise StorageError(f"Failed to retrieve from MinIO: {e}") from e

    def delete(self, storage_path: str) -> None:
        try:
            self.client.remove_object(self.bucket, storage_path)
            logger.info("file_deleted_minio", bucket=self.bucket, object=storage_path)
        except S3Error as e:
            raise StorageError(f"Failed to delete from MinIO: {e}") from e

        # Clean up any temp file
        temp_path = self._temp_dir / storage_path
        if temp_path.exists():
            temp_path.unlink()

    def get_local_path(self, storage_path: str) -> str:
        temp_path = self._temp_dir / storage_path
        if not temp_path.exists():
            content = self.get(storage_path)
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(content)
        return str(temp_path)

    @staticmethod
    def _guess_content_type(ext: str) -> str:
        return _guess_content_type(ext)


class BackblazeB2StorageBackend(StorageBackend):
    def __init__(
        self,
        endpoint: str | None = None,
        key_id: str | None = None,
        application_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
    ):
        self.endpoint = endpoint or settings.B2_ENDPOINT
        self.key_id = key_id or settings.B2_KEY_ID
        self.application_key = application_key or settings.B2_APPLICATION_KEY
        self.bucket = bucket or settings.B2_BUCKET
        self.secure = secure if secure is not None else settings.B2_SECURE

        self.client = Minio(
            self.endpoint,
            access_key=self.key_id,
            secret_key=self.application_key,
            secure=self.secure,
        )

        self._verify_bucket()

        # Temp dir for parser file access
        self._temp_dir = Path(settings.UPLOAD_DIR) / ".b2_temp"
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    def _verify_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                raise StorageError(
                    f"B2 bucket '{self.bucket}' does not exist. "
                    "Create it in the Backblaze B2 console first."
                )
            logger.info("b2_bucket_verified", bucket=self.bucket)
        except S3Error as e:
            raise StorageError(f"Failed to verify B2 bucket: {e}") from e

    def save(self, content: bytes, filename: str) -> str:
        ext = Path(filename).suffix
        object_name = f"{uuid.uuid4()}{ext}"

        try:
            self.client.put_object(
                self.bucket,
                object_name,
                io.BytesIO(content),
                length=len(content),
                content_type=_guess_content_type(ext),
            )
        except S3Error as e:
            raise StorageError(f"Failed to upload to B2: {e}") from e

        logger.info(
            "file_saved_b2",
            bucket=self.bucket,
            object=object_name,
            size=len(content),
        )
        return object_name

    def get(self, storage_path: str) -> bytes:
        try:
            response = self.client.get_object(self.bucket, storage_path)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            raise StorageError(f"Failed to retrieve from B2: {e}") from e

    def delete(self, storage_path: str) -> None:
        try:
            self.client.remove_object(self.bucket, storage_path)
            logger.info("file_deleted_b2", bucket=self.bucket, object=storage_path)
        except S3Error as e:
            raise StorageError(f"Failed to delete from B2: {e}") from e

        # Clean up any temp file
        temp_path = self._temp_dir / storage_path
        if temp_path.exists():
            temp_path.unlink()

    def get_local_path(self, storage_path: str) -> str:
        temp_path = self._temp_dir / storage_path
        if not temp_path.exists():
            content = self.get(storage_path)
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(content)
        return str(temp_path)


def get_storage_backend() -> StorageBackend:
    if settings.STORAGE_BACKEND == "minio":
        return MinIOStorageBackend()
    if settings.STORAGE_BACKEND == "b2":
        return BackblazeB2StorageBackend()
    return LocalStorageBackend()


# Module-level singleton
storage = get_storage_backend()
