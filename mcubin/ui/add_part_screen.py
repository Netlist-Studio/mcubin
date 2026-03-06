import logging
from typing import Callable

log = logging.getLogger(__name__)

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
)
from sqlalchemy.exc import IntegrityError

import mcubin.config as config
from mcubin.database import Session
from mcubin.models import Location, Part
from mcubin.ui.part_form import PartForm, download_image_async


def _resolve_location(session, name: str | None) -> int | None:
    if not name:
        return None
    loc = session.query(Location).filter_by(name=name).first()
    if not loc:
        loc = Location(name=name)
        session.add(loc)
        session.flush()
    return loc.id


class AddPartScreen(QWidget):
    def __init__(self, on_part_saved: Callable, on_status: Callable = None, parent=None):
        super().__init__(parent)
        self._on_part_saved = on_part_saved
        self._on_status = on_status
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

        self.form = PartForm(scan_mode=True, on_lookup_done=self._after_lookup, on_status=self._on_status)
        root.addWidget(self.form)

        root.addStretch()

        from mcubin.ui.part_form import _divider
        root.addWidget(_divider())
        root.addSpacing(16)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._save_btn = QPushButton("Save Part")
        self._save_btn.setObjectName("primaryBtn")
        self._save_btn.clicked.connect(self._save)
        btn_row.addWidget(self._save_btn)
        root.addLayout(btn_row)

        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._save)

        # Event filter on qty_spin for auto-lookup
        self.form.qty_spin.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.form.qty_spin and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if config.get("scan_auto_lookup"):
                    self.form._do_lookup()
                self._save_btn.setFocus()
                return True
        return super().eventFilter(obj, event)

    def _after_lookup(self):
        self._save_btn.setFocus()

    def reset(self):
        self.form.clear()
        QTimer.singleShot(0, self.form.focus_first)

    def _save(self):
        # Capture sticky values before clear
        cfg = config.load()
        sticky_supplier_idx = self.form.supplier_combo.currentIndex() if cfg.get("scan_sticky_supplier") else -1
        sticky_supplier_id  = self.form.supplier_combo.currentData()  if cfg.get("scan_sticky_supplier") else None
        sticky_location     = self.form.loc_combo.currentText()        if cfg.get("scan_sticky_location")  else ""
        sticky_category     = self.form.cat_edit.text()                if cfg.get("scan_sticky_category")   else ""

        log.debug("_save called")
        err = self.form.validate()
        if err:
            if self._on_status:
                self._on_status(err, 4000)
            return

        saved_mpn = self.form.mpn_edit.text().strip() or self.form.supplier_pn_edit.text().strip() or "Part"

        try:
            data = self.form.get_data()
            location_name = data.pop("location_name")
            image_url = data.pop("image_url", None)
            with Session() as session:
                location_id = _resolve_location(session, location_name)
                part = Part(**data, location_id=location_id)
                session.add(part)
                session.commit()
                part_id = part.id
            if image_url:
                download_image_async(part_id, image_url)
        except IntegrityError:
            if self._on_status:
                self._on_status("Failed to save — check for duplicate entries.", 5000)
            return

        self._on_part_saved()
        self.form.clear()

        # Restore sticky values
        if cfg.get("scan_sticky_supplier") and sticky_supplier_idx >= 0:
            self.form.supplier_combo.setCurrentIndex(sticky_supplier_idx)
        if cfg.get("scan_sticky_location") and sticky_location:
            self.form.loc_combo.setCurrentText(sticky_location)
        if cfg.get("scan_sticky_category") and sticky_category:
            self.form.cat_edit.setText(sticky_category)

        if self._on_status:
            self._on_status(f"Saved: {saved_mpn}", 4000)
        QTimer.singleShot(0, self.form.focus_first)
