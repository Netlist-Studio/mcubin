from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QPushButton, QLabel, QFrame,
)
from mcubin.models import Part


class AddPartDialog(QDialog):
    def __init__(self, parent=None, barcode: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Add Part")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._build_ui(barcode)

    def _build_ui(self, barcode: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("Add Part")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        layout.addWidget(title)

        # Divider
        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        layout.addWidget(div)

        # Form
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        def label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #888888; font-size: 12px;")
            return lbl

        self.barcode_edit = QLineEdit(barcode)
        self.barcode_edit.setPlaceholderText("Scan or type barcode…")
        self.mpn_edit = QLineEdit()
        self.mpn_edit.setPlaceholderText("e.g. STM32F401RET6")
        self.mfr_edit = QLineEdit()
        self.mfr_edit.setPlaceholderText("e.g. STMicroelectronics")
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Short description")
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 999999)
        self.qty_spin.setValue(1)
        self.loc_edit = QLineEdit()
        self.loc_edit.setPlaceholderText("e.g. Bin A3")
        self.cat_edit = QLineEdit()
        self.cat_edit.setPlaceholderText("e.g. MCU")

        form.addRow(label("Barcode"), self.barcode_edit)
        form.addRow(label("MPN"), self.mpn_edit)
        form.addRow(label("Manufacturer"), self.mfr_edit)
        form.addRow(label("Description"), self.desc_edit)
        form.addRow(label("Quantity"), self.qty_spin)
        form.addRow(label("Location"), self.loc_edit)
        form.addRow(label("Category"), self.cat_edit)
        layout.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Part")
        save_btn.setObjectName("primaryBtn")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def get_part_data(self) -> dict:
        return {
            "barcode": self.barcode_edit.text().strip() or None,
            "mpn": self.mpn_edit.text().strip() or None,
            "manufacturer": self.mfr_edit.text().strip() or None,
            "description": self.desc_edit.text().strip() or None,
            "quantity": self.qty_spin.value(),
            "location": self.loc_edit.text().strip() or None,
            "category": self.cat_edit.text().strip() or None,
        }
