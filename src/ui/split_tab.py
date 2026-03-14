"""User interface for splitting PDFs."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from pdf_tools.split import split_pdf_by_ranges, split_pdf_to_individual_pages
from ui.password_aware import PasswordAwareOperationMixin
from widgets.file_list_widget import FileListWidget
from widgets.pdf_viewer import PDFViewer

LOGGER = logging.getLogger(__name__)


class SplitTab(QWidget, PasswordAwareOperationMixin):
    """Tab for splitting a PDF into multiple output PDFs."""

    def __init__(self, parent=None) -> None:
        """Initialize the split tab."""
        super().__init__(parent)

        self.file_list = FileListWidget(
            empty_text="Drop one PDF here or use Open PDF.",
            allow_multiple=False,
        )
        self.viewer = PDFViewer()

        self.open_button = QPushButton("Open PDF...")
        self.clear_button = QPushButton("Clear")
        self.individual_radio = QRadioButton("Split into individual pages")
        self.range_radio = QRadioButton("Split by page ranges")
        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText("e.g. 1-3, 4-6, 9")
        self.save_button = QPushButton("Save Split PDFs...")

        self.individual_radio.setChecked(True)

        self._initialize_password_support()
        self._build_layout()
        self._connect_signals()
        self._update_mode_state()
        self._update_actions()

    def _build_layout(self) -> None:
        """Build the split tab layout."""
        instruction_label = QLabel("Open one PDF, preview it, then split it into page files or range-based groups.")
        instruction_label.setWordWrap(True)

        source_buttons = QHBoxLayout()
        source_buttons.setContentsMargins(0, 0, 0, 0)
        source_buttons.setSpacing(8)
        source_buttons.addWidget(self.open_button)
        source_buttons.addWidget(self.clear_button)

        options_group = QGroupBox("Split Options")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(10)
        options_layout.addWidget(self.individual_radio)
        options_layout.addWidget(self.range_radio)

        range_form = QFormLayout()
        range_form.addRow("Ranges", self.range_edit)
        options_layout.addLayout(range_form)

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
        """Connect UI events for the split workflow."""
        self.open_button.clicked.connect(self._browse_file)
        self.clear_button.clicked.connect(self.file_list.clear_files)
        self.save_button.clicked.connect(self._save_split_pdfs)

        self.individual_radio.toggled.connect(self._update_mode_state)
        self.range_radio.toggled.connect(self._update_mode_state)
        self.file_list.currentPdfChanged.connect(self._preview_selected_file)
        self.file_list.filesChanged.connect(self._handle_files_changed)

    def _browse_file(self) -> None:
        """Open a file dialog for a single PDF source."""
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF to Split",
            str(Path.home()),
            "PDF Files (*.pdf)",
        )
        if selected_file:
            self.file_list.add_pdf_paths([selected_file])

    def _preview_selected_file(self, file_path: str) -> None:
        """Update the viewer when the source PDF changes."""
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

    def _update_mode_state(self, *_args) -> None:
        """Enable range input only when range-based splitting is selected."""
        self.range_edit.setEnabled(self.range_radio.isChecked())

    def _update_actions(self) -> None:
        """Enable or disable actions depending on whether a source is selected."""
        has_source = self.file_list.current_path() is not None
        self.clear_button.setEnabled(has_source)
        self.save_button.setEnabled(has_source)

    def _save_split_pdfs(self) -> None:
        """Choose an output folder and split the current PDF."""
        source_path = self.file_list.current_path()
        if source_path is None:
            QMessageBox.warning(self, "No PDF Selected", "Open a PDF before running the split operation.")
            return

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Choose Output Folder",
            str(source_path.parent),
        )
        if not output_dir:
            return

        try:
            if self.individual_radio.isChecked():
                created_files = self._run_password_aware_operation(
                    lambda passwords: split_pdf_to_individual_pages(source_path, output_dir, passwords),
                    "Split Failed",
                )
            else:
                if not self.range_edit.text().strip():
                    QMessageBox.warning(
                        self,
                        "Missing Page Ranges",
                        "Enter one or more page ranges such as 1-3, 4-6, 9.",
                    )
                    return
                created_files = self._run_password_aware_operation(
                    lambda passwords: split_pdf_by_ranges(
                        source_path,
                        output_dir,
                        self.range_edit.text(),
                        passwords,
                    ),
                    "Split Failed",
                )
            if created_files is None:
                return
        except Exception as error:
            LOGGER.exception("Split operation failed")
            QMessageBox.critical(self, "Split Failed", f"Could not split the selected PDF.\n\n{error}")
            return

        QMessageBox.information(
            self,
            "Split Complete",
            f"Created {len(created_files)} PDF file(s) in:\n{output_dir}",
        )
