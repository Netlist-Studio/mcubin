from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QPushButton, QLabel, QFrame,
)
from sqlalchemy.exc import IntegrityError

from mcubin.database import Session
from mcubin.models import Part


def _form_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("formLabel")
    return lbl


def _divider() -> QFrame:
    div = QFrame()
    div.setObjectName("divider")
    div.setFixedHeight(1)
    return div


class AddPartScreen(QWidget):
    """
    Dedicated screen for adding a new part.

    Scan order: MPN → Supplier PN → Quantity
    Each field's Enter key advances focus to the next.
    """

    def __init__(self, on_done: Callable[[bool], None], parent=None):
        super().__init__(parent)
        self._on_done = on_done
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        title = QLabel("Add Part")
        title.setObjectName("screenTitle")
        root.addWidget(title)
        root.addSpacing(4)

        subtitle = QLabel("Scan MPN, Supplier PN, then Quantity — or fill in manually.")
        subtitle.setObjectName("screenSubtitle")
        root.addWidget(subtitle)
        root.addSpacing(28)

        # ── Scan targets (primary flow) ───────────────────────────────────
        scan_label = QLabel("SCAN FIELDS")
        scan_label.setObjectName("sectionLabel")
        root.addWidget(scan_label)
        root.addSpacing(10)

        scan_form = QFormLayout()
        scan_form.setSpacing(10)
        scan_form.setLabelAlignment(Qt.AlignRight)
        scan_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.mpn_edit = QLineEdit()
        self.mpn_edit.setObjectName("barcodeInput")
        self.mpn_edit.setPlaceholderText("Scan or type MPN…")

        self.supplier_pn_edit = QLineEdit()
        self.supplier_pn_edit.setObjectName("barcodeInput")
        self.supplier_pn_edit.setPlaceholderText("Scan or type distributor PN…")

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 999999)
        self.qty_spin.setValue(1)

        scan_form.addRow(_form_label("MPN"), self.mpn_edit)
        scan_form.addRow(_form_label("Supplier PN"), self.supplier_pn_edit)
        scan_form.addRow(_form_label("Quantity"), self.qty_spin)
        root.addLayout(scan_form)

        # Enter advances through scan fields
        self.mpn_edit.returnPressed.connect(self.supplier_pn_edit.setFocus)
        self.supplier_pn_edit.returnPressed.connect(self.qty_spin.setFocus)

        root.addSpacing(24)
        root.addWidget(_divider())
        root.addSpacing(24)

        # ── Additional details ────────────────────────────────────────────
        details_label = QLabel("ADDITIONAL DETAILS")
        details_label.setObjectName("sectionLabel")
        root.addWidget(details_label)
        root.addSpacing(10)

        detail_form = QFormLayout()
        detail_form.setSpacing(10)
        detail_form.setLabelAlignment(Qt.AlignRight)
        detail_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.supplier_edit = QLineEdit()
        self.supplier_edit.setPlaceholderText("e.g. Mouser, DigiKey")
        self.mfr_edit = QLineEdit()
        self.mfr_edit.setPlaceholderText("e.g. STMicroelectronics")
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Short description")
        self.loc_edit = QLineEdit()
        self.loc_edit.setPlaceholderText("e.g. Bin A3")
        self.cat_edit = QLineEdit()
        self.cat_edit.setPlaceholderText("e.g. MCU")

        detail_form.addRow(_form_label("Supplier"), self.supplier_edit)
        detail_form.addRow(_form_label("Manufacturer"), self.mfr_edit)
        detail_form.addRow(_form_label("Description"), self.desc_edit)
        detail_form.addRow(_form_label("Location"), self.loc_edit)
        detail_form.addRow(_form_label("Category"), self.cat_edit)
        root.addLayout(detail_form)

        root.addStretch()
        root.addWidget(_divider())
        root.addSpacing(16)

        # ── Actions ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.save_btn = QPushButton("Save Part")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.clicked.connect(self._save)
        btn_row.addWidget(self.save_btn)
        root.addLayout(btn_row)

        self.feedback = QLabel("")
        self.feedback.setObjectName("feedbackError")
        self.feedback.setAlignment(Qt.AlignRight)
        root.addWidget(self.feedback)

    # ── Public ────────────────────────────────────────────────────────────

    def reset(self):
        for w in (self.mpn_edit, self.supplier_pn_edit, self.supplier_edit,
                  self.mfr_edit, self.desc_edit, self.loc_edit, self.cat_edit):
            w.clear()
        self.qty_spin.setValue(1)
        self.feedback.setText("")
        QTimer.singleShot(0, self.mpn_edit.setFocus)

    # ── Handlers ──────────────────────────────────────────────────────────

    def _save(self):
        data = {
            "mpn":         self.mpn_edit.text().strip() or None,
            "supplier_pn": self.supplier_pn_edit.text().strip() or None,
            "quantity":    self.qty_spin.value(),
            "supplier":    self.supplier_edit.text().strip() or None,
            "manufacturer": self.mfr_edit.text().strip() or None,
            "description": self.desc_edit.text().strip() or None,
            "location":    self.loc_edit.text().strip() or None,
            "category":    self.cat_edit.text().strip() or None,
        }
        try:
            with Session() as session:
                session.add(Part(**data))
                session.commit()
            self._on_done(True)
        except IntegrityError:
            self.feedback.setText("Failed to save — check for duplicate entries.")
