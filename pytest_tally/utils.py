import fcntl
import json
import os
from pathlib import Path
from typing import Any, Dict


def clear_file(filename: Path) -> None:
    with open(filename, "w") as jfile:
        jfile.write("")


class LocakbleJsonFileUtils:
    """
    Class to handle locking and reading/writing to a json file

    __init__ Args:
        file_path (Path): Path to the json file

    Public Methods:
        read_json: Read the json file and return the data
        write_json: Write the json file with the data

    Example:
        >>> file_path = Path("test.json")
        >>> clear_file(file_path)
        >>> utils = LocakbleJsonFileUtils(file_path)
        >>> utils.write_json({"test": "test"})
        >>> utils.read_json()
        => {'test': 'test'}
    """

    def __init__(self, file_path: Path):
        assert isinstance(file_path, Path), f"File {file_path} must be a Path object"
        assert file_path.exists(), f"File {file_path} must exist"
        assert file_path.suffix == ".json", f"File {file_path} must be a json file"
        self.file_path: Path = file_path
        self.file: Any = None

    def _acquire_read_lock(self):
        os.makedirs(self.file_path.parent, exist_ok=True)
        self.file = open(self.file_path, "r")
        fcntl.flock(self.file, fcntl.LOCK_SH)

    def _acquire_overwrite_lock(self):
        os.makedirs(self.file_path.parent, exist_ok=True)
        self.file = open(self.file_path, "w")
        fcntl.flock(self.file, fcntl.LOCK_EX)

    def _acquire_append_lock(self):
        os.makedirs(self.file_path.parent, exist_ok=True)
        self.file = open(self.file_path, "a")
        fcntl.flock(self.file, fcntl.LOCK_EX)

    def _release_lock(self):
        fcntl.flock(self.file, fcntl.LOCK_UN)
        self.file.close()
        self.file = None

    def read_json(self):
        self._acquire_read_lock()
        try:
            data = json.load(self.file)
        except json.decoder.JSONDecodeError:
            data = {}
        except FileNotFoundError:
            os.makedirs(self.file_path.parent, exist_ok=True)
            data = {}
        finally:
            self._release_lock()
        return data

    def overwrite_json(self, data: Dict[str, Any]):
        self._acquire_overwrite_lock()
        try:
            self.file.seek(0)
            json.dump(data, self.file, indent=4)
            self.file.truncate()
        finally:
            self._release_lock()

    def append_json(self, data: Dict[str, Any]):
        self._acquire_append_lock()
        try:
            self.file.seek(0)
            json.dump(data, self.file, indent=4)
            self.file.truncate()
        finally:
            self._release_lock()
