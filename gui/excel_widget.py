from PySide6.QtWidgets import (QListWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QLabel, QPushButton, QFileDialog, QGroupBox,
                               QWidget, QComboBox, QListWidgetItem)
from PySide6.QtCore import Qt, Signal
from pathlib import Path
import excel_parse as excel
from preferences_manager import Config

class ColumnSelectorRow(QWidget):
    hide_column = Signal(str)
    def __init__(
            self,
            parent=None,
            name:str | None = None,
            alignment_categories:list[str] | None = None
    ):
        super().__init__(parent)
        if name is None or alignment_categories is None:
            return
        self.layout = QHBoxLayout(self)
        self.name = QLabel(name)
        self.alignment = QComboBox()
        self.alignment.addItems(alignment_categories)
        self.hide_row_button = QPushButton("Hide Row")
        self.hide_row_button.clicked.connect(self.hide_row)

        self.layout.addWidget(self.name)
        self.layout.addStretch()
        self.layout.addWidget(self.alignment)
        self.layout.addWidget(self.hide_row_button)

    def get_alignment(self):
        return self.alignment.currentText()

    def get_name(self):
        return self.name.text()

    def hide_row(self, state:bool):
        self.hide_column.emit(self.name.text())

class ExcelWidget(QGroupBox):
    excel_ready = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Excel Files")
        self.setMaximumHeight(500)
        self.main_layout = QVBoxLayout(self)

        self.files_select = QHBoxLayout()
        self.main_layout.addLayout(self.files_select)

        self.display_path = QLabel("No File Selected")
        self.files_select.addWidget(self.display_path)
        self.files_select_button = QPushButton("Select File")
        self.files_select_button.clicked.connect(self.source_files)
        self.files_select.addWidget(self.files_select_button)

        self.files = None
        self.column_names = []
        self.alignment_dict = Config.get_value("excel.alignments")
        self.alignment_categories = self.alignment_dict.keys()
        self.hidden_rows = Config.get_value("excel.hidden")

        self.column_organizer = QTabWidget()
        self.column_organizer.setMaximumHeight(400)
        self.column_sheets:list[QListWidget] = []
        self.aligned_columns = []

    def source_files(self):
        pref_path = Config.get_value("directories.excel-path")
        files = QFileDialog.getOpenFileNames(
            self,
            "Open File",
            str(Path.home() / "Downloads") if pref_path == "" else pref_path,
            filter="Excel files (*.xlsx)"
        )
        self.files = files[0]
        path = Path(self.files[-1]).parent
        if path != pref_path:
            Config.set_value("directories.excel-path", str(path))
        self.display_path.setText(", ".join(files[0]))
        for file in self.files:
            self.column_names.append(excel.read_excel(file))
        length = len(self.column_names)
        if length > 0:
            if length == 1:
                tab = self._configure_column_organizer()
                self.column_organizer.addTab(tab, self.files[0])
                self.column_sheets.append(tab)
            else:
                for i in range(length):
                    self.column_organizer.addTab(self.column_names[i], self.column_names[i])
            self.main_layout.addWidget(self.column_organizer)

        self.get_aligned_columns(0)

        self.excel_ready.emit()

    def _configure_column_organizer(self, idx = 0) -> QListWidget:
        widget = QListWidget(supportedDragActions=Qt.DropAction.MoveAction)
        for item in self.column_names[idx]:
            if item in self.hidden_rows:
                continue
            row = QListWidgetItem(widget)
            row_widget = ColumnSelectorRow(name=item, alignment_categories=self.alignment_categories)
            for key in self.alignment_categories:
                if item in self.alignment_dict[key]:
                    row_widget.alignment.setCurrentText(key)
                    break

            row.setSizeHint(row_widget.sizeHint())
            widget.setItemWidget(row, row_widget)
            row_widget.hide_column.connect(
                lambda row_name, w=widget, r=row: self.add_hidden_row(row_name, w, r)
            )
        return widget

    def add_hidden_row(self, row_name:str, widget: QListWidget, item:QListWidgetItem):
        self.hidden_rows.append(row_name)
        idx = widget.row(item)
        row_widget = widget.itemWidget(item)
        widget.removeItemWidget(item)
        if row_widget is not None:
            row_widget.deleteLater()
        widget.takeItem(idx)

        Config.set_value("excel.hidden", self.hidden_rows)

    def get_aligned_columns(self, sheet_idx:int):
        sheet = self.column_sheets[sheet_idx]
        valid_columns = []
        for i in range(sheet.count()):
            row = sheet.item(i)
            row_widget = sheet.itemWidget(row)
            if not row_widget.alignment.currentText() == "None":
                valid_columns.append((i, row_widget.name.text(), row_widget.alignment.currentText()))
        self.aligned_columns = valid_columns


    def get_value(self, sheet_idx:int, column: int | str, value: str):
        sheet = self.column_sheets[sheet_idx]
        column_idx = None
        if type(column) == str:
            ...
        elif type(column) == int:
            column_idx = column
        else:
            return
        row = sheet.item(column_idx)
        row_widget:ColumnSelectorRow = sheet.itemWidget(row)
        match value:
            case "name":
                print(row_widget.name.text())
            case "alignment":
                print(row_widget.alignment.currentText())