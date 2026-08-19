import json
import os, sys
from pathlib import Path

class PreferencesManager:
    def __init__(self):
        _preferences_file = ""
        if sys.platform == "win32":
            _preferences_file = Path(os.environ["APPDATA"]) / "VO_Tools" / "Preferences.json"
        elif sys.platform == "darwin":
            _preferences_file = Path.home() / "Library" / "Application Support" / "VO_Tools" / "Preferences.json"
        else:
            _preferences_file = Path.home() / ".config" / "VO_Tools" / "Preferences.json"

        self.preferences_file = _preferences_file

        if not _preferences_file.exists():
            self._initialize_preferences()

        self._read_preferences()

    def _initialize_preferences(self):
        os.makedirs(os.path.dirname(self.preferences_file), exist_ok=True)

        with open(self.preferences_file, "w", encoding='utf-8') as file:
            json.dump(
                {
                    "excel" : {
                        "alignments" : {
                            "None" : [],
                            "Filename" : ["DLG ID"],
                            "Line Text" : ["English (United States)"],
                            "Character" : ["Voice"],
                            "Select" : ["Rec. Selection"],
                            "Takes" : ["Rec. Takes"],
                            "Updated Line" : ["Rec. Text Change"],
                            "Record Date" : ["Date Recorded"]
                        },
                        "hidden" : []
                    },
                    "directories" : {
                        "aaf_path" : "",
                        "excel_path" : ""
                    }
                },
                file,
                ensure_ascii=False,
                indent=4
            )

    def _read_preferences(self):
        with open(self.preferences_file, "r", encoding='utf-8') as file:
            self.settings = json.loads(file.read())

    def _update_preferences(self):
        with open(self.preferences_file, "w", encoding='utf-8') as file:
            json.dump(self.settings, file, ensure_ascii=False, indent=4)

    def get_value(self, key):
        """
        Use dot separated key to access non-top level keys
        """
        parts = key.split(".")
        value = self.settings
        for part in parts:
            value = value[part]
        return value

    def set_value(self, key, value):
        """
        Use dot separated key to access non-top level keys
        """
        parts = key.split(".")
        target = self.settings
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value

        self._update_preferences()

Config = PreferencesManager()