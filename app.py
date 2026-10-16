#!/usr/bin/env python3
import sys

def main():
    """檢查 PySide6 並啟動應用程式"""
    try:
        import PySide6
    except ImportError:
        print("錯誤: 找不到 PySide6 GUI 界面庫。")
        print("請執行 `pip install PySide6 openpyxl`。")
        sys.exit(1)

    print("檢測到 PySide6 界面庫，啟動員工選擇介面...")
    from employee_cards import main as run_employee_cards
    run_employee_cards()

if __name__ == "__main__":
    main()
