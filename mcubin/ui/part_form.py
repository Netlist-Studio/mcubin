"""
Shared form widget used by both AddPartScreen and EditPartDialog.
"""
import logging
import requests as _requests
import urllib.request
import urllib.error

log = logging.getLogger(__name__)
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QSpinBox, QLabel, QFrame, QComboBox,
    QPushButton, QDialog, QAbstractItemView, QListWidget,
    QListWidgetItem, QDialogButtonBox, QApplication,
)
import mcubin.config as _config
from mcubin.database import Session, IMAGES_DIR
from mcubin.models import Location, Part, Supplier
from mcubin.suppliers import get_provider_api
from mcubin.suppliers.base import PartLookupResult


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


def _load_suppliers() -> list[tuple[int, str]]:
    with Session() as session:
        rows = session.query(Supplier.id, Supplier.name).order_by(Supplier.name).all()
    return list(rows)


def download_image(part_id: int, image_url: str) -> str | None:
    """Download image_url and save to IMAGES_DIR/{part_id}{ext}. Returns filename or None."""
    from urllib.parse import urlparse
    try:
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(urlparse(image_url).path).suffix
        filename = f"{part_id}{ext}"
        dest = IMAGES_DIR / filename
        with _requests.get(image_url, headers={"User-Agent": "Wget/1.21.3"}, stream=True, timeout=(5, 30)) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                log.warning("unexpected content-type: %s", content_type)
                raise ValueError(f"not an image: {content_type}")
            dest.write_bytes(resp.content)
        return filename
    except Exception as e:
        log.error("image download error: %s", e)
        return None


def download_image_async(part_id: int, image_url: str) -> None:
    """Download image in a background thread and update part.image_path when done."""
    import threading

    def _run():
        log.debug("downloading image for part %s: %s", part_id, image_url)
        filename = download_image(part_id, image_url)
        if filename:
            log.debug("image saved: %s", filename)
            with Session() as session:
                part = session.get(Part, part_id)
                if part:
                    part.image_path = filename
                    session.commit()
        else:
            log.warning("image download failed for part %s", part_id)

    threading.Thread(target=_run, daemon=True).start()


