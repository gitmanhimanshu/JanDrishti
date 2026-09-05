"""The media storage port.

`MediaService` depends on this; Cloudinary is one implementation and the local
filesystem is another. Nothing above infrastructure imports a storage SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class StoredFile:
    storage_key: str
    url: str
    backend: str
    thumbnail_url: str = ""
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    file_size: int = 0


@runtime_checkable
class MediaStorage(Protocol):
    name: str

    def upload(
        self, file: BinaryIO, *, folder: str, filename: str, resource_type: str, private: bool
    ) -> StoredFile: ...

    def delete(self, storage_key: str, *, resource_type: str) -> None: ...

    def signed_url(self, storage_key: str, *, expires_in: int = 300) -> str: ...
