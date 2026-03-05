from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QStatusBar, QStackedWidget,
    QMenu, QSplitter,
)
from sqlalchemy.orm import joinedload

from mcubin.database import Session, IMAGES_DIR
from mcubin.models import Location, Part
from mcubin.ui.parts_table import PartsModel, make_parts_table
from mcubin.ui.add_part_screen import AddPartScreen, _resolve_location
from mcubin.ui.part_form import download_image_async
from mcubin.ui.edit_part_dialog import EditPartDialog
from mcubin.ui.locations_screen import LocationsScreen
from mcubin.ui.suppliers_screen import SuppliersScreen
from mcubin.ui.part_detail_panel import PartDetailPanel
from mcubin.ui.dialogs import confirm

NAV = [
    ("parts",     "Parts"),
    ("add_part",  "Add Part"),
    ("locations", "Locations"),
    ("suppliers", "Suppliers"),
    ("settings",  "Settings"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mcubin")
        self.resize(1100, 680)
        self._build_ui()
        self._navigate("parts")
        self._load_parts()

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._nav_buttons = {}
        root.addWidget(self._make_sidebar())

        self.stack = QStackedWidget()
        self._pages = {
            "parts":     self._make_parts_page(),
            "add_part":  AddPartScreen(on_done=self._on_add_done),
            "locations": LocationsScreen(),
            "suppliers": SuppliersScreen(),
            "settings":  self._make_placeholder("Settings", "App settings coming soon."),
        }
        for page in self._pages.values():
            self.stack.addWidget(page)
        root.addWidget(self.stack, stretch=1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _make_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(180)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 0, 8, 16)
        layout.setSpacing(2)

        title = QLabel("mcubin")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        for key, label in NAV:
            btn = QPushButton(label)
            btn.setObjectName("navItem")
            btn.clicked.connect(lambda _, k=key: self._navigate(k))
            layout.addWidget(btn)
            self._nav_buttons[key] = btn

        layout.addStretch()
        return sidebar

    def _make_parts_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Search parts…")
        self.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_input)

        self.model = PartsModel()
        self.table = make_parts_table()
        self.table.setModel(self.model)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.selectionModel().currentChanged.connect(self._on_current_changed)

        self.detail_panel = PartDetailPanel(on_edit=self._edit_part)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([640, 280])
        layout.addWidget(splitter)

        return page

    def _make_placeholder(self, title: str, subtitle: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(8)

        t = QLabel(title)
        t.setObjectName("screenTitle")
        layout.addWidget(t)

        s = QLabel(subtitle)
        s.setObjectName("screenSubtitle")
        layout.addWidget(s)

        layout.addStretch()
        return page

    # ── Navigation ────────────────────────────────────────────────────────

    def _navigate(self, key: str):
        if key == "add_part":
            self._pages["add_part"].reset()
            self.status.showMessage("Scan a barcode or enter an MPN to add a part")
        else:
            self.status.showMessage("")

        self.stack.setCurrentWidget(self._pages[key])

        for k, btn in self._nav_buttons.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_add_done(self, saved: bool):
        self._navigate("parts")
        if saved:
            self._load_parts(self.search_input.text())
            self.status.showMessage("Part added", 3000)

    def _on_current_changed(self, current, _previous):
        if not current.isValid():
            self.detail_panel.show_empty()
        else:
            part_id = self.model.part_at(current.row()).id
            with Session() as session:
                part = session.get(Part, part_id, options=[joinedload(Part.location_obj), joinedload(Part.supplier_obj)])
            self.detail_panel.load(part)

    # ── Edit / Delete ─────────────────────────────────────────────────────

    def _selected_parts(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.model.part_at(r) for r in rows]

    def _selected_part(self):
        parts = self._selected_parts()
        return parts[0] if len(parts) == 1 else None

    def _on_row_double_clicked(self, index):
        part = self.model.part_at(index.row())
        self._edit_part(part)

    def _on_context_menu(self, pos):
        parts = self._selected_parts()
        if not parts:
            return
        menu = QMenu(self)
        if len(parts) == 1:
            menu.addAction("Edit", lambda: self._edit_part(parts[0]))
            menu.addSeparator()
        menu.addAction(
            f"Delete {len(parts)} part{'s' if len(parts) > 1 else ''}",
            lambda: self._delete_parts(parts),
        )
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            parts = self._selected_parts()
            if parts and self.stack.currentWidget() == self._pages["parts"]:
                self._delete_parts(parts)
        super().keyPressEvent(event)

    def _edit_part(self, part: Part):
        dlg = EditPartDialog(part, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            location_name = data.pop("location_name")
            image_url = data.pop("image_url", None)
            with Session() as session:
                location_id = _resolve_location(session, location_name)
                db_part = session.get(Part, part.id)
                for key, value in data.items():
                    setattr(db_part, key, value)
                db_part.location_id = location_id
                session.commit()
            if image_url:
                download_image_async(part.id, image_url)
            self._load_parts(self.search_input.text())
            self.status.showMessage("Part updated", 3000)


    def _delete_parts(self, parts: list):
        count = len(parts)
        if count == 1:
            label = parts[0].mpn or parts[0].supplier_pn or f"Part #{parts[0].id}"
            msg = f"Delete {label}?"
        else:
            msg = f"Delete {count} parts?"
        if confirm(self, msg):
            ids = [p.id for p in parts]
            image_paths = [p.image_path for p in parts if p.image_path]
            with Session() as session:
                session.query(Part).filter(Part.id.in_(ids)).delete()
                session.commit()
            for img in image_paths:
                f = IMAGES_DIR / img
                if f.exists():
                    f.unlink()
            self._load_parts(self.search_input.text())
            self.status.showMessage(
                f"Deleted {count} part{'s' if count > 1 else ''}", 3000
            )

    # ── Data ──────────────────────────────────────────────────────────────

    def _load_parts(self, search: str = ""):
        with Session() as session:
            q = session.query(Part).options(
                joinedload(Part.location_obj),
                joinedload(Part.supplier_obj),
            )
            if search:
                like = f"%{search}%"
                q = q.filter(
                    Part.mpn.ilike(like) |
                    Part.description.ilike(like) |
                    Part.manufacturer.ilike(like) |
                    Part.location_obj.has(Location.name.ilike(like)) |
                    Part.category.ilike(like)
                )
            parts = q.order_by(Part.updated_at.desc()).all()
            session.expunge_all()
        self.model.refresh(parts)
        self.detail_panel.show_empty()
        count = len(parts)
        self.status.showMessage(f"{count} part{'s' if count != 1 else ''}")

    def _on_search(self, text: str):
        self._load_parts(text.strip())
