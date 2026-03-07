"""
App-specific style overlay applied on top of qt-material.
Only things qt-material has no concept of belong here.
"""

CUSTOM_STYLESHEET = """
/* ── Nav items ───────────────────────────────────────────── */
QPushButton#navItem {
    background: transparent;
    border: none;
    border-radius: 0;
    font-weight: 500;
    padding: 10px 16px;
    text-align: left;
}

QPushButton#navItem:hover {
    border: none;
}

QPushButton#navItem[active=true] {
    font-weight: 600;
    border-left: 3px solid palette(highlight);
    padding-left: 13px;
}

/* ── Feedback labels ─────────────────────────────────────── */
QLabel#feedbackError {
    color: #cf6679;
}

QLabel#feedbackSuccess {
    color: #4caf50;
}

/* ── Detail panel image area ─────────────────────────────── */
#detailImageContainer {
    background-color: rgba(0, 0, 0, 0.3);
}

#detailNoImage {
    background-color: rgba(0, 0, 0, 0.3);
}

#detailImageOverlay {
    background-color: rgba(0, 0, 0, 0.82);
}

#detailUploadBtn {
    background: transparent;
    border-radius: 3px;
    padding: 4px 10px;
}

#detailImageActionBtn {
    background: transparent;
    border-radius: 3px;
    padding: 4px 10px;
}

/* ── Destructive actions ─────────────────────────────────── */
#detailRemoveBtn {
    color: #cf6679;
    background: transparent;
    border: 1px solid rgba(207, 102, 121, 0.4);
    border-radius: 3px;
    padding: 4px 10px;
}

#detailRemoveBtn:hover {
    color: #ff8898;
    border-color: rgba(207, 102, 121, 0.8);
}

QPushButton#dialogBtnConfirm {
    background-color: transparent;
    color: #cf6679;
    font-weight: 600;
}

QPushButton#dialogBtnCancel {
    background-color: transparent;
}

/* ── Label designer ───────────────────────────────────── */
QGraphicsView {
    border: none;
    border-radius: 4px;
}

/* ── ComboBox dropdown: remove icon column gap ────────── */
QComboBox QAbstractItemView::item {
    padding-left: 8px;
    padding-right: 8px;
}
"""
