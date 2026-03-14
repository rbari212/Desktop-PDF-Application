"""PDF merge helpers built with pypdf."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from pypdf import PdfWriter

from pdf_tools._common import open_pdf_reader

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class MergePage:
    """Represents a single source page in a merged PDF plan."""

    source_path: Path
    page_index: int
    page_label: str


def build_merge_plan(
    input_paths: Sequence[str | Path],
    passwords: Mapping[str, str] | None = None,
) -> list[MergePage]:
    """Expand input PDFs into a page-by-page merge plan."""
    merge_plan: list[MergePage] = []

    for raw_path in input_paths:
        input_pdf = Path(raw_path).expanduser().resolve()
        reader = open_pdf_reader(input_pdf, passwords)

        for page_index in range(len(reader.pages)):
            merge_plan.append(
                MergePage(
                    source_path=input_pdf,
                    page_index=page_index,
                    page_label=f"{input_pdf.name} - Page {page_index + 1}",
                )
            )

    return merge_plan


def merge_page_plan(
    merge_plan: Sequence[MergePage],
    output_path: str | Path,
    passwords: Mapping[str, str] | None = None,
) -> Path:
    """Write a merged PDF using an explicit page-by-page merge plan."""
    if not merge_plan:
        raise ValueError("Select at least one PDF page to merge.")

    output = Path(output_path).expanduser().resolve()
    writer = PdfWriter()
    reader_cache: dict[str, object] = {}

    try:
        for merge_page in merge_plan:
            cache_key = str(merge_page.source_path)
            reader = reader_cache.get(cache_key)
            if reader is None:
                reader = open_pdf_reader(merge_page.source_path, passwords)
                reader_cache[cache_key] = reader

            writer.add_page(reader.pages[merge_page.page_index])

        with output.open("wb") as stream:
            writer.write(stream)

        LOGGER.info("Merged %s PDF pages into %s", len(merge_plan), output)
        return output
    except Exception:
        LOGGER.exception("Failed to merge PDF page plan into %s", output)
        raise


def merge_pdfs(
    input_paths: Sequence[str | Path],
    output_path: str | Path,
    passwords: Mapping[str, str] | None = None,
) -> Path:
    """Merge multiple PDF files into a single output PDF."""
    if not input_paths:
        raise ValueError("Select at least one PDF to merge.")

    try:
        return merge_page_plan(build_merge_plan(input_paths, passwords), output_path, passwords)
    except Exception:
        LOGGER.exception("Failed to merge PDFs into %s", output_path)
        raise
