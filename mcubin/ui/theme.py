"""
Minimal dark theme — Material Design inspired.
"""

STYLESHEET = """
QWidget {
    background-color: #1a1a1a;
    color: #e8e8e8;
    font-family: "Inter", "Segoe UI", "SF Pro Display", sans-serif;
    font-size: 15px;
}

QMainWindow {
    background-color: #121212;
}

/* ── Sidebar ─────────────────────────────────────────────── */
#sidebar {
    background-color: #0f0f0f;
    border-right: 1px solid #242424;
}

#appTitle {
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 24px 16px 16px 16px;
    letter-spacing: 2px;
    text-transform: uppercase;
}

/* Nav items */
QPushButton#navItem {
    background: transparent;
    border: none;
    border-radius: 0;
    color: #606060;
    font-size: 15px;
    font-weight: 500;
    padding: 10px 16px;
    text-align: left;
}

QPushButton#navItem:hover {
    background-color: #1c1c1c;
    color: #aaaaaa;
    border: none;
}

QPushButton#navItem[active=true] {
    background-color: #1e1e1e;
    color: #ffffff;
    font-weight: 600;
    border-left: 2px solid #5c85d6;
    padding-left: 14px;
}

/* ── Table ───────────────────────────────────────────────── */
QTableView {
    background-color: #1a1a1a;
    alternate-background-color: #1d1d1d;
    gridline-color: #242424;
    border: none;
    selection-background-color: #1e3a5f;
    selection-color: #ffffff;
}

QTableView::item {
    padding: 6px 12px;
    border: none;
}

QHeaderView::section {
    background-color: #121212;
    color: #666666;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #242424;
}

/* ── Inputs ──────────────────────────────────────────────── */
QLineEdit, QSpinBox, QComboBox {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 0;
    padding: 7px 10px;
    color: #e8e8e8;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #5c85d6;
    background-color: #1e1e1e;
}

QLineEdit#barcodeInput {
    font-size: 17px;
    padding: 10px 14px;
    border-color: #5c85d6;
}

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton {
    background-color: #2a2a2a;
    border: 1px solid #383838;
    border-radius: 0;
    padding: 7px 20px;
    color: #cccccc;
    font-weight: 500;
    font-size: 14px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

QPushButton:hover {
    background-color: #333333;
    border-color: #444444;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #222222;
}

QPushButton#primaryBtn {
    background-color: #2952a3;
    border: none;
    color: #ffffff;
    letter-spacing: 0.8px;
}

QPushButton#primaryBtn:hover {
    background-color: #3361b8;
}

QPushButton#primaryBtn:pressed {
    background-color: #1f3f80;
}

/* ── Search bar ──────────────────────────────────────────── */
#searchInput {
    background-color: #1e1e1e;
    border: 1px solid #2a2a2a;
    border-radius: 0;
    padding: 8px 12px;
    color: #e8e8e8;
    font-size: 15px;
}

#searchInput:focus {
    border-color: #5c85d6;
}

/* ── Status bar ──────────────────────────────────────────── */
QStatusBar {
    background-color: #0f0f0f;
    color: #aaaaaa;
    border-top: 1px solid #242424;
    font-size: 14px;
    letter-spacing: 0.3px;
    padding: 2px 8px;
}

/* ── Scrollbars ──────────────────────────────────────────── */
QScrollBar:vertical {
    background: #1a1a1a;
    width: 6px;
    border: none;
}

QScrollBar::handle:vertical {
    background: #333333;
    border-radius: 0;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #444444;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Screen typography ───────────────────────────────────── */
QLabel#screenTitle {
    color: #ffffff;
    font-size: 20px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

QLabel#screenSubtitle {
    color: #555555;
    font-size: 15px;
}

QLabel#sectionLabel {
    color: #666666;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}

QLabel#formLabel {
    color: #777777;
    font-size: 14px;
}

QLabel#feedbackError {
    color: #cf6679;
    font-size: 14px;
}

QLabel#feedbackSuccess {
    color: #4caf50;
    font-size: 14px;
}

/* ── Checkbox ────────────────────────────────────────────── */
QCheckBox {
    color: #cccccc;
    font-size: 15px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #444444;
    background-color: #1e1e1e;
}

QCheckBox::indicator:checked {
    background-color: #2952a3;
    border-color: #2952a3;
}

QCheckBox::indicator:hover {
    border-color: #5c85d6;
}

/* ── Divider ─────────────────────────────────────────────── */
QFrame#divider {
    background-color: #242424;
    max-height: 1px;
}

/* ── Detail panel ────────────────────────────────────────── */
#detailPanel {
    background-color: #161616;
    border-left: 1px solid #242424;
}

#detailEmpty {
    color: #3a3a3a;
    font-size: 15px;
}

#detailMpn {
    color: #ffffff;
    font-size: 17px;
    font-weight: 600;
    letter-spacing: 0.3px;
}

#detailMfr {
    color: #666666;
    font-size: 14px;
    margin-top: 2px;
}

#detailFieldLabel {
    color: #484848;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

#detailFieldValue {
    color: #bbbbbb;
    font-size: 15px;
}

#detailFieldValue a {
    color: #5c85d6;
}

#detailPbHeader {
    color: #484848;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

#detailPbValue {
    color: #bbbbbb;
    font-size: 14px;
}

#detailBtnBar {
    border-top: 1px solid #242424;
}

#detailImageContainer {
    background-color: #0f0f0f;
}

#detailNoImage {
    background-color: #0f0f0f;
}

#detailNoImageText {
    color: #333333;
    font-size: 14px;
}

#detailUploadBtn {
    color: #555555;
    font-size: 13px;
    background: transparent;
    border: 1px solid #2a2a2a;
    border-radius: 3px;
    padding: 4px 10px;
}

#detailUploadBtn:hover {
    color: #888888;
    border-color: #404040;
}

#detailImageOverlay {
    background-color: rgba(0, 0, 0, 210);
}

#detailImageActionBtn {
    color: #bbbbbb;
    font-size: 13px;
    background: transparent;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 4px 10px;
}

#detailImageActionBtn:hover {
    color: #ffffff;
    border-color: #888888;
}

#detailRemoveBtn {
    color: #cc5555;
    font-size: 13px;
    background: transparent;
    border: 1px solid #6a3030;
    border-radius: 3px;
    padding: 4px 10px;
}

#detailRemoveBtn:hover {
    color: #ff7777;
    border-color: #aa4444;
}

/* ── Splitter handle ─────────────────────────────────────── */
QSplitter::handle {
    background-color: #242424;
    width: 1px;
}

/* ── ComboBox dropdown ───────────────────────────────────── */
QAbstractItemView {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 0;
    outline: none;
}

QAbstractItemView::item {
    padding: 6px 10px;
}

QAbstractItemView::item:selected {
    background-color: #1e3a5f;
    color: #ffffff;
}

/* ── Dialogs ─────────────────────────────────────────────── */
QMessageBox {
    background-color: #1e1e1e;
}

QMessageBox QLabel {
    color: #cccccc;
    font-size: 15px;
    background-color: transparent;
}

QDialogButtonBox QPushButton {
    min-width: 72px;
}

QPushButton#dialogBtnConfirm {
    background-color: transparent;
    border: 1px solid #7a2a2a;
    color: #cf4444;
    font-weight: 600;
}

QPushButton#dialogBtnConfirm:hover {
    border-color: #a03333;
    color: #e05555;
}

QPushButton#dialogBtnCancel {
    background-color: transparent;
    border: 1px solid #383838;
    color: #666666;
}

QPushButton#dialogBtnCancel:hover {
    border-color: #555555;
    color: #999999;
}

/* ── Menu ────────────────────────────────────────────────── */
QMenu {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 0;
    padding: 4px 0;
}

QMenu::item {
    padding: 7px 20px;
    color: #cccccc;
}

QMenu::item:selected {
    background-color: #1e3a5f;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #2a2a2a;
    margin: 4px 0;
}
"""
