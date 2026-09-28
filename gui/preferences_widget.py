from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QComboBox,
                               QFileDialog, QPushButton, QMessageBox)
from PySide6.QtWidgets import QSizePolicy
from preferences_manager import UserConfig
import os

class PreferencesWidget(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Preferences")
        self.layout = QVBoxLayout(self)
        self.loaded = UserConfig.user_config_exists()

        self.select_config_layout = QHBoxLayout()

        self.user_edit_button = QPushButton("Edit")
        self.user_edit_button.clicked.connect(self.edit_user_config)
        self.select_config_layout.addWidget(self.user_edit_button)

        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(QIcon("gui/icons/refresh-ccw.png"))
        self.refresh_button.setToolTip("Refresh")
        self.refresh_button.setFixedWidth(32)
        self.refresh_button.clicked.connect(self.refresh)
        self.select_config_layout.addWidget(self.refresh_button)

        self.presets = QComboBox()
        self.load_presets()
        self.presets.setDisabled(not self.loaded)
        self.select_config_layout.addWidget(self.presets)

        self.layout.addLayout(self.select_config_layout)

    def edit_user_config(self):
        os.startfile(str(UserConfig.config_file))

    def refresh(self):
        UserConfig.get_user_config()
        self.load_presets()

    def load_presets(self):
        self.presets.clear()
        if self.loaded:
            if len(UserConfig.content.keys()) < 1:
                self.loaded = False
                self.presets.addItem("None")
                return
            for key in UserConfig.content.keys():
                self.presets.addItem(key)