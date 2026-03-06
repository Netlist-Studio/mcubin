from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMessageBox


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
