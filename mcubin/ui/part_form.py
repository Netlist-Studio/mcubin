"""
Shared form widget used by both AddPartScreen and EditPartDialog.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QLabel, QFrame, QComboBox,
)
from mcubin.database import Session
from mcubin.models import Location, Part


def _form_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("formLabel")
    return lbl


def _divider() -> QFrame:
    div = QFrame()
    div.setObjectName("divider")
    div.setFixedHeight(1)
    return div


def _load_locations() -> list[tuple[int, str]]:
    with Session() as session:
        rows = session.query(Location.id, Location.name).order_by(Location.name).all()
    return list(rows)


class PartForm(QWidget):
    """
    All editable fields for a Part, split into two sections:

    SCAN FIELDS        — MPN, Supplier PN, Quantity (scanner targets)
    ADDITIONAL DETAILS — Supplier, Manufacturer, Description, Location, Category

    In Add mode, Enter on MPN advances to Supplier PN, then to Quantity.
    In Edit mode the scan-field styling is omitted (fields are pre-filled).
    """

    def __init__(self, scan_mode: bool = True, parent=None):
        super().__init__(parent)
        self._scan_mode = scan_mode
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Scan fields ───────────────────────────────────────────────────
        scan_label = QLabel("SCAN FIELDS" if self._scan_mode else "PART ID")
        scan_label.setObjectName("sectionLabel")
        root.addWidget(scan_label)
        root.addSpacing(10)

        scan_form = QFormLayout()
        scan_form.setSpacing(10)
        scan_form.setLabelAlignment(Qt.AlignRight)
        scan_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.mpn_edit = QLineEdit()
        self.mpn_edit.setPlaceholderText("e.g. STM32F401RET6")
        self.supplier_pn_edit = QLineEdit()
        self.supplier_pn_edit.setPlaceholderText("e.g. 296-1002-ND")
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 999999)
        self.qty_spin.setValue(1)

        if self._scan_mode:
            self.mpn_edit.setObjectName("barcodeInput")
            self.mpn_edit.setPlaceholderText("Scan or type MPN…")
            self.supplier_pn_edit.setObjectName("barcodeInput")
            self.supplier_pn_edit.setPlaceholderText("Scan or type distributor PN…")
            # Enter advances through scan fields
            self.mpn_edit.returnPressed.connect(self.supplier_pn_edit.setFocus)
            self.supplier_pn_edit.returnPressed.connect(self.qty_spin.setFocus)

        scan_form.addRow(_form_label("MPN"), self.mpn_edit)
        scan_form.addRow(_form_label("Supplier PN"), self.supplier_pn_edit)
        scan_form.addRow(_form_label("Quantity"), self.qty_spin)
        root.addLayout(scan_form)

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

        self.loc_combo = QComboBox()
        self.loc_combo.setEditable(True)
        self.loc_combo.setInsertPolicy(QComboBox.NoInsert)
        self.loc_combo.lineEdit().setPlaceholderText("e.g. Bin A3")
        self._reload_locations()

        self.cat_edit = QLineEdit()
        self.cat_edit.setPlaceholderText("e.g. MCU")

        detail_form.addRow(_form_label("Supplier"), self.supplier_edit)
        detail_form.addRow(_form_label("Manufacturer"), self.mfr_edit)
        detail_form.addRow(_form_label("Description"), self.desc_edit)
        detail_form.addRow(_form_label("Location"), self.loc_combo)
        detail_form.addRow(_form_label("Category"), self.cat_edit)
        root.addLayout(detail_form)

    def _reload_locations(self):
        self.loc_combo.blockSignals(True)
        current_text = self.loc_combo.currentText()
        self.loc_combo.clear()
        self.loc_combo.addItem("")
        for loc_id, name in _load_locations():
            self.loc_combo.addItem(name, userData=loc_id)
        self.loc_combo.setCurrentText(current_text)
        self.loc_combo.blockSignals(False)

    def populate(self, part: Part):
        self.mpn_edit.setText(part.mpn or "")
        self.supplier_pn_edit.setText(part.supplier_pn or "")
        self.qty_spin.setValue(part.quantity)
        self.supplier_edit.setText(part.supplier or "")
        self.mfr_edit.setText(part.manufacturer or "")
        self.desc_edit.setText(part.description or "")
        self.loc_combo.setCurrentText(part.location or "")
        self.cat_edit.setText(part.category or "")

    def clear(self):
        for w in (self.mpn_edit, self.supplier_pn_edit, self.supplier_edit,
                  self.mfr_edit, self.desc_edit, self.cat_edit):
            w.clear()
        self.loc_combo.setCurrentText("")
        self.qty_spin.setValue(1)
        self._reload_locations()

    def get_data(self) -> dict:
        return {
            "mpn":           self.mpn_edit.text().strip() or None,
            "supplier_pn":   self.supplier_pn_edit.text().strip() or None,
            "quantity":      self.qty_spin.value(),
            "supplier":      self.supplier_edit.text().strip() or None,
            "manufacturer":  self.mfr_edit.text().strip() or None,
            "description":   self.desc_edit.text().strip() or None,
            "location_name": self.loc_combo.currentText().strip() or None,
            "category":      self.cat_edit.text().strip() or None,
        }

    def focus_first(self):
        self.mpn_edit.setFocus()
