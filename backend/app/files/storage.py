"""
Warp Ladger — File Storage Abstraction
StorageBackend ABC with MinIO, S3, and R2 implementations.
"""
import uuid
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

import aioboto3
import structlog
from botocore.config import Config

from app.core.config import settings

log = structlog.get_logger(__name__)


# ─── Abstract Backend ────────────────────────────────────────
class StorageBackend(ABC):
    @abstractmethod
    async def upload(
        self,
        *,
        key: str,
        data: bytes | BinaryIO,
        content_type: str,
        bucket: Optional[str] = None,
    ) -> str:
        """Upload a file. Returns the storage key."""
        ...

    @abstractmethod
    async def generate_presigned_url(
        self,
        *,
        key: str,
        expires_in: int = 3600,
        bucket: Optional[str] = None,
    ) -> str:
        """Generate a pre-signed download URL."""
        ...

    @abstractmethod
    async def delete(self, *, key: str, bucket: Optional[str] = None) -> None:
        """Delete a file."""
        ...


# ─── MinIO / S3-Compatible Backend ───────────────────────────
class S3CompatibleBackend(StorageBackend):
    def __init__(
        self,
        *,
        endpoint_url: Optional[str] = None,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        default_bucket: str,
    ) -> None:
        self._session = aioboto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        self._endpoint_url = endpoint_url
        self._default_bucket = default_bucket

    def _client(self):
        return self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            config=Config(signature_version="s3v4"),
        )

    async def upload(
        self,
        *,
        key: str,
        data: bytes | BinaryIO,
        content_type: str,
        bucket: Optional[str] = None,
    ) -> str:
        bucket = bucket or self._default_bucket
        async with self._client() as client:
            await client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        log.info("file_uploaded", bucket=bucket, key=key)
        return key

    async def generate_presigned_url(
        self,
        *,
        key: str,
        expires_in: int = 3600,
        bucket: Optional[str] = None,
    ) -> str:
        bucket = bucket or self._default_bucket
        async with self._client() as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        return url

    async def delete(self, *, key: str, bucket: Optional[str] = None) -> None:
        bucket = bucket or self._default_bucket
        async with self._client() as client:
            await client.delete_object(Bucket=bucket, Key=key)
        log.info("file_deleted", bucket=bucket, key=key)


class MinIOBackend(S3CompatibleBackend):
    def __init__(self) -> None:
        scheme = "https" if settings.MINIO_SECURE else "http"
        super().__init__(
            endpoint_url=f"{scheme}://{settings.MINIO_ENDPOINT}",
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            region="us-east-1",
            default_bucket=settings.STORAGE_BUCKET_NAME,
        )


class S3Backend(S3CompatibleBackend):
    def __init__(self) -> None:
        super().__init__(
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
            region=settings.AWS_REGION,
            default_bucket=settings.AWS_S3_BUCKET,
        )


class R2Backend(S3CompatibleBackend):
    def __init__(self) -> None:
        super().__init__(
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            access_key=settings.R2_ACCESS_KEY_ID,
            secret_key=settings.R2_SECRET_ACCESS_KEY,
            region="auto",
            default_bucket=settings.R2_BUCKET,
        )


class MemoryStorageBackend(StorageBackend):
    """In-memory storage backend for unit testing and offline execution."""

    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    async def upload(
        self,
        *,
        key: str,
        data: bytes | BinaryIO,
        content_type: str,
        bucket: Optional[str] = None,
    ) -> str:
        if hasattr(data, "read"):
            self.store[key] = data.read()
        else:
            self.store[key] = data
        return key

    async def generate_presigned_url(
        self,
        *,
        key: str,
        expires_in: int = 3600,
        bucket: Optional[str] = None,
    ) -> str:
        return f"https://storage.local/{key}"

    async def delete(self, *, key: str, bucket: Optional[str] = None) -> None:
        self.store.pop(key, None)


_memory_storage = MemoryStorageBackend()


def get_storage_backend() -> StorageBackend:
    """Factory: returns the configured storage backend."""
    match settings.STORAGE_BACKEND:
        case "s3":
            return S3Backend()
        case "r2":
            return R2Backend()
        case "memory":
            return _memory_storage
        case _:
            return MinIOBackend()


def make_storage_key(org_id: uuid.UUID, filename: str) -> str:
    """Generate a namespaced, collision-resistant storage key."""
    safe_filename = filename.replace(" ", "_")
    return f"orgs/{org_id}/{uuid.uuid4()}/{safe_filename}"
