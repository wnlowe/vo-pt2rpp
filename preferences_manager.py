import json
import os, sys
from pathlib import Path
import tomlkit as toml

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
                        "preferences" : str(self.preferences_file.parent),
                        "aaf-path" : "",
                        "excel-path" : "",
                        "reaper-paths" : []
                    },
                    "reaper" :{
                        "failed-restart" : '0'
                    },
                    "record-modes" : ["Stop-Start", "Pulled Down Selects"],
                    "selected" : {
                        "reaper-path" : "",
                        "record-mode" : ""
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

class UserSettingsManager:
    def __init__(self):
        data_path = Config.get_value("directories.preferences")
        self.config_file = Path(data_path) / 'user_preferences.toml'
        if not self.config_file.exists():
            self._initialize_toml(self.config_file)

        self.content = self.get_user_config()

    def _initialize_toml(self, path):
        doc = toml.document()

        template = toml.table()
        template.add(toml.nl())
        template.add(toml.comment("Fill in default search paths for each if desired."))
        template.add(toml.key(["path", "aaf"]), "")
        template.add(toml.key(["path", "excel"]), "")
        template.add(toml.key(["path", "reaper"]), "")

        template.add(toml.nl())
        template.add(toml.comment(
        "Add or remove key values as needed. Keys are the dropdown values while the value array are auto"
        "connect column names. Hidden array is for column names which will not display."
        ))
        template.add(toml.key(["excel", "none"]), "")
        template.add(toml.key(["excel", "filename"]), [''])
        template.add(toml.key(["excel", "line-text"]), [''])
        template.add(toml.key(["excel", "character"]), [''])
        template.add(toml.key(["excel", "select"]), [''])

        template.add(toml.nl())
        template.add(toml.key(["excel", "hidden"]), [''])

        template.add(toml.nl())
        template.add(toml.comment(
        "In the AAF section, mode is the default selection for the record mode dropdown."
        "Identifiers are strings that will exist in track names which will be pulled out "
        "for the REAPER import."
        ))
        template.add(toml.key(["aaf", "mode"]), 'Stop-Start')
        template.add(toml.key(["aaf", "identifiers"]), [''])
        template.add(toml.nl())

        doc["template"] = template

        with open(self.config_file, "w", encoding='utf-8') as file:
            toml.dump(doc, file)

    def user_config_exists(self):
        return self.config_file.exists()

    def get_user_config(self):
        with open(self.config_file, "r", encoding='utf-8') as file:
            return toml.load(file)


Config = PreferencesManager()
UserConfig = UserSettingsManager()