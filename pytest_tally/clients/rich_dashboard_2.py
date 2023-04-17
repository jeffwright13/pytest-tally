import os
from argparse import ArgumentParser, Namespace
from pathlib import Path
from threading import Event, Thread

from blessed import Terminal
from quantiphy import Quantity, render
from rich.box import ROUNDED as rounded
from rich.console import Console, Group, group
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress
from rich.status import Status
from rich.table import Table
from rich.text import Text

from pytest_tally.plugin import DEFAULT_FILE, TallySession
from pytest_tally.utils import LocakbleJsonFileUtils, clear_file

OUTCOME_STYLES = {
    "passed": "green",
    "failed": "bold red",
    "skipped": "yellow",
    "error": "bold magenta",
    "xfail": "red",
    "xpass": "bold yellow",
    "rerun": "yellow",
}


class Duration(Quantity):
    units = "s"
    prec = 2


class Options:
    """Options passed in by user from command line"""

    def __init__(self, args: Namespace) -> None:
        self.filename = Path(args.filename) if args.filename else Path(DEFAULT_FILE)
        assert (
            self.filename.suffix == ".json"
        ), "'filename', if specified, must end in '.json'"

        self.max_rows = args.max_rows if hasattr(args, "max_rows") else 0
        self.lines = args.lines
        self.persist = args.persist


class Stats:
    def __init__(self, options: Options) -> None:
        self.options = options
        self.total_num_tests = 0
        self.num_tests_run: int = 0
        self.testing_started: bool = False
        self.testing_complete: bool = False

    def _get_test_session_data(self, init: bool = False) -> TallySession:
        lock_utils = LocakbleJsonFileUtils(file_path=self.options.filename)
        if init:
            return TallySession(
                session_finished=False,
                session_duration=0.0,
                timer=None,
                lastline_ansi="",
                lastline="",
                tally_tests={},
                config=None,
            )
        j = lock_utils.read_json()
        if j:
            return TallySession(**j, config=None)

    def update_stats(self, init: bool = False) -> None:
        """Retrieve latest info from json file"""
        self.test_session_data = self._get_test_session_data(init=init)
        if self.test_session_data:
            self.total_num_tests = self.test_session_data.session_num_tests
            self.num_tests_run = len(
                [
                    test
                    for test in self.test_session_data.tally_tests.values()
                    if test["timer"]["finished"]
                ]
            )
            self.testing_started = self.num_tests_run > 0
            self.testing_complete = self.test_session_data.session_finished


