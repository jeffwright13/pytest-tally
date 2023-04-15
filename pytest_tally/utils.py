import fcntl
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def human_time_duration(seconds):
    # Credit to borgstrom: https://gist.github.com/borgstrom/936ca741e885a1438c374824efb038b3
    TIME_DURATION_UNITS = (
        ("week", 60 * 60 * 24 * 7),
        ("day", 60 * 60 * 24),
        ("hour", 60 * 60),
        ("min", 60),
        ("sec", 1),
    )

    if seconds == 0:
        return "inf"
    parts = []
    for unit, div in TIME_DURATION_UNITS:
        amount, seconds = divmod(int(seconds), div)
        if amount > 0:
            parts.append(f'{amount} {unit}{"" if amount == 1 else "s"}')
    return ", ".join(parts)


def cleanup_unserializable(d: Dict[str, Any]) -> Dict[str, Any]:
    # Credit to https://github.com/pytest-dev/pytest-reportlog
    """Return new dict with entries that are not json serializable by their str()."""
    result = {}
    for k, v in d.items():
        try:
            json.dumps({k: v})
        except TypeError:
            v = str(v)
        result[k] = v
    return result


def clear_file(filename: Path) -> None:
    print(f"Clearing file: {filename} at time {datetime.now()}")
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

    def _acquire_lock(self):
        os.makedirs(self.file_path.parent, exist_ok=True)
        self.file = open(self.file_path, "r+")
        fcntl.flock(self.file, fcntl.LOCK_EX)

    def _release_lock(self):
        fcntl.flock(self.file, fcntl.LOCK_UN)
        self.file.close()
        self.file = None

    def read_json(self):
        self._acquire_lock()
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

    def write_json(self, data: Dict[str, Any]):
        self._acquire_lock()
        try:
            self.file.seek(0)
            json.dump(data, self.file, indent=4)
            self.file.truncate()
        finally:
            self._release_lock()


"""
def file_locker(
    filename: Path,
) -> FileLock:
    '''Following code is from Python Cookbook online: https://www.oreilly.com/library/view/python-cookbook/0596001673/ch04s25.html'''
    if os.name == "nt":
        import pywintypes
        import win32con
        import win32file

        LOCK_EX = win32con.LOCKFILE_EXCLUSIVE_LOCK
        LOCK_SH = 0  # the default
        LOCK_NB = win32con.LOCKFILE_FAIL_IMMEDIATELY
        __overlapped = pywintypes.OVERLAPPED()

        def lock(file, flags):
            hfile = win32file._get_osfhandle(file.fileno())
            win32file.LockFileEx(hfile, flags, 0, 0xFFFF0000, __overlapped)

        def unlock(file):
            hfile = win32file._get_osfhandle(file.fileno())
            win32file.UnlockFileEx(hfile, 0, 0xFFFF0000, __overlapped)

    elif os.name == "posix":
        from fcntl import LOCK_EX, LOCK_NB, LOCK_SH

        def lock(file, flags):
            fcntl.flock(file.fileno(), flags)

        def unlock(file):
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)

    else:
        raise RuntimeError("PortaLocker only defined for nt and posix platforms")
"""

"""
import json
import os
import sys
import fcntl  # Unix-based systems
import msvcrt  # Windows

class FileLock:
    def __init__(self, file_path):
        self.file_path = file_path
        self.locked = False

    def acquire(self):
        try:
            if sys.platform == "win32":
                # Windows platform
                self.file_handle = open(self.file_path, "r+")
                msvcrt.locking(self.file_handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                # Unix-based platforms (Mac, Linux, etc.)
                self.file_handle = open(self.file_path, "r+")
                fcntl.flock(self.file_handle, fcntl.LOCK_EX)
            self.locked = True
        except Exception as e:
            print(f"Error acquiring file lock: {e}")

    def release(self):
        try:
            if self.locked:
                if sys.platform == "win32":
                    # Windows platform
                    msvcrt.locking(self.file_handle.fileno(), msvcrt.LK_UNLCK, 1)
                    self.file_handle.close()
                else:
                    # Unix-based platforms (Mac, Linux, etc.)
                    fcntl.flock(self.file_handle, fcntl.LOCK_UN)
                    self.file_handle.close()
                self.locked = False
        except Exception as e:
            print(f"Error releasing file lock: {e}")

    def write(self, data):
        try:
            self.acquire()
            with open(self.file_path, "w") as file:
                json.dump(data, file)
        finally:
            self.release()

    def read(self):
        try:
            self.acquire()
            with open(self.file_path, "r") as file:
                data = json.load(file)
            return data
        finally:
            self.release()
"""
