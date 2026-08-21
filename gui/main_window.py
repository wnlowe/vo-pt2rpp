from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QMainWindow, QLabel, QWidget, QVBoxLayout,
                               QHBoxLayout, QFileDialog, QPushButton, QGroupBox)
import gui.aaf_widget as aaf_widget
import gui.excel_widget as excel_widget
import gui.reaper_widget as reaper_widget
import excel_parse as excel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Pro Tools AAF to REAPER Session")
        self.setWindowIcon(QIcon("icons/main_icon.png"))
        self.setMinimumSize(800, 600)

        container = QWidget()
        self.setCentralWidget(container)

        self.main_layout = QVBoxLayout(container)

        self.aaf = aaf_widget.AAF_Widget()
        self.main_layout.addWidget(self.aaf)
        self.aaf.aaf_ready.connect(self._execute_ready)

        self.excel_w = excel_widget.ExcelWidget()
        self.main_layout.addWidget(self.excel_w)
        self.excel_w.excel_ready.connect(self._execute_ready)

        self.reaper = reaper_widget.ReaperWidget()
        self.main_layout.addWidget(self.reaper)
        self.reaper.reaper_ready.connect(self._execute_ready)

        self.preferences_selection = QGroupBox("Preferences Selection")
        self.main_layout.addWidget(self.preferences_selection)

        self.execute_button = QPushButton("Build Session (0/3)")
        self.preparation_stage = 0
        self.execute_button.setEnabled(False)
        self.execute_button.clicked.connect(self.build_session)
        self.main_layout.addWidget(self.execute_button)

    def _execute_ready(self):
        self.preparation_stage += 1
        if self.preparation_stage == 3:
            self.execute_button.setEnabled(True)
        else:
            self.execute_button.setText(f"Build Session ({self.preparation_stage}/3)")

    def build_session(self):
        ...