class _PickResultDialog(QDialog):
    """Pick one result from a list of PartLookupResults."""

    def __init__(self, results: list[PartLookupResult], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Part")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._results = results
        self._selected: PartLookupResult | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        root.addWidget(QLabel("Multiple results found. Select one:"))

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        for r in self._results:
            text = " · ".join(filter(None, [r.mpn, r.manufacturer, r.description]))
            item = QListWidgetItem(text or "(no description)")
            self._list.addItem(item)
        if self._results:
            self._list.setCurrentRow(0)
        self._list.itemDoubleClicked.connect(self._accept)
        root.addWidget(self._list)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _accept(self):
        row = self._list.currentRow()
        if row >= 0:
            self._selected = self._results[row]
        self.accept()

    def get_selected(self) -> PartLookupResult | None:
        return self._selected


class PartForm(QWidget):
    """
    All editable fields for a Part, split into two sections:

    SCAN FIELDS        — MPN, Supplier PN, Quantity (scanner targets)
    ADDITIONAL DETAILS — Supplier, Manufacturer, Description, Location, Category

    In Add mode, Enter on MPN advances to Supplier PN, then to Quantity.
    In Edit mode the scan-field styling is omitted (fields are pre-filled).
    """

    def __init__(self, scan_mode: bool = True, on_lookup_done=None, on_status=None, parent=None):
        super().__init__(parent)
        self._scan_mode = scan_mode
        self._on_lookup_done = on_lookup_done
        self._on_status = on_status
        self._lookup_extras: dict = {}  # datasheet, rohs_status, attributes, unit_price, price_breaks, image_url
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

        # Lookup button
        lookup_row = QHBoxLayout()
        lookup_row.addStretch()
        self._lookup_btn = QPushButton("Lookup")
        self._lookup_btn.clicked.connect(self._do_lookup)
        lookup_row.addWidget(self._lookup_btn)
        root.addSpacing(8)
        root.addLayout(lookup_row)

        root.addSpacing(16)
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

        self.supplier_combo = QComboBox()
        self.supplier_combo.setPlaceholderText("Select supplier…")
        self._reload_suppliers()

        self.mfr_edit = QLineEdit()
        self.mfr_edit.setPlaceholderText("e.g. STMicroelectronics")
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Short description")

        self.loc_combo = QComboBox()
        self.loc_combo.setEditable(True)
        self.loc_combo.setInsertPolicy(QComboBox.NoInsert)
        self.loc_combo.setMinimumWidth(200)
        self.loc_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.loc_combo.lineEdit().setPlaceholderText("e.g. Bin A3")
        self._reload_locations()

        self.cat_edit = QLineEdit()
        self.cat_edit.setPlaceholderText("e.g. MCU")

        detail_form.addRow(_form_label("Supplier"), self.supplier_combo)
        detail_form.addRow(_form_label("Manufacturer"), self.mfr_edit)
        detail_form.addRow(_form_label("Description"), self.desc_edit)
        detail_form.addRow(_form_label("Location"), self.loc_combo)
        detail_form.addRow(_form_label("Category"), self.cat_edit)
        root.addLayout(detail_form)

    def _reload_suppliers(self):
        self.supplier_combo.blockSignals(True)
        current_id = self.supplier_combo.currentData()
        self.supplier_combo.clear()
        self.supplier_combo.addItem("", userData=None)
        for sup_id, name in _load_suppliers():
            self.supplier_combo.addItem(name, userData=sup_id)
        idx = self.supplier_combo.findData(current_id)
        self.supplier_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.supplier_combo.blockSignals(False)

    def _reload_locations(self):
        self.loc_combo.blockSignals(True)
        current_text = self.loc_combo.currentText()
        self.loc_combo.clear()
        self.loc_combo.addItem("")
        for loc_id, name in _load_locations():
            self.loc_combo.addItem(name, userData=loc_id)
        self.loc_combo.setCurrentText(current_text)
        self.loc_combo.blockSignals(False)

    def _show_status(self, msg: str, timeout: int = 0):
        if self._on_status:
            self._on_status(msg, timeout)

    def _do_lookup(self):
        self._show_status("")
        supplier_id = self.supplier_combo.currentData()
        if not supplier_id:
            self._show_status("Select a supplier first.", 4000)
            return

        with Session() as session:
            sup = session.get(Supplier, supplier_id)
            if not sup:
                return
            provider = sup.provider
            settings = sup.settings or {}

        api_cls = get_provider_api(provider)
        if not api_cls:
            self._show_status(f"No API support for {provider}.", 4000)
            return
        if not api_cls.is_configured(settings):
            self._show_status("API key not configured — check Suppliers settings.", 5000)
            return

        supplier_pn = self.supplier_pn_edit.text().strip()
        mpn = self.mpn_edit.text().strip()
        if not supplier_pn and not mpn:
            self._show_status("Enter MPN or Supplier PN.", 4000)
            return

        api = api_cls(settings)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if supplier_pn:
                results = api.lookup_by_supplier_pn(supplier_pn)
            else:
                results = api.lookup_by_mpn(mpn)
            if not results:
                self._show_status("No results found.", 4000)
                return
            if len(results) == 1 or _config.get("scan_accept_first"):
                result = results[0]
            else:
                QApplication.restoreOverrideCursor()
                dlg = _PickResultDialog(results, self)
                if not dlg.exec() or not dlg.get_selected():
                    return
                result = dlg.get_selected()
                QApplication.setOverrideCursor(Qt.WaitCursor)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_status(f"Lookup failed: {e}", 6000)
            return
        finally:
            QApplication.restoreOverrideCursor()

        self._apply_result(result)
        self._show_status(f"Lookup: {result.mpn or result.supplier_pn}", 3000)
        if self._on_lookup_done:
            self._on_lookup_done()

    def _apply_result(self, result: PartLookupResult):
        if result.mpn:
            self.mpn_edit.setText(result.mpn)
        if result.supplier_pn:
            self.supplier_pn_edit.setText(result.supplier_pn)
        if result.manufacturer:
            self.mfr_edit.setText(result.manufacturer)
        if result.description:
            self.desc_edit.setText(result.description)
        if result.category:
            self.cat_edit.setText(result.category)

        self._lookup_extras = {
            "datasheet":    result.datasheet,
            "rohs_status":  result.rohs_status,
            "attributes":   result.attributes or {},
            "unit_price":   result.unit_price,
            "price_breaks": result.price_breaks or [],
            "image_url":    result.image_url,
            "supplier_data_updated_at": datetime.now(timezone.utc),
        }

    def populate(self, part: Part):
        self.mpn_edit.setText(part.mpn or "")
        self.supplier_pn_edit.setText(part.supplier_pn or "")
        self.qty_spin.setValue(part.quantity)
        idx = self.supplier_combo.findData(part.supplier_id)
        self.supplier_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.mfr_edit.setText(part.manufacturer or "")
        self.desc_edit.setText(part.description or "")
        self.loc_combo.setCurrentText(part.location or "")
        self.cat_edit.setText(part.category or "")

    def clear(self):
        for w in (self.mpn_edit, self.supplier_pn_edit, self.mfr_edit,
                  self.desc_edit, self.cat_edit):
            w.clear()
        self.supplier_combo.setCurrentIndex(0)
        self.loc_combo.setCurrentText("")
        self.qty_spin.setValue(1)
        self._lookup_extras = {}
        self._reload_suppliers()
        self._reload_locations()

    def get_data(self) -> dict:
        data = {
            "mpn":           self.mpn_edit.text().strip() or None,
            "supplier_pn":   self.supplier_pn_edit.text().strip() or None,
            "quantity":      self.qty_spin.value(),
            "supplier_id":   self.supplier_combo.currentData(),
            "manufacturer":  self.mfr_edit.text().strip() or None,
            "description":   self.desc_edit.text().strip() or None,
            "location_name": self.loc_combo.currentText().strip() or None,
            "category":      self.cat_edit.text().strip() or None,
        }
        data.update(self._lookup_extras)
        return data

    def validate(self) -> str | None:
        """Return an error message if the form is invalid, or None if valid."""
        data = self.get_data()
        if not data.get("mpn") and not data.get("supplier_pn"):
            return "Enter at least an MPN or Supplier PN."
        return None

    def focus_first(self):
        self.mpn_edit.setFocus()
