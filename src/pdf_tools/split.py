"""PDF split helpers built with pypdf."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping

from pypdf import PdfWriter

from pdf_tools._common import open_pdf_reader

LOGGER = logging.getLogger(__name__)


def split_pdf_to_individual_pages(
    input_path: str | Path,
    output_dir: str | Path,
    passwords: Mapping[str, str] | None = None,
) -> list[Path]:
    """Split a PDF into one file per page."""
    input_pdf = Path(input_path).expanduser().resolve()
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        reader = open_pdf_reader(input_pdf, passwords)

        page_count = len(reader.pages)
        if page_count == 0:
            raise ValueError("The selected PDF does not contain any pages.")

        width = max(3, len(str(page_count)))
        created_files: list[Path] = []
        base_name = input_pdf.stem

        for page_index, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)
            output_file = target_dir / f"{base_name}_page_{page_index:0{width}d}.pdf"
            with output_file.open("wb") as stream:
                writer.write(stream)
            created_files.append(output_file)

        LOGGER.info("Split %s into %s individual PDF files", input_pdf, len(created_files))
        return created_files
    except Exception:
        LOGGER.exception("Failed to split %s into individual pages", input_pdf)
        raise


def split_pdf_by_ranges(
    input_path: str | Path,
    output_dir: str | Path,
    range_text: str,
    passwords: Mapping[str, str] | None = None,
) -> list[Path]:
    """Split a PDF into multiple output files using page ranges."""
    input_pdf = Path(input_path).expanduser().resolve()
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        reader = open_pdf_reader(input_pdf, passwords)

        page_ranges = _parse_range_groups(range_text, len(reader.pages))
        created_files: list[Path] = []
        base_name = input_pdf.stem

        for group_index, (start_page, end_page) in enumerate(page_ranges, start=1):
            writer = PdfWriter()
            for page_number in range(start_page, end_page + 1):
                writer.add_page(reader.pages[page_number])

            readable_start = start_page + 1
            readable_end = end_page + 1
            output_file = target_dir / (
                f"{base_name}_part_{group_index:02d}_pages_{readable_start}-{readable_end}.pdf"
            )

            with output_file.open("wb") as stream:
                writer.write(stream)
            created_files.append(output_file)

        LOGGER.info("Split %s into %s ranged PDF files", input_pdf, len(created_files))
        return created_files
    except Exception:
        LOGGER.exception("Failed to split %s by page ranges", input_pdf)
        raise


def _parse_range_groups(range_text: str, total_pages: int) -> list[tuple[int, int]]:
    """Parse a comma-separated set of page ranges into zero-based tuples."""
    cleaned_text = range_text.strip()
    if not cleaned_text:
        raise ValueError("Enter one or more page ranges such as 1-3, 4-6, 9.")

    groups: list[tuple[int, int]] = []
    for raw_token in cleaned_text.split(","):
        token = raw_token.strip()
        if not token:
            continue

        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start_page = int(start_text)
            end_page = int(end_text)
        else:
            start_page = int(token)
            end_page = start_page

        if start_page < 1 or end_page < 1 or start_page > total_pages or end_page > total_pages:
            raise ValueError(f"Page range '{token}' is outside the document page count ({total_pages}).")
        if start_page > end_page:
            raise ValueError(f"Page range '{token}' is invalid because the start exceeds the end.")

        groups.append((start_page - 1, end_page - 1))

    if not groups:
        raise ValueError("Enter at least one valid page range.")

    return groups
