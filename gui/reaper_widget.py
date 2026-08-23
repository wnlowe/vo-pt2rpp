from unittest import case

from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QComboBox,
                               QFileDialog, QPushButton, QMessageBox)
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtCore import QTimer, QProcess, Signal
import os, sys, time, socket
from pathlib import Path
import reapy
from preferences_manager import Config
from log import log, log_func

class MinDurationGuard:
    def __init__(self, min_ms):
        self.min_ms = min_ms
        self.start = time.perf_counter()

    @log_func("print")
    def run_after(self, callback):
        elapsed = (time.perf_counter() - self.start) * 1000
        remaining = max(0, self.min_ms - elapsed)
        QTimer.singleShot(int(remaining), callback)

class ReaperWidget(QGroupBox):
    reaper_ready = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Reaper Configuration")
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

    @log_func("print")
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
            if self.configuration_selector.count() == 0:
                for path in values:
                    self.configuration_selector.addItem(path)
            return
        elif type(config_path) == str and config_path != "":
            self._add_combo_value(config_path, values)
        elif type(config_path) == list and len(config_path) > 0:
            for path in config_path:
                if path not in list:
                    self._add_combo_value(path, values)
                else:
                    continue

    @log_func("print")
    def _add_combo_value(self, config_path: str, values: list):
        self.configuration_selector.addItem(config_path)
        self.configuration_selector.setCurrentText(config_path)
        values: list = Config.get_value("directories.reaper_paths")
        values.append(config_path)
        Config.set_value("directories.reaper_paths", values)

    @log_func("print")
    def verify_configuration(self, v = True):
        self.add_configuration.setEnabled(False)
        self.execute_configuration.setEnabled(False)
        self.execute_configuration.setText("Verifying...")
        guard = MinDurationGuard(500)
        result = self._check_ready(v)
        match result:
            case 0:
                self.execute_configuration.setText("Success")
                guard.run_after(self._ready_execution)
            case 1:
                guard.run_after(self._need_restart)
            case 2:
                guard.run_after(lambda: self._register_reaper(True))

    @log_func("print")
    def _check_ready(self, allow_retry) -> int:
        import psutil
        if self._check_reapy():
            return 0
        reaper_running = any("reaper" in (p.info.get("name") or "").lower()
               for p in psutil.process_iter(["name"]))
        if reaper_running and allow_retry:
            if self._reaper_troubleshoot():
                msg = QMessageBox.information(self, "Startup Tip",
                                              '''With SWS installed you have a "Set Global Startup Action" action
                                              in your action list. If you already have something here, in your action
                                              list you can create a custom action to hold multiple actions including
                                              "activate_reapy_server.py" and set this new custom action to be your
                                              global startup action. This will allow you to have multiple startup
                                              actions as long as you add them to your custom action.''')
                if self._check_reapy():
                    return 0
        if reaper_running:
            return 1
        return 2

    @log_func("print")
    def _reaper_troubleshoot(self):
        msg_1 = QMessageBox()
        msg_1.setWindowTitle("Troubleshooting")
        msg_1.setText("It appears REAPER is running, is this true?")
        msg_1.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        ret = msg_1.exec()
        if ret == QMessageBox.StandardButton.Yes:
            msg_2 = QMessageBox()
            msg_2.setWindowTitle("Startup Action")
            msg_2.setText('You should now have an action titled "activate_reapy_server.py" in your'
                          'action list, has that now been run?')
            msg_2.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            ret_2 = msg_2.exec()
            if ret_2 == QMessageBox.StandardButton.Yes:
                return True
        return False

    @log_func("print")
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
                    self._need_restart()
                    return
                self._register_reaper(True)
                return
            case QMessageBox.StandardButton.Close:
                import psutil
                for p in psutil.process_iter(["name", "pid"]):
                    if "reaper" in (p.info.get("name") or "").lower():
                        self._close_reaper(p.info["pid"])
            case QMessageBox.StandardButton.Cancel:
                self._rerun()
                return

    @log_func("print")
    def _close_reaper(self, pid: int):
        if sys.platform == "win32":
            QProcess.startDetached("taskkill", ["/PID", str(pid)])
        elif sys.platform == "darwin":
            QProcess.startDetached("osascript", ["-e", 'tell application "REAPER" to quit'])
        else:
            raise NotImplementedError("Graceful REAPER close not implemented for this platform")
        self._check_reaper_state(0, self._register_reaper)

    @log_func("print")
    def _check_reaper_state(self, iterations: int, on_complete, rpp_open:bool = False, ):
        import psutil
        is_running = any("reaper" in (p.info.get("name") or "").lower()
               for p in psutil.process_iter(["name"]))
        if is_running == rpp_open:
            if on_complete:
                on_complete(True)
            return
        if iterations > 15:
            if on_complete:
                on_complete(False)
            return

        self._reaper_timer = QTimer(singleShot=True, interval=2000)
        self._reaper_timer.timeout.connect(
            lambda: self._check_reaper_state(iterations + 1, on_complete, rpp_open)
        )
        self._reaper_timer.start()

    @log_func("print")
    def _register_reaper(self, reaper_closed: bool):
        if not reaper_closed:
            self._rerun()
            return
        try:
            resource_path = self.configuration_selector.currentText()
            reapy.configure_reaper(resource_path=resource_path)
        except Exception as e:
            QMessageBox.critical(self, "Registration failed", str(e))
            self._rerun()
            return

        msg = QMessageBox()
        msg.setText("Reaper has been registered")
        msg.setInformativeText("You can now start reaper. Press OK when REAPER is running.")
        msg.exec()
        self._check_reaper_state(0, self.verify_configuration, True)
        return

    @log_func("print")
    def _rerun(self):
        self.execute_configuration.setText("Verify")
        self.execute_configuration.setEnabled(True)

    @log_func("print")
    def _check_reapy(self, timeout: float = 2.0) -> bool:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            return reapy.dist_api_is_enabled()
        except OSError:
            return False
        finally:
            socket.setdefaulttimeout(old_timeout)

    @log_func("print")
    def _ready_execution(self):
        self.reaper_ready.emit()