from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QFileDialog, QGroupBox)
from pathlib import Path

class ExcelWidget(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Excel Files")
        self.main_layout = QVBoxLayout(self)

        self.files_select = QHBoxLayout()
        self.main_layout.addLayout(self.files_select)

        self.display_path = QLabel("No File Selected")
        self.files_select.addWidget(self.display_path)
        self.files_select_button = QPushButton("Select File")
        self.files_select_button.clicked.connect(self.source_files)
        self.files_select.addWidget(self.files_select_button)

        self.files = None

    def source_files(self):
        files = QFileDialog.getOpenFileNames(self, "Open File", str(Path.home() / "Downloads"), filter="Excel files (*.xlsx)")
        self.files = files[0]
        self.display_path.setText(", ".join(files[0]))