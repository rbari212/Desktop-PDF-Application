"""Shared UI helpers for retrying operations that require PDF passwords."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from pdf_tools._common import PdfPasswordError

LOGGER = logging.getLogger(__name__)


class PasswordAwareOperationMixin:
    """Mixin that prompts for PDF passwords and retries the requested operation."""

    def _initialize_password_support(self) -> None:
        """Create a cache of passwords already entered by the user."""
        self._pdf_passwords: dict[str, str] = {}

    def _run_password_aware_operation(self, operation, dialog_title: str):
        """Run an operation, prompting for PDF passwords until it succeeds or is cancelled."""
        while True:
            try:
                return operation(self._pdf_passwords)
            except PdfPasswordError as error:
                LOGGER.info("Password required for %s", error.file_path)
                password = self._prompt_for_password(error.file_path, str(error))
                if password is None:
                    return None
                self._pdf_passwords[str(error.file_path)] = password
            except Exception:
                raise

    def _prompt_for_password(self, file_path: Path, message: str) -> str | None:
        """Ask the user for the password to open an encrypted PDF."""
        password, accepted = QInputDialog.getText(
            self,
            "PDF Password Required",
            f"{message}\n\nEnter the password for:\n{file_path.name}",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            QMessageBox.information(self, "Operation Cancelled", "The operation was cancelled.")
            return None

        if not password:
            QMessageBox.warning(self, "Missing Password", "Enter a password to continue.")
            return self._prompt_for_password(file_path, message)

        return password
