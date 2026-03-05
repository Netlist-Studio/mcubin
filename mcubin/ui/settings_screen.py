from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QCheckBox,
)

import mcubin.config as config


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

        root.addStretch()
