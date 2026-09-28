from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QMainWindow, QComboBox, QWidget, QVBoxLayout,
                               QHBoxLayout, QFileDialog, QPushButton, QGroupBox)
import gui.aaf_widget as aaf_widget
import gui.excel_widget as excel_widget
import gui.reaper_widget as reaper_widget
import gui.preferences_widget as preferences_widget
from preferences_manager import Config
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

        self.preferences = preferences_widget.PreferencesWidget()
        self.main_layout.addWidget(self.preferences)

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
        self.preferences_layout = QVBoxLayout(self.preferences_selection)
        self.recording_method = QComboBox()
        self.recording_method.addItems(Config.get_value("record-modes"))
        self.preferences_layout.addWidget(self.recording_method)
        self.main_layout.addWidget(self.preferences_selection)

        self.preparation_stage = 0
        self.execute_button = QPushButton(f"Build Session ({self.preparation_stage}/3)")
        self.execute_button.setEnabled(False)
        self.execute_button.clicked.connect(self.build_session)
        self.main_layout.addWidget(self.execute_button)

    def _execute_ready(self):
        self.preparation_stage += 1
        if self.preparation_stage == 3:
            self.execute_button.setEnabled(True)
            self.execute_button.setText(f"Build Session ({self.preparation_stage}/3)")
        elif self.preparation_stage < 3:
            self.execute_button.setText(f"Build Session ({self.preparation_stage}/3)")

    def build_session(self):
        ...