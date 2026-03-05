from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
)
from mcubin.models import Part
from mcubin.ui.part_form import PartForm, _divider


class EditPartDialog(QDialog):
    def __init__(self, part: Part, on_status=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Part")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._on_status = on_status
        self._build_ui(part)

    def _build_ui(self, part: Part):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(0)

        title = QLabel("Edit Part")
        title.setObjectName("screenTitle")
        root.addWidget(title)
        root.addSpacing(16)
        root.addWidget(_divider())
        root.addSpacing(16)

        self.form = PartForm(scan_mode=False, on_status=self._on_status)
        self.form.populate(part)
        root.addWidget(self.form)

        root.addSpacing(20)
        root.addWidget(_divider())
        root.addSpacing(16)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("primaryBtn")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

    def get_data(self) -> dict:
        return self.form.get_data()
