"""PDF rotation helpers built with pypdf."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping

from pypdf import PdfWriter

from pdf_tools._common import open_pdf_reader

LOGGER = logging.getLogger(__name__)


def rotate_pdf(
    input_path: str | Path,
    output_path: str | Path,
    angle: int,
    page_selection: str | None = None,
    passwords: Mapping[str, str] | None = None,
) -> Path:
    """Rotate selected pages or all pages in a PDF."""
    if angle not in {90, 180, 270}:
        raise ValueError("Rotation angle must be 90, 180, or 270 degrees.")

    input_pdf = Path(input_path).expanduser().resolve()
    output_pdf = Path(output_path).expanduser().resolve()

    try:
        reader = open_pdf_reader(input_pdf, passwords)

        selected_pages = (
            set(_parse_page_selection(page_selection or "", len(reader.pages)))
            if page_selection
            else set(range(len(reader.pages)))
        )

        writer = PdfWriter()
        for page_index, page in enumerate(reader.pages):
            if page_index in selected_pages:
                # pypdf rotates clockwise in-place and returns the page object.
                page.rotate(angle)
            writer.add_page(page)

        with output_pdf.open("wb") as stream:
            writer.write(stream)

        LOGGER.info("Rotated %s and saved the result to %s", input_pdf, output_pdf)
        return output_pdf
    except Exception:
        LOGGER.exception("Failed to rotate %s", input_pdf)
        raise


def _parse_page_selection(selection_text: str, total_pages: int) -> list[int]:
    """Parse a page selection string such as '1-3, 6, 8-9'."""
    cleaned_text = selection_text.strip()
    if not cleaned_text:
        raise ValueError("Enter page numbers or ranges such as 1-3, 6, 8-9.")

    pages: list[int] = []
    seen_pages: set[int] = set()

    for raw_token in cleaned_text.split(","):
        token = raw_token.strip()
        if not token:
            continue

        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start_page = int(start_text)
            end_page = int(end_text)
            if start_page > end_page:
                raise ValueError(f"Page range '{token}' is invalid because the start exceeds the end.")
            page_numbers = range(start_page, end_page + 1)
        else:
            page_numbers = [int(token)]

        for page_number in page_numbers:
            if page_number < 1 or page_number > total_pages:
                raise ValueError(
                    f"Page '{page_number}' is outside the document page count ({total_pages})."
                )

            page_index = page_number - 1
            if page_index not in seen_pages:
                pages.append(page_index)
                seen_pages.add(page_index)

    if not pages:
        raise ValueError("Enter at least one valid page number or range.")

    return pages
