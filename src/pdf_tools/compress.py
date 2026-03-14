"""PDF compression and optimization helpers built with pypdf."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping

from pypdf import PdfWriter

from pdf_tools._common import open_pdf_reader

LOGGER = logging.getLogger(__name__)


def optimize_pdf(
    input_path: str | Path,
    output_path: str | Path,
    remove_metadata: bool = True,
    compress_streams: bool = True,
    passwords: Mapping[str, str] | None = None,
) -> Path:
    """Optimize a PDF by removing metadata and compressing streams when possible."""
    input_pdf = Path(input_path).expanduser().resolve()
    output_pdf = Path(output_path).expanduser().resolve()

    try:
        reader = open_pdf_reader(input_pdf, passwords)

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        if compress_streams:
            for page_index, page in enumerate(writer.pages, start=1):
                try:
                    page.compress_content_streams(level=9)
                except Exception as compression_error:
                    LOGGER.warning(
                        "Could not compress content streams on page %s of %s: %s",
                        page_index,
                        input_pdf,
                        compression_error,
                    )

        if remove_metadata:
            writer.metadata = None

        # This reduces duplicate objects and removes orphaned ones before writing.
        writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)

        with output_pdf.open("wb") as stream:
            writer.write(stream)

        LOGGER.info("Optimized %s and saved the result to %s", input_pdf, output_pdf)
        return output_pdf
    except Exception:
        LOGGER.exception("Failed to optimize %s", input_pdf)
        raise
