from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QStatusBar, QMessageBox,
)
from sqlalchemy.exc import IntegrityError

from mcubin.database import Session
from mcubin.models import Part
from mcubin.ui.parts_table import PartsModel, make_parts_table
from mcubin.ui.add_part_dialog import AddPartDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mcubin")
        self.resize(1100, 680)
        self._build_ui()
        self._load_parts()
        # Focus barcode input on launch
        QTimer.singleShot(0, self.barcode_input.setFocus)

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_sidebar())
        root.addWidget(self._make_content(), stretch=1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _make_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(180)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("mcubin")
        title.setObjectName("appTitle")
        layout.addWidget(title)
        layout.addStretch()
        return sidebar

    def _make_content(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)

        # Top bar
        top = QHBoxLayout()
        top.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Search parts…")
        self.search_input.textChanged.connect(self._on_search)
        top.addWidget(self.search_input, stretch=1)

        add_btn = QPushButton("+ Add Part")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._open_add_dialog)
        top.addWidget(add_btn)

        layout.addLayout(top)

        # Barcode scanner strip
        scan_row = QHBoxLayout()
        scan_label = QLabel("Barcode:")
        scan_label.setStyleSheet("color: #888888; font-size: 12px;")
        scan_row.addWidget(scan_label)

        self.barcode_input = QLineEdit()
        self.barcode_input.setObjectName("barcodeInput")
        self.barcode_input.setPlaceholderText("Scan a barcode to add or find a part…")
        self.barcode_input.returnPressed.connect(self._on_barcode_scanned)
        scan_row.addWidget(self.barcode_input, stretch=1)

        layout.addLayout(scan_row)

        # Parts table
        self.model = PartsModel()
        self.table = make_parts_table()
        self.table.setModel(self.model)
        layout.addWidget(self.table)

        return content

    # ── Data ──────────────────────────────────────────────────────────────

    def _load_parts(self, search: str = ""):
        with Session() as session:
            q = session.query(Part)
            if search:
                like = f"%{search}%"
                q = q.filter(
                    Part.mpn.ilike(like) |
                    Part.description.ilike(like) |
                    Part.manufacturer.ilike(like) |
                    Part.barcode.ilike(like) |
                    Part.location.ilike(like) |
                    Part.category.ilike(like)
                )
            parts = q.order_by(Part.updated_at.desc()).all()
            session.expunge_all()
        self.model.refresh(parts)
        count = len(parts)
        self.status.showMessage(f"{count} part{'s' if count != 1 else ''}")

    # ── Handlers ──────────────────────────────────────────────────────────

    def _on_search(self, text: str):
        self._load_parts(text.strip())

    def _on_barcode_scanned(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return

        # Check if part exists
        with Session() as session:
            part = session.query(Part).filter_by(barcode=barcode).first()

        if part:
            # Highlight it in the table
            self._highlight_barcode(barcode)
            self.status.showMessage(f"Found: {part.mpn or barcode}", 3000)
        else:
            # Open add dialog pre-filled with barcode
            self._open_add_dialog(barcode=barcode)

        self.barcode_input.clear()

    def _highlight_barcode(self, barcode: str):
        self.search_input.setText(barcode)

    def _open_add_dialog(self, checked=False, barcode: str = ""):
        dlg = AddPartDialog(self, barcode=barcode)
        if dlg.exec():
            data = dlg.get_part_data()
            try:
                with Session() as session:
                    part = Part(**data)
                    session.add(part)
                    session.commit()
                self._load_parts(self.search_input.text())
                self.status.showMessage(f"Added {data.get('mpn') or data.get('barcode') or 'part'}", 3000)
            except IntegrityError:
                QMessageBox.warning(self, "Duplicate", "A part with that barcode already exists.")
