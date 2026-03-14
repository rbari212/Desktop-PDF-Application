"""PDF password helpers built with pypdf."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping

from pypdf import PdfWriter

from pdf_tools._common import open_pdf_reader

LOGGER = logging.getLogger(__name__)


def protect_pdf(
    input_path: str | Path,
    output_path: str | Path,
    user_password: str,
    owner_password: str | None = None,
    passwords: Mapping[str, str] | None = None,
) -> Path:
    """Apply password protection to a PDF."""
    if not user_password:
        raise ValueError("A password is required to protect the PDF.")

    input_pdf = Path(input_path).expanduser().resolve()
    output_pdf = Path(output_path).expanduser().resolve()

    try:
        reader = open_pdf_reader(input_pdf, passwords)

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        try:
            # Prefer AES when the optional backend is present.
            writer.encrypt(
                user_password=user_password,
                owner_password=owner_password or None,
                algorithm="AES-256",
            )
        except Exception as encryption_error:
            LOGGER.warning(
                "AES encryption backend unavailable; falling back to default pypdf encryption: %s",
                encryption_error,
            )
            writer.encrypt(
                user_password=user_password,
                owner_password=owner_password or None,
            )

        with output_pdf.open("wb") as stream:
            writer.write(stream)

        LOGGER.info("Applied password protection to %s and saved %s", input_pdf, output_pdf)
        return output_pdf
    except Exception:
        LOGGER.exception("Failed to apply password protection to %s", input_pdf)
        raise
