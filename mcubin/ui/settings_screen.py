from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox,
    QApplication, QLineEdit,
)

import mcubin.config as config
from mcubin.ui.dialogs import fix_combo


THEMES = [
    "dark_amber.xml",
    "dark_blue.xml",
    "dark_cyan.xml",
    "dark_lightgreen.xml",
    "dark_pink.xml",
    "dark_purple.xml",
    "dark_red.xml",
    "dark_teal.xml",
    "dark_yellow.xml",
    "light_amber.xml",
    "light_blue.xml",
    "light_blue_500.xml",
    "light_cyan.xml",
    "light_cyan_500.xml",
    "light_lightgreen.xml",
    "light_lightgreen_500.xml",
    "light_orange.xml",
    "light_pink.xml",
    "light_pink_500.xml",
    "light_purple.xml",
    "light_purple_500.xml",
    "light_red.xml",
    "light_red_500.xml",
    "light_teal.xml",
    "light_teal_500.xml",
    "light_yellow.xml",
]


class SettingsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        title = QLabel("Settings")
        title.setObjectName("screenTitle")
        root.addWidget(title)
        root.addSpacing(4)

        subtitle = QLabel("Configure app behaviour.")
        subtitle.setObjectName("screenSubtitle")
        root.addWidget(subtitle)
        root.addSpacing(32)

        # ── Appearance ─────────────────────────────────────────
        appearance_label = QLabel("APPEARANCE")
        appearance_label.setObjectName("sectionLabel")
        root.addWidget(appearance_label)
        root.addSpacing(16)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(12)
        theme_lbl = QLabel("Theme")
        theme_lbl.setObjectName("formLabel")
        theme_row.addWidget(theme_lbl)
        self._theme_combo = QComboBox()
        fix_combo(self._theme_combo)
        self._theme_combo.addItems(THEMES)
        current_theme = config.get("theme") or "dark_blue.xml"
        if current_theme in THEMES:
            self._theme_combo.setCurrentIndex(THEMES.index(current_theme))
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self._theme_combo)
        theme_row.addStretch()
        root.addLayout(theme_row)
        root.addSpacing(24)

        # ── Scan mode ──────────────────────────────────────────
        scan_label = QLabel("SCAN MODE")
        scan_label.setObjectName("sectionLabel")
        root.addWidget(scan_label)
        root.addSpacing(16)

        self._checks = [
            ("scan_auto_lookup",     "Auto-lookup after quantity scan"),
            ("scan_accept_first",    "Accept first result automatically"),
            ("scan_sticky_supplier", "Remember supplier between scans"),
            ("scan_sticky_location", "Remember location between scans"),
            ("scan_sticky_category", "Remember category between scans"),
        ]

        cfg = config.load()
        for key, label in self._checks:
            cb = QCheckBox(label)
            cb.setChecked(bool(cfg.get(key, config.DEFAULTS[key])))
            cb.stateChanged.connect(lambda state, k=key: config.set(k, bool(state)))
            root.addWidget(cb)
            root.addSpacing(10)

        root.addSpacing(24)

        # ── Label printing ─────────────────────────────────────
        label_label = QLabel("LABEL PRINTING")
        label_label.setObjectName("sectionLabel")
        root.addWidget(label_label)
        root.addSpacing(16)

        printer_row = QHBoxLayout()
        printer_row.setSpacing(12)
        printer_lbl = QLabel("Printer device")
        printer_lbl.setObjectName("formLabel")
        printer_row.addWidget(printer_lbl)
        self._printer_input = QLineEdit()
        self._printer_input.setPlaceholderText("/dev/usb/lp0")
        self._printer_input.setText(config.get("label_printer_device") or "/dev/usb/lp0")
        self._printer_input.editingFinished.connect(self._on_printer_changed)
        printer_row.addWidget(self._printer_input)
        printer_row.addStretch()
        root.addLayout(printer_row)

        root.addStretch()

    def _on_printer_changed(self) -> None:
        config.set("label_printer_device", self._printer_input.text().strip())

    def _on_theme_changed(self, theme: str) -> None:
        from mcubin.app import apply_theme
        app = QApplication.instance()
        apply_theme(app, theme)
        config.set("theme", theme)
