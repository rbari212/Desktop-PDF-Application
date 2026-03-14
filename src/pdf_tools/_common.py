"""Shared helpers for opening PDFs, including encrypted inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from pypdf import PdfReader


class PdfPasswordError(ValueError):
    """Raised when a PDF requires a password or the provided password is invalid."""

    def __init__(self, file_path: str | Path, message: str | None = None) -> None:
        """Store the file path that triggered the password error."""
        self.file_path = Path(file_path).expanduser().resolve()
        super().__init__(message or f"A password is required to open {self.file_path.name}.")


def open_pdf_reader(
    input_path: str | Path,
    passwords: Mapping[str, str] | None = None,
) -> PdfReader:
    """Open a PDF reader and decrypt it when a cached password is available."""
    resolved_path = Path(input_path).expanduser().resolve()
    reader = PdfReader(str(resolved_path))

    if not reader.is_encrypted:
        return reader

    # Many bank and statement PDFs are encrypted but openable with a blank user password.
    if reader.decrypt("") != 0:
        return reader

    password = (passwords or {}).get(str(resolved_path))
    if password is None:
        raise PdfPasswordError(resolved_path, f"'{resolved_path.name}' is encrypted and requires a password.")

    decrypt_result = reader.decrypt(password)
    if decrypt_result == 0:
        raise PdfPasswordError(resolved_path, f"The password for '{resolved_path.name}' is incorrect.")

    return reader
