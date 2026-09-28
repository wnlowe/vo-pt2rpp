import sys
from PySide6.QtWidgets import QApplication
import gui.main_window as mw

def main():
    app = QApplication()

    window = mw.MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
