from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
)
from sqlalchemy.exc import IntegrityError

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

        self.form = PartForm(scan_mode=True)
        root.addWidget(self.form)

        root.addStretch()

        from mcubin.ui.part_form import _divider
        root.addWidget(_divider())
        root.addSpacing(16)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Save Part")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

        self.feedback = QLabel("")
        self.feedback.setObjectName("feedbackError")
        self.feedback.setAlignment(Qt.AlignRight)
        root.addWidget(self.feedback)

    def reset(self):
        self.form.clear()
        self.feedback.setText("")
        QTimer.singleShot(0, self.form.focus_first)

    def _save(self):
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
            self._on_done(True)
        except IntegrityError:
            self.feedback.setText("Failed to save — check for duplicate entries.")
