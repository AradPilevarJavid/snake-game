"""Streaming SHA-256 helpers used by the launcher and release tooling."""

from __future__ import annotations

import hashlib
from pathlib import Path


CHUNK_SIZE = 1024 * 1024


def sha256_file(path: str | Path, chunk_size: int = CHUNK_SIZE) -> str:
    """Return the lowercase SHA-256 digest for *path*."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as file_handle:
        while chunk := file_handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def file_matches(path: str | Path, expected_hash: str, expected_size: int) -> bool:
    """Return whether a regular file has the expected size and digest."""
    candidate = Path(path)
    try:
        if not candidate.is_file() or candidate.stat().st_size != expected_size:
            return False
        return sha256_file(candidate) == expected_hash.lower()
    except OSError:
        return False
