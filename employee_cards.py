import json
import os
import sys

# 避免載入 GTK3 平台主題（新版 GNOME 缺少 xsettings 'antialiasing' 設定鍵會導致崩潰）
os.environ.setdefault("QT_QPA_PLATFORMTHEME", "generic")

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame, QGridLayout
)
from PySide6.QtCore import Qt

CARDS_PER_ROW = 3
APP_DIR_NAME = "HRTool"
EMPLOYEE_FILENAME = "employees.json"


def get_data_dir():
    """Windows: %LOCALAPPDATA%\\HRTool；其他系統: ~/.local/share/HRTool"""
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, APP_DIR_NAME)


def get_employee_file():
    return os.path.join(get_data_dir(), EMPLOYEE_FILENAME)


def load_employees(path=None):
    path = path or get_employee_file()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    return [n for n in data if isinstance(n, str)] if isinstance(data, list) else []


def save_employees(employees, path=None):
    path = path or get_employee_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(employees, f, ensure_ascii=False, indent=2)


class EmployeeCardsWindow(QMainWindow):
    """員工卡片畫面：頂端輸入框與新增按鈕，下方每列三張員工卡片。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("員工列表")
        self.resize(700, 500)
        self.employees = []

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        top = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("請輸入員工名稱")
        self.name_input.returnPressed.connect(self.add_employee)
        self.add_button = QPushButton("增加")
        self.add_button.clicked.connect(self.add_employee)
        top.addWidget(self.name_input)
        top.addWidget(self.add_button)
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setAlignment(Qt.AlignTop)
        for col in range(CARDS_PER_ROW):
            self.grid.setColumnStretch(col, 1)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        self.load_employees()

    def load_employees(self):
        """從 employees.json 載入員工名單並顯示成卡片。"""
        for name in load_employees():
            self._append_card(name)

    def add_employee(self):
        name = self.name_input.text().strip()
        if not name:
            return
        self._append_card(name)
        try:
            save_employees(self.employees)
        except OSError as e:
            print(f"無法儲存員工名單: {e}", file=sys.stderr)
        self.name_input.clear()
        self.name_input.setFocus()

    def _append_card(self, name):
        index = len(self.employees)
        self.employees.append(name)
        self.grid.addWidget(self._make_card(name),
                            index // CARDS_PER_ROW, index % CARDS_PER_ROW)

    @staticmethod
    def _make_card(name):
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setMinimumHeight(80)
        card.setStyleSheet(
            "QFrame { background: #FFFFFF; border: 1px solid #CCCCCC; border-radius: 8px; }"
        )
        card_layout = QVBoxLayout(card)
        label = QLabel(name)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("border: none; font-size: 16px;")
        card_layout.addWidget(label)
        return card


def main():
    app = QApplication(sys.argv)
    window = EmployeeCardsWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
