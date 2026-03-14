"""User interface for rotating PDF pages."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from pdf_tools.rotate import rotate_pdf
from ui.password_aware import PasswordAwareOperationMixin
from widgets.file_list_widget import FileListWidget
from widgets.pdf_viewer import PDFViewer

LOGGER = logging.getLogger(__name__)


class RotateTab(QWidget, PasswordAwareOperationMixin):
    """Tab for rotating selected or all pages in a PDF."""

    def __init__(self, parent=None) -> None:
        """Initialize the rotate tab."""
        super().__init__(parent)

        self.file_list = FileListWidget(
            empty_text="Drop one PDF here or use Open PDF.",
            allow_multiple=False,
        )
        self.viewer = PDFViewer()

        self.open_button = QPushButton("Open PDF...")
        self.clear_button = QPushButton("Clear")
        self.angle_combo = QComboBox()
        self.angle_combo.addItems(["90", "180", "270"])
        self.all_pages_checkbox = QCheckBox("Rotate all pages")
        self.all_pages_checkbox.setChecked(True)
        self.page_edit = QLineEdit()
        self.page_edit.setPlaceholderText("e.g. 1-3, 6, 8-9")
        self.save_button = QPushButton("Save Rotated PDF...")

        self._initialize_password_support()
        self._build_layout()
        self._connect_signals()
        self._update_page_input_state()
        self._update_actions()

    def _build_layout(self) -> None:
        """Build the rotate tab layout."""
        instruction_label = QLabel("Open one PDF, preview it, then rotate all pages or only the selected page ranges.")
        instruction_label.setWordWrap(True)

        source_buttons = QHBoxLayout()
        source_buttons.setContentsMargins(0, 0, 0, 0)
        source_buttons.setSpacing(8)
        source_buttons.addWidget(self.open_button)
        source_buttons.addWidget(self.clear_button)

        options_group = QGroupBox("Rotation Options")
        options_form = QFormLayout(options_group)
        options_form.addRow("Angle", self.angle_combo)
        options_form.addRow("", self.all_pages_checkbox)
        options_form.addRow("Pages", self.page_edit)

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
        """Connect UI actions for the rotate workflow."""
        self.open_button.clicked.connect(self._browse_file)
        self.clear_button.clicked.connect(self.file_list.clear_files)
        self.save_button.clicked.connect(self._save_rotated_pdf)

        self.all_pages_checkbox.toggled.connect(self._update_page_input_state)
        self.file_list.currentPdfChanged.connect(self._preview_selected_file)
        self.file_list.filesChanged.connect(self._handle_files_changed)

    def _browse_file(self) -> None:
        """Open a file dialog for a single source PDF."""
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF to Rotate",
            str(Path.home()),
            "PDF Files (*.pdf)",
        )
        if selected_file:
            self.file_list.add_pdf_paths([selected_file])

    def _preview_selected_file(self, file_path: str) -> None:
        """Update the preview widget when the source changes."""
        if file_path:
            self.viewer.load_pdf(file_path)
        else:
            self.viewer.clear()

    def _handle_files_changed(self, _files: list[str]) -> None:
        """Refresh action state after a source change."""
        if self.file_list.count() == 0:
            self.viewer.clear()
        elif self.file_list.currentRow() < 0:
            self.file_list.setCurrentRow(0)

        self._update_actions()

    def _update_page_input_state(self, *_args) -> None:
        """Disable the page selection field when rotating all pages."""
        self.page_edit.setEnabled(not self.all_pages_checkbox.isChecked())

    def _update_actions(self) -> None:
        """Enable or disable actions depending on the selected source."""
        has_source = self.file_list.current_path() is not None
        self.clear_button.setEnabled(has_source)
        self.save_button.setEnabled(has_source)

    def _save_rotated_pdf(self) -> None:
        """Open a save dialog and rotate the requested pages."""
        source_path = self.file_list.current_path()
        if source_path is None:
            QMessageBox.warning(self, "No PDF Selected", "Open a PDF before running the rotate operation.")
            return

        if not self.all_pages_checkbox.isChecked() and not self.page_edit.text().strip():
            QMessageBox.warning(
                self,
                "Missing Page Selection",
                "Enter page numbers or ranges such as 1-3, 6, 8-9.",
            )
            return

        default_output = source_path.with_name(f"{source_path.stem}_rotated.pdf")
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Rotated PDF",
            str(default_output),
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return

        try:
            result = self._run_password_aware_operation(
                lambda passwords: rotate_pdf(
                    source_path,
                    output_path,
                    int(self.angle_combo.currentText()),
                    None if self.all_pages_checkbox.isChecked() else self.page_edit.text(),
                    passwords,
                ),
                "Rotation Failed",
            )
            if result is None:
                return
        except Exception as error:
            LOGGER.exception("Rotate operation failed")
            QMessageBox.critical(self, "Rotation Failed", f"Could not rotate the selected PDF.\n\n{error}")
            return

        QMessageBox.information(self, "Rotation Complete", f"Rotated PDF saved to:\n{output_path}")
