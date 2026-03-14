"""User interface for the PDF merge workflow."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from pdf_tools.merge import MergePage, build_merge_plan, merge_page_plan
from ui.password_aware import PasswordAwareOperationMixin
from widgets.file_list_widget import FileListWidget
from widgets.pdf_viewer import PDFViewer

LOGGER = logging.getLogger(__name__)


class MergeTab(QWidget, PasswordAwareOperationMixin):
    """Tab for merging multiple PDFs into a single output document."""

    def __init__(self, parent=None) -> None:
        """Initialize the merge tab."""
        super().__init__(parent)

        self._merge_plan: list[MergePage] = []
        self._preview_output_path = Path(tempfile.gettempdir()) / "pdf_merge_application_merge_preview.pdf"

        self.file_list = FileListWidget(
            empty_text=(
                "Drop PDF files here or use Add PDFs.\n"
                "Drag items to reorder files before building the page plan."
            ),
            allow_multiple=True,
            allow_reorder=True,
        )
        self.page_list = QListWidget()
        self.page_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.page_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.page_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.page_list.setDragDropOverwriteMode(False)
        self.page_list.setSpacing(4)
        self.viewer = PDFViewer()

        self.add_button = QPushButton("Add PDFs...")
        self.remove_button = QPushButton("Remove Selected File")
        self.clear_button = QPushButton("Clear Files")
        self.reset_pages_button = QPushButton("Reset Pages From Files")
        self.delete_page_button = QPushButton("Delete Selected Page")
        self.save_button = QPushButton("Save Merged PDF...")

        self._initialize_password_support()
        self._build_layout()
        self._connect_signals()
        self._update_actions()

    def _build_layout(self) -> None:
        """Build the merge tab layout."""
        instruction_label = QLabel(
            "Add PDFs, reorder source files, then adjust the merged page list before saving."
        )
        instruction_label.setWordWrap(True)

        source_buttons = QHBoxLayout()
        source_buttons.setContentsMargins(0, 0, 0, 0)
        source_buttons.setSpacing(8)
        source_buttons.addWidget(self.add_button)
        source_buttons.addWidget(self.remove_button)
        source_buttons.addWidget(self.clear_button)

        source_group = QGroupBox("Source PDFs")
        source_layout = QVBoxLayout(source_group)
        source_layout.setSpacing(10)
        source_layout.addLayout(source_buttons)
        source_layout.addWidget(self.file_list)

        page_buttons = QHBoxLayout()
        page_buttons.setContentsMargins(0, 0, 0, 0)
        page_buttons.setSpacing(8)
        page_buttons.addWidget(self.reset_pages_button)
        page_buttons.addWidget(self.delete_page_button)

        page_group = QGroupBox("Merged Page Order")
        page_layout = QVBoxLayout(page_group)
        page_layout.setSpacing(10)
        page_layout.addLayout(page_buttons)
        page_layout.addWidget(self.page_list)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left_layout.addWidget(instruction_label)
        left_layout.addWidget(source_group)
        left_layout.addWidget(page_group, 1)
        left_layout.addWidget(self.save_button)

        left_panel = QWidget()
        left_panel.setLayout(left_layout)

        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(self.viewer)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([430, 900])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(splitter)

    def _connect_signals(self) -> None:
        """Connect UI actions for the merge workflow."""
        self.add_button.clicked.connect(self._browse_files)
        self.remove_button.clicked.connect(self.file_list.remove_selected_items)
        self.clear_button.clicked.connect(self.file_list.clear_files)
        self.reset_pages_button.clicked.connect(self._rebuild_page_plan_from_files)
        self.delete_page_button.clicked.connect(self._delete_selected_page)
        self.save_button.clicked.connect(self._save_merged_pdf)

        self.file_list.filesChanged.connect(self._handle_source_files_changed)
        self.file_list.currentPdfChanged.connect(lambda _path: self._update_actions())
        self.page_list.itemSelectionChanged.connect(self._sync_preview_to_selected_page)
        self.page_list.model().rowsMoved.connect(self._handle_page_list_reordered)

    def _browse_files(self) -> None:
        """Open a file dialog for selecting PDFs to merge."""
        selected_files, _ = QFileDialog.getOpenFileNames(
            self,
            "Add PDFs to Merge",
            str(Path.home()),
            "PDF Files (*.pdf)",
        )
        if selected_files:
            self.file_list.add_pdf_paths(selected_files)

    def _handle_source_files_changed(self, _files: list[str]) -> None:
        """Rebuild the merged page plan whenever the source file set changes."""
        self._rebuild_page_plan_from_files()

    def _rebuild_page_plan_from_files(self) -> None:
        """Expand the source PDFs into an editable page-by-page merge plan."""
        input_paths = self.file_list.all_paths()
        if not input_paths:
            self._merge_plan = []
            self.page_list.clear()
            self.viewer.clear()
            self._update_actions()
            return

        try:
            merge_plan = self._run_password_aware_operation(
                lambda passwords: build_merge_plan(input_paths, passwords),
                "Merge Setup Failed",
            )
            if merge_plan is None:
                self._merge_plan = []
                self.page_list.clear()
                self.viewer.clear()
                self._update_actions()
                return
        except Exception as error:
            LOGGER.exception("Failed to build merge page plan")
            QMessageBox.critical(
                self,
                "Merge Setup Failed",
                f"Could not build the merged page list.\n\n{error}",
            )
            self._merge_plan = []
            self.page_list.clear()
            self.viewer.clear()
            self._update_actions()
            return

        self._merge_plan = list(merge_plan)
        self._populate_page_list()
        self._refresh_merged_preview()

    def _populate_page_list(self) -> None:
        """Populate the merged page list from the current merge plan."""
        self.page_list.blockSignals(True)
        self.page_list.clear()

        for merge_page in self._merge_plan:
            item = QListWidgetItem(merge_page.page_label)
            item.setToolTip(str(merge_page.source_path))
            item.setData(Qt.ItemDataRole.UserRole, merge_page)
            self.page_list.addItem(item)

        if self.page_list.count():
            self.page_list.setCurrentRow(0)

        self.page_list.blockSignals(False)
        self._update_actions()

    def _handle_page_list_reordered(self, *_args) -> None:
        """Sync internal page order and refresh the merged preview after reordering."""
        self._sync_merge_plan_from_page_list()
        self._refresh_merged_preview()

    def _sync_merge_plan_from_page_list(self) -> None:
        """Rebuild the merge plan from the current page list ordering."""
        merge_plan: list[MergePage] = []
        for row in range(self.page_list.count()):
            item = self.page_list.item(row)
            merge_page = item.data(Qt.ItemDataRole.UserRole)
            if merge_page is not None:
                merge_plan.append(merge_page)
        self._merge_plan = merge_plan
        self._update_actions()

    def _delete_selected_page(self) -> None:
        """Delete the selected page from the merged page list."""
        current_row = self.page_list.currentRow()
        if current_row < 0:
            return

        self.page_list.takeItem(current_row)
        if self.page_list.count():
            self.page_list.setCurrentRow(max(0, min(current_row, self.page_list.count() - 1)))

        self._sync_merge_plan_from_page_list()
        self._refresh_merged_preview()

    def _refresh_merged_preview(self) -> None:
        """Regenerate and display the current merged preview."""
        if not self._merge_plan:
            self.viewer.clear()
            self._update_actions()
            return

        self.viewer.clear()

        try:
            preview_file = self._run_password_aware_operation(
                lambda passwords: merge_page_plan(self._merge_plan, self._preview_output_path, passwords),
                "Preview Failed",
            )
            if preview_file is None:
                self.viewer.clear()
                self._update_actions()
                return
        except Exception as error:
            LOGGER.exception("Failed to generate merge preview")
            QMessageBox.critical(
                self,
                "Preview Failed",
                f"Could not generate the merged preview.\n\n{error}",
            )
            self.viewer.clear()
            self._update_actions()
            return

        self.viewer.load_pdf(preview_file, show_error_dialog=False)
        self._sync_preview_to_selected_page()
        self._update_actions()

    def _sync_preview_to_selected_page(self) -> None:
        """Jump the viewer to the currently selected merged page."""
        current_row = self.page_list.currentRow()
        if current_row >= 0:
            self.viewer.go_to_page(current_row)
        self._update_actions()

    def _update_actions(self) -> None:
        """Enable or disable actions depending on the current list state."""
        has_files = self.file_list.count() > 0
        has_file_selection = self.file_list.currentItem() is not None
        has_pages = self.page_list.count() > 0
        has_page_selection = self.page_list.currentItem() is not None

        self.remove_button.setEnabled(has_file_selection)
        self.clear_button.setEnabled(has_files)
        self.reset_pages_button.setEnabled(has_files)
        self.delete_page_button.setEnabled(has_page_selection)
        self.save_button.setEnabled(has_pages)

    def _save_merged_pdf(self) -> None:
        """Open a save dialog and merge the selected PDF pages."""
        if not self._merge_plan:
            QMessageBox.warning(
                self,
                "No Pages Selected",
                "Add PDFs and keep at least one page in the merged page list before saving.",
            )
            return

        default_output = self.file_list.all_paths()[0].with_name("merged.pdf")
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Merged PDF",
            str(default_output),
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return

        try:
            result = self._run_password_aware_operation(
                lambda passwords: merge_page_plan(self._merge_plan, output_path, passwords),
                "Merge Failed",
            )
            if result is None:
                return
        except Exception as error:
            LOGGER.exception("Merge operation failed")
            QMessageBox.critical(self, "Merge Failed", f"Could not merge the selected PDFs.\n\n{error}")
            return

        QMessageBox.information(self, "Merge Complete", f"Merged PDF saved to:\n{output_path}")
