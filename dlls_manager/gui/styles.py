"""Steam-inspired dark theme QSS for DLSS Manager."""

DARK_THEME = """
QWidget {
    background-color: #1b2838;
    color: #c7d5e0;
    font-family: "Segoe UI", "DejaVu Sans", sans-serif;
    font-size: 14px;
}

QMainWindow {
    background-color: #171a21;
}

/* Sidebar */
QListWidget#sidebar {
    background-color: #171a21;
    border: none;
    border-right: 1px solid #2a475e;
    outline: none;
    font-size: 15px;
    padding: 8px 0px;
}
QListWidget#sidebar::item {
    padding: 12px 16px;
    border-left: 3px solid transparent;
}
QListWidget#sidebar::item:selected {
    background-color: #1b2838;
    border-left: 3px solid #66c0f4;
    color: #66c0f4;
}
QListWidget#sidebar::item:hover {
    background-color: #2a475e;
}

/* Pages */
QStackedWidget {
    background-color: #1b2838;
}

/* Surfaces / Cards */
QFrame#surface {
    background-color: #1b2838;
    border: 1px solid #2a475e;
    border-radius: 6px;
}

QLabel#page_title {
    font-size: 20px;
    font-weight: bold;
    color: #ffffff;
}
QLabel#section_title {
    font-size: 16px;
    font-weight: bold;
    color: #66c0f4;
}
QLabel#subtle {
    color: #8f98a0;
    font-size: 13px;
}

/* Buttons */
QPushButton {
    background-color: #2a475e;
    color: #c7d5e0;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 14px;
}
QPushButton:hover {
    background-color: #3a5a7e;
}
QPushButton:pressed {
    background-color: #1b2838;
}
QPushButton:disabled {
    background-color: #2a2a2a;
    color: #555;
}
QPushButton#launch_button, QPushButton#primary_button {
    background-color: #5c7e10;
    color: #ffffff;
}
QPushButton#launch_button:hover, QPushButton#primary_button:hover {
    background-color: #6e9514;
}
QPushButton#danger_button {
    background-color: #8b3a3a;
    color: #ffffff;
}
QPushButton#danger_button:hover {
    background-color: #a04545;
}

/* Inputs */
QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: #0e1a26;
    border: 1px solid #2a475e;
    border-radius: 4px;
    padding: 6px 8px;
    color: #c7d5e0;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #66c0f4;
}

/* ComboBox */
QComboBox {
    background-color: #0e1a26;
    border: 1px solid #2a475e;
    border-radius: 4px;
    padding: 6px 8px;
    color: #c7d5e0;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #1b2838;
    border: 1px solid #2a475e;
    selection-background-color: #2a475e;
    color: #c7d5e0;
}

/* Table */
QTableWidget {
    background-color: #1b2838;
    border: 1px solid #2a475e;
    gridline-color: #2a475e;
    color: #c7d5e0;
}
QTableWidget::item {
    padding: 6px;
}
QTableWidget::item:selected {
    background-color: #2a475e;
}
QHeaderView::section {
    background-color: #171a21;
    color: #66c0f4;
    border: none;
    border-bottom: 1px solid #2a475e;
    padding: 6px;
    font-weight: bold;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #c7d5e0;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #2a475e;
    border-radius: 3px;
    background-color: #0e1a26;
}
QCheckBox::indicator:checked {
    background-color: #66c0f4;
    border: 1px solid #66c0f4;
}

/* Scrollbar */
QScrollBar:vertical {
    background: #171a21;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #2a475e;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #3a5a7e;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Status badges */
QLabel#badge_ok {
    background-color: #5c7e10;
    color: #ffffff;
    border-radius: 3px;
    padding: 2px 8px;
}
QLabel#badge_warn {
    background-color: #8a6914;
    color: #ffffff;
    border-radius: 3px;
    padding: 2px 8px;
}
QLabel#badge_blocked {
    background-color: #8b3a3a;
    color: #ffffff;
    border-radius: 3px;
    padding: 2px 8px;
}

/* Command preview */
QPlainTextEdit#command_preview {
    background-color: #0e1a26;
    color: #66c0f4;
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 13px;
    border: 1px solid #2a475e;
    border-radius: 4px;
}

/* List */
QListWidget#install_list {
    background-color: #1b2838;
    border: 1px solid #2a475e;
    border-radius: 4px;
    outline: none;
}
QListWidget#install_list::item {
    padding: 10px 12px;
    border-bottom: 1px solid #2a475e;
}
QListWidget#install_list::item:selected {
    background-color: #2a475e;
    color: #66c0f4;
}
QListWidget#install_list::item:hover {
    background-color: #243648;
}
"""