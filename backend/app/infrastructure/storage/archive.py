"""Safe ZIP extraction guarding against zip-slip and zip-bombs."""
from __future__ import annotations

import zipfile
from pathlib import Path

from app.core.security import UnsafePathError, ensure_within
from app.domain.exceptions import ValidationError


def extract_zip_safely(*, zip_path: str, dest_dir: str, max_total_bytes: int) -> int:
    """Extract a zip into dest_dir. Returns total uncompressed bytes.

    Rejects entries that escape dest_dir (zip-slip) and aborts if the total
    uncompressed size exceeds max_total_bytes (zip-bomb guard).
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise ValidationError("Uploaded file is not a valid ZIP archive.") from exc

    total = 0
    with archive:
        # Pre-flight: validate paths and total size before writing anything.
        for info in archive.infolist():
            if info.is_dir():
                continue
            total += info.file_size
            if total > max_total_bytes:
                raise ValidationError("Uploaded archive exceeds the maximum allowed size.")
            try:
                ensure_within(dest, Path(info.filename))
            except UnsafePathError as exc:
                raise ValidationError("Archive contains an unsafe path.") from exc

        archive.extractall(dest)

    return total
