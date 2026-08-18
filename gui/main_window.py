from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QMainWindow, QLabel, QWidget, QVBoxLayout,
                               QHBoxLayout, QFileDialog, QPushButton, QGroupBox)
import gui.aaf_widget as aaf_widget
import gui.excel_widget as excel_widget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Pro Tools AAF to REAPER Session")
        self.setWindowIcon(QIcon("icons/main_icon.png"))
        self.setMinimumSize(800, 600)

        container = QWidget()
        self.setCentralWidget(container)

        self.main_layout = QVBoxLayout(container)

        aaf = aaf_widget.AAF_Widget()
        self.main_layout.addWidget(aaf)

        excel = excel_widget.ExcelWidget()
        self.main_layout.addWidget(excel)

        self.test = QLabel("Test Text")
        self.main_layout.addWidget(self.test)

        self.preferences_selection = QGroupBox("Preferences Selection")
        self.main_layout.addWidget(self.preferences_selection)
