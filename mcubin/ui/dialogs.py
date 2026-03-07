from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QMessageBox, QVBoxLayout,
)


def get_text(parent, title: str, label: str, text: str = "") -> str | None:
    """Styled single-line text input dialog. Returns stripped text or None if cancelled."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumWidth(320)

    lay = QVBoxLayout(dlg)
    lay.setSpacing(12)
    lay.setContentsMargins(20, 16, 20, 16)
    lay.addWidget(QLabel(label))

    edit = QLineEdit(text)
    edit.selectAll()
    lay.addWidget(edit)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    for btn in buttons.buttons():
        btn.setIcon(QIcon())
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    edit.returnPressed.connect(dlg.accept)
    lay.addWidget(buttons)

    if dlg.exec() == QDialog.Accepted:
        return edit.text().strip() or None
    return None


def confirm(parent, message: str) -> bool:
    """Show a styled confirmation dialog. Returns True if the user confirmed."""
    dlg = QMessageBox(parent)
    dlg.setWindowTitle("Confirm")
    dlg.setText(message)
    dlg.setIcon(QMessageBox.NoIcon)
    dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    dlg.setDefaultButton(QMessageBox.No)
    for btn in dlg.buttons():
        if dlg.buttonRole(btn) == QMessageBox.YesRole:
            btn.setObjectName("dialogBtnConfirm")
        else:
            btn.setObjectName("dialogBtnCancel")
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.setIcon(QIcon())
    return dlg.exec() == QMessageBox.Yes
