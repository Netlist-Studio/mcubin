from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QStatusBar, QStackedWidget,
)

from mcubin.database import Session
from mcubin.models import Part
from mcubin.ui.parts_table import PartsModel, make_parts_table
from mcubin.ui.add_part_screen import AddPartScreen

NAV = [
    ("parts",     "Parts"),
    ("add_part",  "Add Part"),
    ("locations", "Locations"),
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
            "locations": self._make_placeholder("Locations", "Bin and shelf management coming soon."),
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
        layout.addWidget(self.table)

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
                    Part.location.ilike(like) |
                    Part.category.ilike(like)
                )
            parts = q.order_by(Part.updated_at.desc()).all()
            session.expunge_all()
        self.model.refresh(parts)
        count = len(parts)
        self.status.showMessage(f"{count} part{'s' if count != 1 else ''}")

    def _on_search(self, text: str):
        self._load_parts(text.strip())
