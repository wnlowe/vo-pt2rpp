from PySide6.QtWidgets import (QWidget, QFileDialog, QVBoxLayout, QPushButton,
                               QHBoxLayout, QLabel, QGroupBox, QComboBox)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal
from pathlib import Path
import aaf_parse as aaf
from preferences_manager import Config, UserConfig

class AAF_Widget(QGroupBox):
    aaf_ready = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("AAF")
        self.main_layout = QVBoxLayout(self)

        self.select_aaf_button = QPushButton(QIcon("icons/file-headphone.png"), "Select AAF")
        self.select_aaf_button.clicked.connect(self.select_aaf)
        self.aaf_path = None

        self.display_path = QLabel("No Path Selected")

        self.aaf_selector = QHBoxLayout()
        self.aaf_selector.addWidget(self.display_path)
        self.aaf_selector.addWidget(self.select_aaf_button)

        self.main_layout.addLayout(self.aaf_selector)

        self._collect_toml()
        self.config_select = QComboBox()
        self.config_select.addItems(["None", "New Config..."])

###TEMP?
        self.session = None
        self.track_names = []
        self.track_roles = []

        self.aaf_overview = QVBoxLayout()
        self.tracks_layout = QHBoxLayout()
        self.roles_layout = QHBoxLayout()

        self.tracks_info = QLabel("Select Valid AAF First")
        self.roles_info = QLabel("Select Valid AAF First")

        self.tracks_layout.addWidget(self.tracks_info)
        self.roles_layout.addWidget(self.roles_info)

        self.aaf_overview.addLayout(self.tracks_layout)
        self.aaf_overview.addLayout(self.roles_layout)

        self.main_layout.addLayout(self.aaf_overview)



    def select_aaf(self):
        perf_path = Config.get_value("directories.aaf-path")
        path = QFileDialog.getOpenFileName(
            caption="PT AAF Select",
            dir=str(Path.home() / "Downloads") if perf_path == "" else perf_path,
            filter="PT AAF (*.aaf)"
        )[0]
        success = True
        if path == "" or path is None:
            path = "No AAF Selected"
            success = False
        self.display_path.setText(path)
        if success:
            self.process_aaf(path)
            self.aaf_ready.emit()
            new_path = str(Path(path).parent)
            if new_path != perf_path:
                Config.set_value("directories.aaf-path", new_path)

    def process_aaf(self, path):
        output: aaf.AAFSession = aaf.parse_aaf(path, ["4060", "4061", "416", "selects", "alts"])
        self.session = output
        for track in output.tracks:
            self.track_names.append(track.name)
            self.track_roles.append(track.suggested_role)
        self._update_info()

    def _update_info(self):
        self.tracks_info.setText(f"Tracks: {self.track_names}")
        self.roles_info.setText(f"Roles: {self.track_roles}")
