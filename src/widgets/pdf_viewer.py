"""Embedded PDF viewer widget built on top of Qt PDF classes."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QPointF
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfPageSelector, QPdfView
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

LOGGER = logging.getLogger(__name__)

PDF_NO_ERROR = getattr(QPdfDocument.Error, "None_", None)
PDF_INCORRECT_PASSWORD = getattr(QPdfDocument.Error, "IncorrectPassword", None)


class PDFViewer(QWidget):
    """Composite widget that displays and navigates PDF documents."""

    def __init__(self, parent=None) -> None:
        """Initialize the PDF viewer widget."""
        super().__init__(parent)
        self._current_path: Path | None = None
        self._syncing_page_selector = False

        self._document = QPdfDocument(self)
        self._pdf_view = QPdfView(self)
        self._pdf_view.setDocument(self._document)
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self._pdf_view.setPageMode(QPdfView.PageMode.SinglePage)
        self._pdf_view.setPageSpacing(12)

        self._navigator = self._pdf_view.pageNavigator()

        self._file_label = QLabel("Drop or open a PDF to preview it here.")
        self._file_label.setObjectName("viewerFileLabel")

        self._back_button = QPushButton("Back")
        self._forward_button = QPushButton("Forward")
        self._previous_button = QPushButton("Previous")
        self._next_button = QPushButton("Next")
        self._page_selector = QPdfPageSelector()
        self._page_selector.setDocument(self._document)
        self._mode_button = QPushButton("Continuous")
        self._mode_button.setCheckable(True)
        self._fit_page_button = QPushButton("Fit Page")
        self._fit_width_button = QPushButton("Fit Width")
        self._zoom_out_button = QPushButton("-")
        self._zoom_in_button = QPushButton("+")
        self._zoom_label = QLabel("100%")

        self._build_layout()
        self._connect_signals()
        self._update_controls()

    def load_pdf(self, file_path: str | Path, show_error_dialog: bool = True) -> bool:
        """Load a PDF file into the embedded viewer."""
        resolved_path = Path(file_path).expanduser().resolve()
        self.clear()
        self._document.setPassword("")

        error = self._document.load(str(resolved_path))
        if error == PDF_INCORRECT_PASSWORD:
            password, accepted = QInputDialog.getText(
                self,
                "PDF Password Required",
                "Enter the PDF password to preview the file:",
                QLineEdit.Password,
            )
            if accepted and password:
                self._document.close()
                self._document.setPassword(password)
                error = self._document.load(str(resolved_path))

        if error != PDF_NO_ERROR:
            LOGGER.warning("Failed to load PDF preview for %s: %s", resolved_path, error)
            self.clear()
            if show_error_dialog:
                QMessageBox.warning(
                    self,
                    "Preview Unavailable",
                    f"Could not preview the selected PDF.\n\n{resolved_path}\n\nReason: {error}",
                )
            return False

        self._current_path = resolved_path
        self._navigator.clear()
        self._navigator.jump(0, QPointF(), 0)
        self._update_status_label()
        self._update_controls()
        return True

    def clear(self) -> None:
        """Clear the current document from the viewer."""
        self._document.close()
        self._current_path = None
        self._file_label.setText("Drop or open a PDF to preview it here.")
        self._zoom_label.setText("100%")
        self._update_controls()

    def current_path(self) -> Path | None:
        """Return the current previewed PDF path."""
        return self._current_path

    def go_to_page(self, page_index: int) -> None:
        """Navigate to a specific zero-based page in the loaded document."""
        if self._document.pageCount() == 0:
            return

        bounded_index = max(0, min(page_index, self._document.pageCount() - 1))
        self._navigator.jump(bounded_index, QPointF(), 0)

    def _build_layout(self) -> None:
        """Build the viewer layout and toolbar."""
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)
        toolbar_layout.addWidget(self._back_button)
        toolbar_layout.addWidget(self._forward_button)
        toolbar_layout.addWidget(self._previous_button)
        toolbar_layout.addWidget(self._next_button)
        toolbar_layout.addWidget(self._page_selector)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self._mode_button)
        toolbar_layout.addWidget(self._fit_page_button)
        toolbar_layout.addWidget(self._fit_width_button)
        toolbar_layout.addWidget(self._zoom_out_button)
        toolbar_layout.addWidget(self._zoom_label)
        toolbar_layout.addWidget(self._zoom_in_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._file_label)
        layout.addLayout(toolbar_layout)
        layout.addWidget(self._pdf_view, 1)

    def _connect_signals(self) -> None:
        """Connect Qt signals for viewer state synchronization."""
        self._back_button.clicked.connect(self._navigator.back)
        self._forward_button.clicked.connect(self._navigator.forward)
        self._previous_button.clicked.connect(self._go_to_previous_page)
        self._next_button.clicked.connect(self._go_to_next_page)
        self._fit_page_button.clicked.connect(self._fit_page)
        self._fit_width_button.clicked.connect(self._fit_width)
        self._zoom_in_button.clicked.connect(self._zoom_in)
        self._zoom_out_button.clicked.connect(self._zoom_out)
        self._mode_button.toggled.connect(self._toggle_continuous_mode)

        self._page_selector.currentPageChanged.connect(self._on_page_selector_changed)
        self._navigator.currentPageChanged.connect(self._sync_page_selector)
        self._navigator.backAvailableChanged.connect(self._update_controls)
        self._navigator.forwardAvailableChanged.connect(self._update_controls)
        self._document.pageCountChanged.connect(self._update_status_label)
        self._document.pageCountChanged.connect(self._update_controls)
        self._pdf_view.zoomFactorChanged.connect(self._update_zoom_label)

    def _toggle_continuous_mode(self, enabled: bool) -> None:
        """Switch between single-page and continuous page mode."""
        if enabled:
            self._pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
            self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        else:
            self._pdf_view.setPageMode(QPdfView.PageMode.SinglePage)
            self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)

        self._update_zoom_label()

    def _on_page_selector_changed(self, page_index: int) -> None:
        """Jump to the page chosen in the page selector."""
        if self._syncing_page_selector or self._document.pageCount() == 0:
            return

        self._navigator.jump(page_index, QPointF(), 0)

    def _sync_page_selector(self, page_index: int) -> None:
        """Keep the page selector synchronized with navigation history."""
        self._syncing_page_selector = True
        self._page_selector.setCurrentPage(page_index)
        self._syncing_page_selector = False
        self._update_controls()

    def _go_to_previous_page(self) -> None:
        """Navigate to the previous page in the document."""
        current_page = self._navigator.currentPage()
        if current_page > 0:
            self._navigator.jump(current_page - 1, QPointF(), 0)

    def _go_to_next_page(self) -> None:
        """Navigate to the next page in the document."""
        current_page = self._navigator.currentPage()
        if current_page < self._document.pageCount() - 1:
            self._navigator.jump(current_page + 1, QPointF(), 0)

    def _fit_page(self) -> None:
        """Scale the PDF view to fit the full page."""
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self._update_zoom_label()

    def _fit_width(self) -> None:
        """Scale the PDF view to fit the page width."""
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._update_zoom_label()

    def _zoom_in(self) -> None:
        """Increase the zoom factor using a controlled increment."""
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        new_zoom = min(self._pdf_view.zoomFactor() * 1.2, 5.0)
        self._pdf_view.setZoomFactor(new_zoom)

    def _zoom_out(self) -> None:
        """Decrease the zoom factor using a controlled increment."""
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        new_zoom = max(self._pdf_view.zoomFactor() / 1.2, 0.2)
        self._pdf_view.setZoomFactor(new_zoom)

    def _update_status_label(self, *_args) -> None:
        """Update the file label with the current document details."""
        if not self._current_path:
            self._file_label.setText("Drop or open a PDF to preview it here.")
            return

        page_count = self._document.pageCount()
        page_suffix = "page" if page_count == 1 else "pages"
        self._file_label.setText(f"{self._current_path.name}  |  {page_count} {page_suffix}")

    def _update_zoom_label(self, *_args) -> None:
        """Refresh the zoom percentage display."""
        zoom_percent = round(self._pdf_view.zoomFactor() * 100)
        self._zoom_label.setText(f"{zoom_percent}%")

    def _update_controls(self, *_args) -> None:
        """Enable or disable controls based on document state."""
        has_document = self._document.pageCount() > 0
        current_page = self._navigator.currentPage() if has_document else 0

        self._back_button.setEnabled(has_document and self._navigator.backAvailable())
        self._forward_button.setEnabled(has_document and self._navigator.forwardAvailable())
        self._previous_button.setEnabled(has_document and current_page > 0)
        self._next_button.setEnabled(has_document and current_page < self._document.pageCount() - 1)
        self._page_selector.setEnabled(has_document)
        self._mode_button.setEnabled(has_document)
        self._fit_page_button.setEnabled(has_document)
        self._fit_width_button.setEnabled(has_document)
        self._zoom_in_button.setEnabled(has_document)
        self._zoom_out_button.setEnabled(has_document)
