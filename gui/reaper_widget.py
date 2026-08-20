from unittest import case

from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QComboBox,
                               QFileDialog, QPushButton, QMessageBox)
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtCore import QTimer, QProcess
import os, sys, time, socket
from pathlib import Path
import reapy
from preferences_manager import Config

class MinDurationGuard:
    def __init__(self, min_ms):
        self.min_ms = min_ms
        self.start = time.perf_counter()

    def run_after(self, callback):
        elapsed = (time.perf_counter() - self.start) * 1000
        remaining = max(0, self.min_ms - elapsed)
        QTimer.singleShot(int(remaining), callback)

class ReaperWidget(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Reaper Configuration")
        self.layout = QVBoxLayout(self)

        self.configuration_layout = QHBoxLayout()
        self.add_configuration = QPushButton("+")
        self.add_configuration.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.configuration_selector = QComboBox()
        self._find_configuration()
        self.add_configuration.clicked.connect(lambda: self._find_configuration(True))
        self.execute_configuration = QPushButton("Verify")
        self.execute_configuration.clicked.connect(self.verify_configuration)

        self.configuration_layout.addWidget(self.add_configuration)
        self.configuration_layout.addWidget(self.configuration_selector)
        self.configuration_layout.addWidget(self.execute_configuration)

        self.layout.addLayout(self.configuration_layout)

    def _find_configuration(self, manual = False):
        config_path = ""
        values: list = Config.get_value("directories.reaper_paths")
        if manual:
            config_path = QFileDialog.getExistingDirectory(None, "Select REAPER Configuration")
        else:
            if len(values) > 0:
                config_path = values
            if sys.platform == "win32":
                config_path = str(Path(os.environ["APPDATA"]) / "REAPER")
            elif sys.platform == "darwin":
                config_path = str(Path.home() / "Library" / "Application Support" / "REAPER")

        if config_path in values:
            return
        elif type(config_path) == str and config_path != "":
            self._add_combo_value(config_path, values)
        elif type(config_path) == list and len(config_path) > 0:
            for path in config_path:
                if path not in list:
                    self._add_combo_value(path, values)
                else:
                    continue

    def _add_combo_value(self, config_path: str, values: list):
        self.configuration_selector.addItem(config_path)
        self.configuration_selector.setCurrentText(config_path)
        values: list = Config.get_value("directories.reaper_paths")
        values.append(config_path)
        Config.set_value("directories.reaper_paths", values)

    def verify_configuration(self):
        self.add_configuration.setEnabled(False)
        self.execute_configuration.setEnabled(False)
        self.execute_configuration.setText("Verifying...")
        guard = MinDurationGuard(500)
        result = self._check_ready()
        match result:
            case 0:
                self.execute_configuration.setText("Success")
                guard.run_after(...)
            case 1:
                guard.run_after(self._need_restart)
            case 2:
                guard.run_after(self._register_reaper)

    def _check_ready(self) -> int:
        import psutil
        if self._check_reapy():
            return 0
        if any("reaper" in (p.info.get("name") or "").lower()
               for p in psutil.process_iter(["name"])):
            return 1
        return 2

    def _need_restart(self):
        msgBox = QMessageBox()
        msgBox.setText("Reaper Needs to Close")
        msgBox.setInformativeText("Close reaper yourself and hit OK or hit Close to close REAPER")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Ok |
                                  QMessageBox.StandardButton.Close |
                                  QMessageBox.StandardButton.Cancel)
        msgBox.setDefaultButton(QMessageBox.StandardButton.Close)
        ret = msgBox.exec()

        match ret:
            case QMessageBox.StandardButton.Ok:
                import psutil
                if any("reaper" in (p.info.get("name") or "").lower()
                       for p in psutil.process_iter(["name"])):
                    self._need_restart(True)
                    return
                self._register_reaper()
            case QMessageBox.StandardButton.Close:
                import psutil
                for p in psutil.process_iter(["name", "pid"]):
                    if "reaper" in (p.info.get("name") or "").lower():
                        self._close_reaper(p.info["pid"])
            case QMessageBox.StandardButton.Cancel:
                self._rerun()
                return

    def _close_reaper(self, pid: int):
        if sys.platform == "win32":
            QProcess.startDetached("taskkill", ["/PID", str(pid)])
        elif sys.platform == "darwin":
            QProcess.startDetached("osascript", ["-e", 'tell application "REAPER" to quit'])
        else:
            raise NotImplementedError("Graceful REAPER close not implemented for this platform")

    def _check_closed(self, iterations: int):
        import psutil
        if not any("reaper" in (p.info.get("name") or "").lower()
               for p in psutil.process_iter(["name"])):
            self._register_reaper()
            return
        if iterations > 15:
            self._rerun()
            return
        timer = QTimer(singleShot=True, interval=2000)
        timer.timeout.connect(lambda: self._check_closed(iterations + 1))

    def _register_reaper(self):
        resource_path = self.configuration_selector.currentText()
        reapy.configure_reaper(resource_path=resource_path)
        # Message box to say it is safe to restart reaper now
        # Take us to activating the execute button
        ...

    def _rerun(self):
        self.execute_configuration.setText("Verify")
        self.execute_configuration.setEnabled(True)

    def _check_reapy(self, timeout: float = 2.0) -> bool:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            return reapy.dist_api_is_enabled()
        except OSError:
            return False
        finally:
            socket.setdefaulttimeout(old_timeout)