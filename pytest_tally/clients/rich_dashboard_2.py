import os
import time
from argparse import ArgumentParser, Namespace
from pathlib import Path
from threading import Event, Thread

from blessed import Terminal
from quantiphy import Quantity, render
from rich import print
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


def get_test_session_data(filename: Path) -> TallySession:
    # retrieve updated data from json file
    lock_utils = LocakbleJsonFileUtils(file_path=filename)
    j = lock_utils.read_json()
    if j:
        return TallySession(**j, config=None)
    else:
        return TallySession(
            session_finished=False,
            session_duration=0.0,
            timer=None,
            lastline_ansi="",
            lastline="",
            tally_tests={},
            config=None,
        )


def generate_main_panel_group(
    parsed_args,
    stylize_last_line: bool = True,
) -> Group:
    # get latest data from json file
    filename = parsed_args.filename
    test_session_data = get_test_session_data(filename)

    num_tests_run = len(
        [
            test
            for test in test_session_data.tally_tests.values()
            if test["test_outcome"]
        ]
    )
    testing_started = num_tests_run > 0
    testing_complete = test_session_data.session_finished

    ### MAIN TABLE ###
    table = Table(
        highlight=True, expand=True, show_lines=parsed_args.lines, box=rounded
    )
    table.add_column("Test")
    table.add_column("Duration")
    table.add_column("Outcome")

    # accommodate optional execution flags for max rows to display ("-r"),
    num_rows = (
        len(test_session_data.tally_tests)
        if parsed_args.max_rows == 0
        else parsed_args.max_rows
    )
    tally_tests = list(test_session_data.tally_tests.values())[-num_rows:]

    # for each test result, add a row to the table with test info
    for i, test in enumerate(tally_tests):
        name = Text(test["node_id"], style="bold blue")
        duration = (
            Duration(str(test["test_duration"])) if test["test_duration"] else 0.0
        )
        outcome = Text(test["test_outcome"]) if test["test_outcome"] else Text("---")
        for key, value in OUTCOME_STYLES.items():
            if key in outcome.plain.lower():
                outcome.stylize(value)
                name.stylize(value)
                break
        else:
            outcome.stylize("bold blue")
            name.stylize("bold blue")

        # show spinny progress icon for the last line of the table,
        # unless json file indicates the session is over - this ensures
        # the final rendered table won't have the icon frozen in time
        if stylize_last_line:
            if i == len(tally_tests) - 1:
                name = Status(name)
                table.add_row(name, Status(""), outcome)
            else:
                table.add_row(name, render(duration, "s"), outcome)
        else:
            table.add_row(name, render(duration, "s"), outcome)
            # table.caption = Text.from_ansi(test_session_data.lastline_ansi)

    ### PROGRESS BAR PANEL ###
    # test_session_data = get_test_session_data(filename)
    # testing_complete = test_session_data.session_finished
    progress = Progress(expand=True)
    if not testing_started:
        progress_task = progress.add_task(
            "Waiting for tests to start...",
            start=False,
            total=len(test_session_data.tally_tests),
        )
    if testing_started:
        progress_task = (
            progress.add_task(
                "Testing Complete",
                start=True,
                total=len(test_session_data.tally_tests),
            )
            if testing_complete
            else progress.add_task(
                "Testing...",
                total=len(test_session_data.tally_tests),
            )
        )
    progress.update(progress_task, completed=num_tests_run)
    panel_progress = Panel(progress)

    ### LASTLINE PANEL ###
    last_line = Text.from_ansi(test_session_data.lastline_ansi)
    panel_last_line = Panel(last_line)

    ### CREATE RENDERABLE GROUP ###
    @group()
    def get_panels(finished: bool = False):
        if not testing_started:
            yield panel_progress
        else:
            yield table
            yield panel_progress
        if testing_complete:
            yield panel_last_line

    return get_panels()


def rich_client(parsed_args: Namespace) -> None:
    filename = (
        Path(parsed_args.filename) if parsed_args.filename else Path(DEFAULT_FILE)
    )
    assert filename.suffix == ".json", "'filename', if specified, must end in '.json'"

    # keep rendering table until all tests are finished
    while True:
        test_session_data = get_test_session_data(filename)

        with Live(
            generate_main_panel_group(parsed_args),
            vertical_overflow="visible",
            refresh_per_second=8,
        ) as live:
            # num_tests_run = len(
            #     [
            #         test
            #         for test in test_session_data.tally_tests.values()
            #         if test["test_outcome"]
            #     ]
            # )
            # testing_started = num_tests_run > 0
            testing_complete = test_session_data.session_finished

            while not testing_complete:
                time.sleep(0.1)
                live.update(generate_main_panel_group(parsed_args))

                if live._renderable._render:
                    progress = live._renderable._render[0].renderable
                    progress.update(
                        0, advance=len(live._renderable._render[1]), refresh=True
                    )

                test_session_data = get_test_session_data(filename)
                testing_complete = test_session_data.session_finished
                if testing_complete:
                    for _ in range(10):
                        time.sleep(0.1)
                        test_session_data = get_test_session_data(filename)
                        if test_session_data.lastline:
                            break

            # Don't stylize (show spinny progress icon) if tests are finished
            live.update(generate_main_panel_group(parsed_args, stylize_last_line=False))

        while True:
            # the test session is finished, so we signal the kb_input
            # thread to exit, then exit ourselves
            test_session_data = get_test_session_data(filename)
            live.update(generate_main_panel_group(parsed_args, stylize_last_line=False))
            event.set()


def kb_input(parsed_args: Namespace):
    while True:
        with term.cbreak():
            if event.is_set() and not parsed_args.persist:
                os._exit(0)
            key = term.inkey(timeout=1).lower()
            if key and key == "q":
                os._exit(0)


def main():
    global console, event, table, progress, term, test_session_data, lines, persist
    term = Terminal()
    console = Console()

    # Define CLI arguments and process them
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
        default=0,
        help="ma[x] number of rows to display (default: no limit)",
    )
    parsed_args = parser.parse_args()
    filename = (
        Path(parsed_args.filename) if parsed_args.filename else Path(DEFAULT_FILE)
    )
    assert filename.suffix == ".json", "'filename', if specified, must end in '.json'"
    parsed_args.filename = filename

    clear_file(filename)
    console.clear()

    event = Event()
    t1 = Thread(target=rich_client, args=(parsed_args,))
    t2 = Thread(target=kb_input, args=(parsed_args,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()


if __name__ == "__main__":
    main()
