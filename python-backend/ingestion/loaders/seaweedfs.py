"""SeaweedFS loader via Go Storage Gateway (D12 capability-based)."""

from __future__ import annotations

from ingestion.clients.go_storage import GoStorageClient
from ingestion.core.exceptions import LoadError
from ingestion.loaders.base import LoadResult, Loader


class SeaweedFSLoader(Loader):
    """Load bytes from SeaweedFS via Go Storage Gateway signed URLs.

    Never has direct S3 credentials (D12). Identifier is the artifact UUID.
    """

    name = "seaweedfs"

    def __init__(self, client: GoStorageClient) -> None:
        self.client = client

    async def load(self, identifier: str) -> LoadResult:
        try:
            metadata = await self.client.get_metadata(identifier)
        except Exception as e:
            raise LoadError(f"Failed to fetch metadata for {identifier}: {e}") from e

        try:
            data = await self.client.download_bytes(identifier)
        except Exception as e:
            raise LoadError(f"Failed to download bytes for {identifier}: {e}") from e

        filename = (
            metadata.get("filename")
            or metadata.get("name")
            or metadata.get("original_name")
            or f"{identifier}.bin"
        )
        content_type = metadata.get("content_type") or metadata.get("mime_type")

        return LoadResult(
            data=data,
            filename=filename,
            source="seaweedfs",
            content_type=content_type,
            size=len(data),
        )
