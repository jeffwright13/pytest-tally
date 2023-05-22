import json
import logging
import shutil
import sys
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog
from tkinter.ttk import Notebook, Progressbar

from quantiphy import Quantity, render
from watchdog.events import FileSystemEventHandler, LoggingEventHandler
from watchdog.observers import Observer

from pytest_tally import __version__
from pytest_tally.plugin import DEFAULT_FILE, TallySession
from pytest_tally.utils import LocakbleJsonFileUtils, clear_file

TERM_SIZE = shutil.get_terminal_size()
APP_HEIGHT = 700
APP_WIDTH = 1020
APP_TITLE = f"Pytest Tally v{__version__}"


@dataclass
class TableColumn:
    name: str
    width: int


TABLE_COLUMNS = [
    TableColumn("  node_id", 70),
    TableColumn("  duration", 20),
    TableColumn("  outcome", 20),
]


class Duration(Quantity):
    units = "s"
    prec = 2


class Stats:
    def __init__(self) -> None:
        self.tot_num_to_run: int = 0
        self.num_running: int = 0
        self.num_finished: int = 0
        self.testing_started: bool = False
        self.testing_complete: bool = False

    def _get_test_session_data(
        self, file_path: Path, init: bool = False
    ) -> TallySession:
        lock_utils = LocakbleJsonFileUtils(file_path=file_path)
        if init:
            return TallySession(
                session_started=False,
                session_finished=False,
                session_duration=0.0,
                num_tests_to_run=0,
                num_tests_have_run=0,
                timer=None,
                lastline="",
                lastline_ansi="",
                tally_tests={},
                config=None,
            )
        j = lock_utils.read_json()
        if j:
            return TallySession(**j, config=None)

    def update_stats(self, file_path: Path, init: bool = False) -> None:
        """Retrieve latest info from json file"""
        self.test_session_data = self._get_test_session_data(
            file_path=file_path, init=init
        )
        if self.test_session_data:
            self.tot_num_to_run = self.test_session_data.num_tests_to_run
            self.num_running = len(
                [
                    test
                    for test in self.test_session_data.tally_tests.values()
                    if test["timer"]["running"]
                ]
            )
            self.num_finished = len(
                [
                    test
                    for test in self.test_session_data.tally_tests.values()
                    if test["timer"]["finished"]
                ]
            )
            self.testing_started = self.test_session_data.session_started
            self.testing_complete = self.test_session_data.session_finished


class FileChangeEventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory and Path(event.src_path) == self.file_path:
            self.callback()


class TestResultsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.stats = Stats()
        self.file_path = DEFAULT_FILE
        self.max_rows = None

        self.create_widgets()
        self.file_observer = None  # Initialize the file_observer attribute
        if self.file_path:
            self.start_file_monitoring()

    def create_widgets(self):
        self.title_label = tk.Label(
            self.root, text="Test Results", font=("Arial", 18, "bold")
        )
        self.title_label.grid(row=0, column=0, columnspan=3, pady=10)

        self.resize_button = tk.Button(
            self.root, text="Resize", command=self.resize_window
        )
        self.resize_button.grid(row=1, column=0, pady=10)

        self.notebook = Notebook(self.root)
        self.notebook.grid(row=1, column=0, columnspan=3, pady=10, sticky="nsew")

        self.table_tab = tk.Frame(self.notebook)
        self.notebook.add(self.table_tab, text="Results")

        self.config_tab = tk.Frame(self.notebook)
        self.notebook.add(self.config_tab, text="Configuration")

        self.create_config_widgets()
        self.create_table_widgets()

        # Create a label to display the lastline
        self.lastline_label = tk.Label(
            self.root,
            font=tkfont.Font(family="Arial", size=14, weight="bold"),
            justify=tk.CENTER,
            # anchor="nsew",
            wraplength=APP_WIDTH - 100,
        )
        self.lastline_label.grid(
            row=2, column=0, columnspan=3, padx=10, pady=5, sticky="nsew"
        )

    def create_config_widgets(self):
        self.config_frame = tk.Frame(self.config_tab)
        self.config_frame.pack(pady=10)

        self.file_label = tk.Label(self.config_frame, text="File Path:")
        self.file_label.grid(row=0, column=0, sticky="w")

        self.file_entry = tk.Entry(self.config_frame, width=20)
        self.file_entry.grid(row=0, column=1, padx=5, sticky="w")

        self.browse_button = tk.Button(
            self.config_frame, text="Browse", command=self.browse_file
        )
        self.browse_button.grid(row=0, column=2, padx=5, sticky="w")

        self.max_rows_label = tk.Label(self.config_frame, text="Max Rows:")
        self.max_rows_label.grid(row=0, column=3, padx=5, sticky="w")

        self.max_rows_entry = tk.Entry(self.config_frame, width=10)
        self.max_rows_entry.grid(row=0, column=4, padx=5, sticky="w")

        self.apply_button = tk.Button(
            self.config_frame, text="Apply", command=self.apply_config
        )
        self.apply_button.grid(row=0, column=5, padx=5, sticky="w")

    def create_table_widgets(self):
        self.table_frame = tk.Frame(self.table_tab)
        self.table_frame.pack(pady=10)

        self.table_header = tk.Frame(self.table_frame)
        self.table_header.pack()

        for i, header in enumerate(TABLE_COLUMNS):
            label = tk.Label(
                self.table_header,
                text=header.name,
                font=("Arial", 14, "bold"),
                width=header.width,
                anchor="w",
            )
            label.grid(row=0, column=i, padx=10, pady=5, sticky="w")

        self.table_canvas = tk.Canvas(self.table_frame, height=400)
        self.table_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create the table body and configure the canvas
        self.table_body = tk.Frame(self.table_canvas)
        self.table_canvas.create_window((0, 0), window=self.table_body, anchor="nw")

        # Create the scrollbar after creating the canvas
        self.table_scrollbar = tk.Scrollbar(
            self.table_frame, orient=tk.VERTICAL, command=self.table_canvas.yview
        )
        self.table_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure the canvas to use the scrollbar
        self.table_canvas.configure(yscrollcommand=self.table_scrollbar.set)

        # Bind the scrollbar and canvas together
        self.table_scrollbar.config(command=self.table_canvas.yview)
        self.table_canvas.bind_all(
            "<MouseWheel>",
            lambda event: self.table_canvas.yview_scroll(
                int(-1 * (event.delta / 120)), "units"
            ),
        )

        # Configure the table_body to expand with the window size
        self.table_body.bind(
            "<Configure>",
            lambda event: self.table_canvas.configure(
                scrollregion=self.table_canvas.bbox("all")
            ),
        )

        # Attach the table_body to the canvas
        self.table_canvas.create_window((0, 0), window=self.table_body, anchor="nw")

        # Create the footer frame
        self.table_footer = tk.Frame(self.table_frame)
        self.table_footer.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        self.file_entry.delete(0, tk.END)
        self.file_entry.insert(0, file_path)

    def apply_config(self):
        self.file_path = Path(self.file_entry.get())
        if self.file_path:
            self.start_file_monitoring()

        max_rows = self.max_rows_entry.get()

        if self.file_path and max_rows:
            self.max_rows = int(max_rows)

            self.fetch_results()

    def fetch_results(self):
        if self.file_path is not None and self.file_path.is_file():
            self.stats.update_stats(file_path=self.file_path)

            if self.stats.test_session_data:
                self.update_table(self.stats.test_session_data.tally_tests)
            else:
                print("Error loading test session data.")
        else:
            print("Invalid file path.")

    def update_table(self, results):
        # Clear the table body
        for widget in self.table_body.winfo_children():
            widget.destroy()

        # Sort the results by node_id
        sorted_results = sorted(results.values(), key=lambda x: x["node_id"])

        # Display the maximum number of rows specified
        for i, result in enumerate(sorted_results[: self.max_rows]):
            row_frame = tk.Frame(self.table_body)
            row_frame.grid(row=i, column=0, padx=5, pady=2, sticky="w")

            node_id_label = tk.Label(
                row_frame,
                text=result["node_id"],
                font=("Arial", 14),
                width=TABLE_COLUMNS[0].width,
                anchor="w",
            )
            node_id_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

            duration_label = tk.Label(
                row_frame,
                text=render(Duration(result["test_duration"]), "s"),
                font=("Arial", 14),
                width=TABLE_COLUMNS[1].width,
                anchor="w",
            )
            duration_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")

            outcome_label = tk.Label(
                row_frame,
                text=result["test_outcome"],
                font=("Arial", 14),
                width=TABLE_COLUMNS[2].width,
                anchor="w",
            )
            outcome_label.grid(row=0, column=2, padx=10, pady=5, sticky="w")

        # Clear the lastline label
        self.lastline_label.config(text="")

        # Update the lastline label with final test results
        if self.stats.test_session_data:
            lastline = self.stats.test_session_data.lastline
            self.lastline_label.config(text=lastline)

    def start_file_monitoring(self):
        if self.file_path is not None and self.file_path.is_file():
            event_handler = FileChangeEventHandler(self.file_changed_callback)
            event_handler.file_path = (
                self.file_path
            )  # Set the file_path attribute in the event handler
            self.file_observer = Observer()
            self.file_observer.schedule(
                event_handler, str(self.file_path.parent), recursive=False
            )
            self.file_observer.start()
        else:
            print("Invalid file path.")

    def file_changed_callback(self):
        self.fetch_results()

    def stop_file_monitoring(self):
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()

    def __del__(self):
        self.stop_file_monitoring()

    def resize_window(self):
        new_height = min(
            TERM_SIZE.height - 200, self.stats.test_session_data.tot_num_to_run
        )
        self.root.geometry(f"{APP_WIDTH}x{new_height}")


def main():
    root = tk.Tk()
    root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
    TestResultsGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
