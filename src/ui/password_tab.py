"""User interface for password-protecting PDFs."""

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
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from pdf_tools.password import protect_pdf
from ui.password_aware import PasswordAwareOperationMixin
from widgets.file_list_widget import FileListWidget
from widgets.pdf_viewer import PDFViewer

LOGGER = logging.getLogger(__name__)


class PasswordTab(QWidget, PasswordAwareOperationMixin):
    """Tab for applying password protection to a PDF."""

    def __init__(self, parent=None) -> None:
        """Initialize the password tab."""
        super().__init__(parent)

        self.file_list = FileListWidget(
            empty_text="Drop one PDF here or use Open PDF.",
            allow_multiple=False,
        )
        self.viewer = PDFViewer()

        self.open_button = QPushButton("Open PDF...")
        self.clear_button = QPushButton("Clear")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        self.save_button = QPushButton("Save Protected PDF...")

        self._initialize_password_support()
        self._build_layout()
        self._connect_signals()
        self._update_actions()

    def _build_layout(self) -> None:
        """Build the password tab layout."""
        instruction_label = QLabel("Open one PDF, preview it, set a password, and save the protected output.")
        instruction_label.setWordWrap(True)

        source_buttons = QHBoxLayout()
        source_buttons.setContentsMargins(0, 0, 0, 0)
        source_buttons.setSpacing(8)
        source_buttons.addWidget(self.open_button)
        source_buttons.addWidget(self.clear_button)

        options_group = QGroupBox("Password Options")
        options_form = QFormLayout(options_group)
        options_form.addRow("Password", self.password_edit)
        options_form.addRow("Confirm Password", self.confirm_password_edit)

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
        """Connect UI actions for password protection."""
        self.open_button.clicked.connect(self._browse_file)
        self.clear_button.clicked.connect(self.file_list.clear_files)
        self.save_button.clicked.connect(self._save_protected_pdf)

        self.file_list.currentPdfChanged.connect(self._preview_selected_file)
        self.file_list.filesChanged.connect(self._handle_files_changed)

    def _browse_file(self) -> None:
        """Open a file dialog for choosing a source PDF."""
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF to Protect",
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

    def _save_protected_pdf(self) -> None:
        """Validate password fields and save a protected PDF."""
        source_path = self.file_list.current_path()
        if source_path is None:
            QMessageBox.warning(self, "No PDF Selected", "Open a PDF before applying password protection.")
            return

        password = self.password_edit.text()
        confirm_password = self.confirm_password_edit.text()

        if not password:
            QMessageBox.warning(self, "Missing Password", "Enter a password for the protected PDF.")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Password Mismatch", "The password and confirmation do not match.")
            return

        default_output = source_path.with_name(f"{source_path.stem}_protected.pdf")
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Protected PDF",
            str(default_output),
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return

        try:
            result = self._run_password_aware_operation(
                lambda passwords: protect_pdf(source_path, output_path, password, None, passwords),
                "Protection Failed",
            )
            if result is None:
                return
        except Exception as error:
            LOGGER.exception("Password operation failed")
            QMessageBox.critical(
                self,
                "Protection Failed",
                f"Could not password-protect the selected PDF.\n\n{error}",
            )
            return

        QMessageBox.information(self, "Protection Complete", f"Protected PDF saved to:\n{output_path}")
