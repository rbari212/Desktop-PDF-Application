"""Main window for the desktop PDF application."""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from ui.compress_tab import CompressTab
from ui.extract_tab import ExtractTab
from ui.merge_tab import MergeTab
from ui.password_tab import PasswordTab
from ui.rotate_tab import RotateTab
from ui.split_tab import SplitTab


class MainWindow(QMainWindow):
    """Primary application window hosting all PDF operation tabs."""

    def __init__(self, parent=None) -> None:
        """Initialize the main window."""
        super().__init__(parent)
        self.setWindowTitle("PDF Merge Application")
        self.resize(1360, 880)
        self.setMinimumSize(1180, 760)

        tab_widget = QTabWidget()
        tab_widget.setDocumentMode(True)
        tab_widget.addTab(MergeTab(), "Merge")
        tab_widget.addTab(SplitTab(), "Split")
        tab_widget.addTab(RotateTab(), "Rotate")
        tab_widget.addTab(ExtractTab(), "Extract")
        tab_widget.addTab(PasswordTab(), "Password")
        tab_widget.addTab(CompressTab(), "Compress")

        self.setCentralWidget(tab_widget)
        self.statusBar().showMessage("Ready")
        self._apply_styles()

    def _apply_styles(self) -> None:
        """Apply a minimal shared style across the application."""
        self.setStyleSheet(
            """
            QWidget {
                font-size: 13px;
            }

            QMainWindow {
                background: #edf2f6;
            }

            QTabWidget::pane {
                background: #ffffff;
                border: 1px solid #d6dde5;
                border-radius: 12px;
                top: -1px;
            }

            QTabBar::tab {
                background: #dbe3ea;
                color: #23313f;
                padding: 10px 18px;
                margin-right: 6px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }

            QTabBar::tab:selected {
                background: #ffffff;
            }

            QPushButton {
                background: #243446;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
            }

            QPushButton:hover {
                background: #314559;
            }

            QPushButton:disabled {
                background: #9aa6b2;
                color: #f3f4f6;
            }

            QLineEdit,
            QComboBox,
            QListWidget,
            QPdfPageSelector {
                background: #f8fafb;
                border: 1px solid #d6dde5;
                border-radius: 8px;
                padding: 6px;
            }

            QGroupBox {
                border: 1px solid #d6dde5;
                border-radius: 10px;
                margin-top: 12px;
                font-weight: 600;
                padding-top: 8px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }

            QLabel#viewerFileLabel {
                color: #4c5a67;
                font-weight: 600;
            }

            QSplitter::handle {
                background: #d6dde5;
                width: 2px;
            }
            """
        )
