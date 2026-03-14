"""Reusable list widgets for handling PDF file selection."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDragMoveEvent, QDropEvent, QPainter
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem


class FileListWidget(QListWidget):
    """List widget that accepts dropped PDF files and optional reordering."""

    filesChanged = Signal(list)
    currentPdfChanged = Signal(str)

    def __init__(
        self,
        empty_text: str,
        allow_multiple: bool = True,
        allow_reorder: bool = False,
        parent=None,
    ) -> None:
        """Initialize the list widget."""
        super().__init__(parent)
        self._empty_text = empty_text
        self._allow_multiple = allow_multiple
        self._allow_reorder = allow_reorder

        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(allow_reorder)
        self.setDefaultDropAction(
            Qt.DropAction.MoveAction if allow_reorder else Qt.DropAction.CopyAction
        )
        self.setSpacing(6)
        self.setMinimumHeight(150)

        if allow_reorder:
            self.setDragDropMode(QAbstractItemView.DragDrop)
            self.setDragDropOverwriteMode(False)
        else:
            self.setDragDropMode(QAbstractItemView.DropOnly)

        self.itemSelectionChanged.connect(self._emit_current_pdf_changed)
        self.model().rowsMoved.connect(self._emit_files_changed)

    def add_pdf_paths(self, paths: Iterable[str | Path]) -> None:
        """Add one or more PDF paths to the list."""
        existing = {path.resolve() for path in self.all_paths()}
        added_any = False

        for raw_path in paths:
            pdf_path = Path(raw_path).expanduser().resolve()
            if pdf_path.suffix.lower() != ".pdf" or not pdf_path.exists():
                continue

            if not self._allow_multiple:
                self.clear()
                existing.clear()

            if pdf_path in existing:
                continue

            item = QListWidgetItem(pdf_path.name)
            item.setToolTip(str(pdf_path))
            item.setData(Qt.ItemDataRole.UserRole, str(pdf_path))
            self.addItem(item)
            existing.add(pdf_path)
            added_any = True

            if not self._allow_multiple:
                break

        if self.count() and self.currentRow() < 0:
            self.setCurrentRow(0)

        if added_any:
            self._emit_files_changed()
            self._emit_current_pdf_changed()

    def remove_selected_items(self) -> None:
        """Remove the currently selected items from the list."""
        for item in self.selectedItems():
            row = self.row(item)
            self.takeItem(row)

        if self.count():
            self.setCurrentRow(max(0, min(self.currentRow(), self.count() - 1)))

        self._emit_files_changed()
        self._emit_current_pdf_changed()
        self.viewport().update()

    def clear_files(self) -> None:
        """Clear all files from the list."""
        self.clear()
        self._emit_files_changed()
        self._emit_current_pdf_changed()
        self.viewport().update()

    def current_path(self) -> Path | None:
        """Return the currently selected PDF path if present."""
        item = self.currentItem()
        if item is None:
            return None
        path_value = item.data(Qt.ItemDataRole.UserRole)
        return Path(path_value) if path_value else None

    def all_paths(self) -> list[Path]:
        """Return all PDF paths in the current visual order."""
        paths: list[Path] = []
        for index in range(self.count()):
            item = self.item(index)
            path_value = item.data(Qt.ItemDataRole.UserRole)
            if path_value:
                paths.append(Path(path_value))
        return paths

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag operations that contain valid PDF files."""
        if event.source() is self and self._allow_reorder:
            event.acceptProposedAction()
            return

        if self._extract_pdf_paths(event.mimeData()):
            event.acceptProposedAction()
            return

        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Continue drag operations only for valid PDF data."""
        if event.source() is self and self._allow_reorder:
            event.acceptProposedAction()
            return

        if self._extract_pdf_paths(event.mimeData()):
            event.acceptProposedAction()
            return

        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle internal reordering and external PDF drops."""
        if event.source() is self and self._allow_reorder:
            super().dropEvent(event)
            self._emit_files_changed()
            return

        paths = self._extract_pdf_paths(event.mimeData())
        if paths:
            # External drops are always added through the public add helper.
            self.add_pdf_paths(paths)
            event.acceptProposedAction()
            return

        event.ignore()

    def paintEvent(self, event) -> None:
        """Paint the list and a centered placeholder when empty."""
        super().paintEvent(event)

        if self.count() != 0:
            return

        painter = QPainter(self.viewport())
        painter.setPen(QColor("#6f7c8a"))
        placeholder_rect = self.viewport().rect().adjusted(16, 16, -16, -16)
        painter.drawText(
            placeholder_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self._empty_text,
        )

    def _extract_pdf_paths(self, mime_data) -> list[Path]:
        """Extract local PDF paths from a mime payload."""
        if not mime_data.hasUrls():
            return []

        pdf_paths: list[Path] = []
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue

            path = Path(url.toLocalFile()).expanduser().resolve()
            if path.suffix.lower() == ".pdf" and path.is_file():
                pdf_paths.append(path)

        return pdf_paths

    def _emit_files_changed(self, *_args) -> None:
        """Emit the files changed signal with current ordering."""
        self.filesChanged.emit([str(path) for path in self.all_paths()])

    def _emit_current_pdf_changed(self) -> None:
        """Emit the selected file path whenever the selection changes."""
        current_path = self.current_path()
        self.currentPdfChanged.emit(str(current_path) if current_path else "")
