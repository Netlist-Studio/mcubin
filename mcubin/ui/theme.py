"""
Minimal dark theme — Bomist-inspired.
"""

STYLESHEET = """
QWidget {
    background-color: #1a1a1a;
    color: #e8e8e8;
    font-family: "Inter", "Segoe UI", "SF Pro Display", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #141414;
}

/* ── Sidebar ─────────────────────────────────────────────── */
#sidebar {
    background-color: #111111;
    border-right: 1px solid #2a2a2a;
}

#appTitle {
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    padding: 24px 16px 16px 16px;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* Nav items — QPushButton used as sidebar tabs */
QPushButton#navItem {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: #666666;
    font-size: 13px;
    font-weight: 500;
    padding: 9px 14px;
    text-align: left;
}

QPushButton#navItem:hover {
    background-color: #1e1e1e;
    color: #cccccc;
    border: none;
}

QPushButton#navItem[active=true] {
    background-color: #1e1e1e;
    color: #ffffff;
    font-weight: 600;
}

/* ── Table ───────────────────────────────────────────────── */
QTableView {
    background-color: #1a1a1a;
    alternate-background-color: #1e1e1e;
    gridline-color: #262626;
    border: none;
    selection-background-color: #2d4f7c;
    selection-color: #ffffff;
}

QTableView::item {
    padding: 6px 12px;
    border: none;
}

QHeaderView::section {
    background-color: #141414;
    color: #888888;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #2a2a2a;
}

/* ── Inputs ──────────────────────────────────────────────── */
QLineEdit, QSpinBox, QComboBox {
    background-color: #242424;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 7px 10px;
    color: #e8e8e8;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #4d7fbc;
    background-color: #282828;
}

QLineEdit#barcodeInput {
    font-size: 15px;
    padding: 10px 14px;
    border-color: #4d7fbc;
}

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton {
    background-color: #2a2a2a;
    border: 1px solid #383838;
    border-radius: 6px;
    padding: 7px 16px;
    color: #e8e8e8;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #333333;
    border-color: #484848;
}

QPushButton:pressed {
    background-color: #222222;
}

QPushButton#primaryBtn {
    background-color: #2d5fa8;
    border-color: #3a6bbf;
    color: #ffffff;
}

QPushButton#primaryBtn:hover {
    background-color: #3568b8;
}

/* ── Search bar ──────────────────────────────────────────── */
#searchInput {
    background-color: #1e1e1e;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e8e8e8;
    font-size: 13px;
}

#searchInput:focus {
    border-color: #4d7fbc;
}

/* ── Status bar ──────────────────────────────────────────── */
QStatusBar {
    background-color: #111111;
    color: #666666;
    border-top: 1px solid #2a2a2a;
    font-size: 11px;
}

/* ── Scrollbars ──────────────────────────────────────────── */
QScrollBar:vertical {
    background: #1a1a1a;
    width: 8px;
    border: none;
}

QScrollBar::handle:vertical {
    background: #383838;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #484848;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Screen typography ───────────────────────────────────── */
QLabel#screenTitle {
    color: #ffffff;
    font-size: 20px;
    font-weight: 600;
}

QLabel#screenSubtitle {
    color: #666666;
    font-size: 13px;
}

QLabel#sectionLabel {
    color: #888888;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

QLabel#formLabel {
    color: #888888;
    font-size: 12px;
}

QLabel#feedbackError {
    color: #e05c5c;
    font-size: 12px;
}

/* ── Divider ─────────────────────────────────────────────── */
QFrame#divider {
    background-color: #2a2a2a;
    max-height: 1px;
}

/* ── ComboBox dropdown ───────────────────────────────────── */
QAbstractItemView {
    background-color: #242424;
    border: 1px solid #333333;
    outline: none;
}

QAbstractItemView::item {
    padding: 6px 10px;
}

QAbstractItemView::item:selected {
    background-color: #2d4f7c;
    color: #ffffff;
}
"""
