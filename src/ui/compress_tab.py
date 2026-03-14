"""User interface for optimizing PDFs."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from pdf_tools.compress import optimize_pdf
from ui.password_aware import PasswordAwareOperationMixin
from widgets.file_list_widget import FileListWidget
from widgets.pdf_viewer import PDFViewer

LOGGER = logging.getLogger(__name__)


class CompressTab(QWidget, PasswordAwareOperationMixin):
    """Tab for optimizing a PDF using pypdf features."""

    def __init__(self, parent=None) -> None:
        """Initialize the compress tab."""
        super().__init__(parent)

        self.file_list = FileListWidget(
            empty_text="Drop one PDF here or use Open PDF.",
            allow_multiple=False,
        )
        self.viewer = PDFViewer()

        self.open_button = QPushButton("Open PDF...")
        self.clear_button = QPushButton("Clear")
        self.remove_metadata_checkbox = QCheckBox("Remove document metadata")
        self.remove_metadata_checkbox.setChecked(True)
        self.compress_streams_checkbox = QCheckBox("Compress content streams when possible")
        self.compress_streams_checkbox.setChecked(True)
        self.save_button = QPushButton("Save Optimized PDF...")

        self._initialize_password_support()
        self._build_layout()
        self._connect_signals()
        self._update_actions()

    def _build_layout(self) -> None:
        """Build the compress tab layout."""
        instruction_label = QLabel("Open one PDF, preview it, and save an optimized copy with lossless stream compression.")
        instruction_label.setWordWrap(True)

        source_buttons = QHBoxLayout()
        source_buttons.setContentsMargins(0, 0, 0, 0)
        source_buttons.setSpacing(8)
        source_buttons.addWidget(self.open_button)
        source_buttons.addWidget(self.clear_button)

        options_group = QGroupBox("Optimization Options")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(10)
        options_layout.addWidget(self.remove_metadata_checkbox)
        options_layout.addWidget(self.compress_streams_checkbox)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left_layout.addWidget(instruction_label)
        left_layout.addLayout(source_buttons)
        left_layout.addWidget(self.file_list)
        left_layout.addWidget(options_group)
        left_layout.addWidget(self.save_button)

        left_panel = QWidget()
        left_panel.setLayout(left_layout)

        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(self.viewer)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 900])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(splitter)

    def _connect_signals(self) -> None:
        """Connect UI actions for optimization."""
        self.open_button.clicked.connect(self._browse_file)
        self.clear_button.clicked.connect(self.file_list.clear_files)
        self.save_button.clicked.connect(self._save_optimized_pdf)

        self.file_list.currentPdfChanged.connect(self._preview_selected_file)
        self.file_list.filesChanged.connect(self._handle_files_changed)

    def _browse_file(self) -> None:
        """Open a file dialog for choosing a source PDF."""
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF to Optimize",
            str(Path.home()),
            "PDF Files (*.pdf)",
        )
        if selected_file:
            self.file_list.add_pdf_paths([selected_file])

    def _preview_selected_file(self, file_path: str) -> None:
        """Update the preview when the selected source changes."""
        if file_path:
            self.viewer.load_pdf(file_path)
        else:
            self.viewer.clear()

    def _handle_files_changed(self, _files: list[str]) -> None:
        """Refresh action state after source changes."""
        if self.file_list.count() == 0:
            self.viewer.clear()
        elif self.file_list.currentRow() < 0:
            self.file_list.setCurrentRow(0)

        self._update_actions()

    def _update_actions(self) -> None:
        """Enable or disable actions depending on the selected source."""
        has_source = self.file_list.current_path() is not None
        self.clear_button.setEnabled(has_source)
        self.save_button.setEnabled(has_source)

    def _save_optimized_pdf(self) -> None:
        """Open a save dialog and write the optimized PDF."""
        source_path = self.file_list.current_path()
        if source_path is None:
            QMessageBox.warning(self, "No PDF Selected", "Open a PDF before running optimization.")
            return

        default_output = source_path.with_name(f"{source_path.stem}_optimized.pdf")
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Optimized PDF",
            str(default_output),
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return

        try:
            result = self._run_password_aware_operation(
                lambda passwords: optimize_pdf(
                    source_path,
                    output_path,
                    remove_metadata=self.remove_metadata_checkbox.isChecked(),
                    compress_streams=self.compress_streams_checkbox.isChecked(),
                    passwords=passwords,
                ),
                "Optimization Failed",
            )
            if result is None:
                return
        except Exception as error:
            LOGGER.exception("Compression operation failed")
            QMessageBox.critical(
                self,
                "Optimization Failed",
                f"Could not optimize the selected PDF.\n\n{error}",
            )
            return

        QMessageBox.information(self, "Optimization Complete", f"Optimized PDF saved to:\n{output_path}")