class TallyApp:
    def __init__(self, args: Namespace):
        self.console = Console()
        self.term = Terminal()
        self.event = Event()
        self.table = Table(
            highlight=True, expand=True, show_lines=args.lines, box=rounded
        )
        self.progress = Progress(expand=True)
        self.progress_task = self.progress.add_task(
            "Waiting for tests to start...", start=False
        )
        self.panel_progress = Panel(self.progress)

        self.options = Options(args)
        self.stats = Stats(self.options)

    def kb_input(self):
        while True:
            with self.term.cbreak():
                if self.event.is_set() and not self.options.persist:
                    os._exit(0)
                key = self.term.inkey(timeout=1).lower()
                if key and key == "q":
                    os._exit(0)

    def main_panel_group(self, stylize_last_line: bool = True) -> Group:
        # main table (no panel container; it stands alone, looks better that way);
        # it's ok to loop over a Rich Table because it just redraws each iteration;
        # in fact the Table class does not even have an update() method.
        self.table = Table(
            highlight=True, expand=True, show_lines=self.options.lines, box=rounded
        )
        self.table.add_column("Test")
        self.table.add_column("Duration")
        self.table.add_column("Outcome")

        # wait till plugin.py starts to populate results file
        if (
            not hasattr(self.stats.test_session_data, "tally_tests")
            or not self.stats.test_session_data.tally_tests
        ):
            return self.panel_progress

        # accommodate optional execution flag for max rows to display ("-x"),
        num_table_rows = (
            len(self.stats.test_session_data.tally_tests)
            if self.options.max_rows == 0
            else self.options.max_rows
        )
        tally_tests = list(self.stats.test_session_data.tally_tests.values())[
            -num_table_rows:
        ]

        # for each test result, add a row to the table with test info
        for _, test in enumerate(tally_tests):
            name = Text(test["node_id"], style="bold blue")
            duration = (
                Duration(str(test["test_duration"])) if test["test_duration"] else 0.0
            )
            outcome = (
                Text(test["test_outcome"]) if test["test_outcome"] else Text("---")
            )
            for key, value in OUTCOME_STYLES.items():
                if key in outcome.plain.lower():
                    outcome.stylize(value)
                    name.stylize(value)
                    break
            else:
                outcome.stylize("bold blue")
                name.stylize("bold blue")

            # show spinny progress icon for last line of table unless session is over;
            # this ensures final rendered table won't have spinny icon frozen in time
            if stylize_last_line:
                if _ == len(tally_tests) - 1:
                    name = Status(name)
                    self.table.add_row(name, Status(""), outcome)
                else:
                    self.table.add_row(name, render(duration, "s"), outcome)
            else:
                self.table.add_row(name, render(duration, "s"), outcome)

        # update progress bar w/ containing panel
        self.stats.update_stats()
        if self.stats.testing_started:
            if self.stats.testing_complete:
                self.progress.update(
                    self.progress_task,
                    description="Testing Complete",
                    start=True,
                    completed=self.stats.num_tests_run,
                )
            else:
                self.progress.update(
                    self.progress_task,
                    description="Testing...",
                    start=True,
                    total=self.stats.total_num_tests,
                    completed=self.stats.num_tests_run,
                )

        # rederable group; members depend on what phase of test session we are in
        @group()
        def get_panels(finished: bool = False):
            if not self.stats.testing_started:
                yield self.panel_progress
            else:
                yield self.table
                yield self.panel_progress
            if self.stats.testing_complete:
                self.stats.update_stats()
                if self.stats.test_session_data and hasattr(
                    self.stats.test_session_data, "lastline_ansi"
                ):
                    last_line_ansi = self.stats.test_session_data.lastline_ansi
                else:
                    last_line_ansi = ""
                last_line = Text.from_ansi(last_line_ansi)
                yield Panel(last_line)

        return get_panels()

    def rich_client(self) -> None:
        # put thread into a loop that proceseses pytest results until they are done
        while True:
            self.stats.update_stats(init=True)

            with Live(
                self.main_panel_group(),
                vertical_overflow="visible",
                refresh_per_second=8,
            ) as live:
                while not self.stats.testing_complete:
                    # time.sleep(0.5)
                    live.update(self.main_panel_group())

                    # THIS NEEDS REFACTORING
                    if live.renderable:
                        self.progress.update(
                            0, completed=self.stats.num_tests_run, refresh=True
                        )

                    self.stats.update_stats()

                    # if self.stats.testing_complete:
                    #     for _ in range(10):
                    #         time.sleep(0.1)
                    #         if self.stats.test_session_data.lastline:
                    #             break

                # Don't stylize (show spinny progress icon) if tests are finished
                live.update(self.main_panel_group(stylize_last_line=False))

            while True:
                # the test session is finished, so we signal the kb_input
                # thread to exit, then exit ourselves
                self.stats.update_stats()
                live.update(self.main_panel_group(stylize_last_line=False))
                self.event.set()


def main():
    # CLI arguments
    parser = ArgumentParser(prog="tally")
    parser.add_argument("filename", nargs="?", help="path to data file")
    parser.add_argument(
        "-l",
        "--lines",
        action="store_true",
        default=False,
        help="draw separation [l]ines in between each table row (default: False)",
    )
    parser.add_argument(
        "-p",
        "--persist",
        action="store_true",
        default=False,
        help="persist table after tests are finished (default: False)",
    )
    parser.add_argument(
        "-x",
        "--max_rows",
        action="store",
        type=int,
        default=0,
        help="ma[x] number of rows to display (default: 0 [no limit])",
    )
    args = parser.parse_args()

    tally_app = TallyApp(args)
    clear_file(tally_app.options.filename)
    tally_app.console.clear()

    tally_app.event = Event()
    t1 = Thread(target=tally_app.rich_client)
    t2 = Thread(target=tally_app.kb_input)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


if __name__ == "__main__":
    main()
