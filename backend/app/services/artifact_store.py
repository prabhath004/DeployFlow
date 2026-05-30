"""Artifact store abstraction.

Phase 9 = S3 (real or LocalStack). NoopArtifactStore lets the worker run in
purely local dev without uploading anything. The factory below picks based
on ARTIFACTS_BACKEND.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ArtifactStore(ABC):
    @abstractmethod
    async def upload_text(self, *, key: str, body: str, content_type: str) -> str:
        """Upload a string body. Returns the URI (s3:// for S3, or a placeholder)."""


class NoopArtifactStore(ArtifactStore):
    async def upload_text(self, *, key: str, body: str, content_type: str) -> str:
        return f"noop://{key}"


class S3ArtifactStore(ArtifactStore):
    def __init__(
        self,
        *,
        bucket: str,
        prefix: str,
        region: str,
        endpoint_url: str | None,
    ) -> None:
        import aioboto3  # local import — only loaded when S3 is configured
        self._session = aioboto3.Session()
        self._bucket = bucket
        self._prefix = prefix.rstrip("/") + "/" if prefix else ""
        self._region = region
        self._endpoint_url = endpoint_url

    def _client(self):
        return self._session.client(
            "s3",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
        )

    async def upload_text(self, *, key: str, body: str, content_type: str) -> str:
        full_key = f"{self._prefix}{key}"
        async with self._client() as s3:
            await s3.put_object(
                Bucket=self._bucket,
                Key=full_key,
                Body=body.encode("utf-8"),
                ContentType=content_type,
            )
        return f"s3://{self._bucket}/{full_key}"


def make_artifact_store(settings) -> ArtifactStore:
    if settings.artifacts_backend == "s3":
        if not settings.s3_artifacts_bucket:
            raise RuntimeError("ARTIFACTS_BACKEND=s3 but S3_ARTIFACTS_BUCKET is not set")
        return S3ArtifactStore(
            bucket=settings.s3_artifacts_bucket,
            prefix=settings.s3_artifacts_prefix,
            region=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url,
        )
    return NoopArtifactStore()
