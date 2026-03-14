"""Application entry point for the PDF desktop application."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def configure_logging() -> None:
    """Configure application-wide logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> int:
    """Create and run the Qt application."""
    configure_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("PDF Merge Application")
    app.setOrganizationName("PDF Merge Application")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
