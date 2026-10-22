import json
import os
import sys

# 避免載入 GTK3 平台主題（新版 GNOME 缺少 xsettings 'antialiasing' 設定鍵會導致崩潰）
os.environ.setdefault("QT_QPA_PLATFORMTHEME", "generic")

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QGridLayout, QComboBox,
    QToolButton, QMessageBox,
)
from PySide6.QtCore import Qt

CARDS_PER_ROW = 3
APP_DIR_NAME = "HRTool"
EMPLOYEE_FILENAME = "employees.json"
START_KEY = "workStart"
END_KEY = "workOff"
WORK_SCHEDULES = ("0800 - 1700", "0830 - 1730", "0900 - 1800")


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
        return {}
    return data if isinstance(data, dict) else {}


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
        self.employees = {}
        self.card_widgets = {}
        self.clock_in_window = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        top = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("請輸入員工名稱")
        self.name_input.setMaximumWidth(200)
        self.name_input.returnPressed.connect(self.add_employee)
        self.schedule_combo = QComboBox()
        self.schedule_combo.addItems(WORK_SCHEDULES)
        self.add_button = QPushButton("增加")
        self.add_button.clicked.connect(self.add_employee)
        top.addWidget(self.name_input)
        top.addWidget(QLabel("上下班時段"))
        top.addWidget(self.schedule_combo)
        top.addWidget(self.add_button)
        top.addStretch(1)
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
        for name, times in load_employees().items():
            self._append_card(name, times)

    def add_employee(self):
        name = self.name_input.text().strip()
        if not name or name in self.employees:
            return
        start_time, end_time = self.schedule_combo.currentText().split(" - ", 1)
        self._append_card(name, {
            START_KEY: start_time,
            END_KEY: end_time,
        })
        try:
            save_employees(self.employees)
        except OSError as e:
            print(f"無法儲存員工名單: {e}", file=sys.stderr)
        self.name_input.clear()
        self.name_input.setFocus()

    def _append_card(self, name, times):
        index = len(self.employees)
        self.employees[name] = times
        card_container = QWidget()
        card_container.setMinimumHeight(88)
        card_layout = QGridLayout(card_container)
        card_layout.setContentsMargins(0, 0, 0, 0)

        card = self._make_card(name)
        card.clicked.connect(
            lambda checked=False, employee_name=name: self.open_clock_in(employee_name)
        )
        card_layout.addWidget(card, 0, 0)

        delete_button = QToolButton(card_container)
        delete_button.setText("×")
        delete_button.setToolTip(f"刪除{name}")
        delete_button.setFixedSize(24, 24)
        delete_button.setStyleSheet(
            "QToolButton { background: #FDECEC; color: #C62828; border: 1px solid #F2B8B5; "
            "border-radius: 12px; font-size: 18px; font-weight: bold; }"
            "QToolButton:hover { background: #F8C9C6; }"
        )
        delete_button.clicked.connect(
            lambda checked=False, employee_name=name: self.confirm_remove_employee(employee_name)
        )
        card_layout.addWidget(
            delete_button, 0, 0, alignment=Qt.AlignTop | Qt.AlignRight
        )

        self.card_widgets[name] = card_container
        self.grid.addWidget(
            card_container, index // CARDS_PER_ROW, index % CARDS_PER_ROW
        )

    @staticmethod
    def _make_card(name):
        card = QPushButton(name)
        card.setMinimumHeight(88)
        card.setStyleSheet(
            "QPushButton { background: #FFFFFF; border: 1px solid #CCCCCC; "
            "border-radius: 8px; font-size: 16px; }"
            "QPushButton:hover { background: #F0F7FF; border-color: #4A90E2; }"
        )
        return card

    def confirm_remove_employee(self, employee_name):
        reply = QMessageBox.question(
            self,
            "確認刪除員工",
            f"確定要刪除員工「{employee_name}」嗎？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.remove_employee(employee_name)

    def remove_employee(self, employee_name):
        if employee_name not in self.employees:
            return

        updated_employees = {
            name: times
            for name, times in self.employees.items()
            if name != employee_name
        }
        try:
            save_employees(updated_employees)
        except OSError as e:
            QMessageBox.critical(self, "刪除失敗", f"無法儲存員工名單：\n{e}")
            return

        self.employees = updated_employees
        card_widget = self.card_widgets.pop(employee_name)
        self.grid.removeWidget(card_widget)
        card_widget.deleteLater()
        for index, widget in enumerate(self.card_widgets.values()):
            self.grid.addWidget(
                widget, index // CARDS_PER_ROW, index % CARDS_PER_ROW
            )

    def open_clock_in(self, employee_name):
        from clock_in_app import ClockInApp

        times = self.employees[employee_name]
        self.clock_in_window = ClockInApp(
            employee_name,
            start_time=times.get(START_KEY, ""),
            end_time=times.get(END_KEY, ""),
            on_close=self.return_to_employee_cards,
        )
        self.clock_in_window.setAttribute(Qt.WA_DeleteOnClose)
        self.hide()
        self.clock_in_window.show()

    def return_to_employee_cards(self):
        self.clock_in_window = None
        self.show()


def main():
    app = QApplication(sys.argv)
    window = EmployeeCardsWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
