import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from threading import Event, Thread

from blessed import Terminal
from quantiphy import Quantity, render
from rich.console import Console
from rich.live import Live
from rich.status import Status
from rich.table import Table
from rich.text import Text

from pytest_tally.plugin import DEFAULT_FILE, TallySession
from pytest_tally.utils import clear_file, human_time_duration

class Duration(Quantity):
    units = "s"
    prec = 2


def get_test_session_data(filename: Path) -> TallySession:
    try:
        with open(filename, "r") as jfile:
            j = json.load(jfile)
            return TallySession(**j, config=None)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        os.makedirs(filename.parent, exist_ok=True)
        clear_file(filename)
        return TallySession(
            session_finished=False,
            session_duration=0.0,
            timer=None,
            lastline="",
            tally_tests={},
            config=None,
        )
    except Exception as e:
        raise e


def generate_table(
    filename: Path,
    max_rows: int = 0,
    width: int = 0,
    stylize_last_line: bool = True,
) -> Table:
    test_session_data = get_test_session_data(filename)

    table = Table(highlight=True, show_lines=lines)
    if not table.columns:
        table.add_column("Test")
        table.add_column("Duration")
        table.add_column("Outcome")

    num_rows = len(test_session_data.tally_tests) if max_rows == 0 else max_rows
    if width:
        table.width = width
    tally_tests = list(test_session_data.tally_tests.values())[-num_rows:]

    for i, test in enumerate(tally_tests):
        name = Text(test["node_id"], style="bold blue")

        duration = Duration(str(test["test_duration"])) if test["test_duration"] else 0.0

        outcome = Text(test["test_outcome"]) if test["test_outcome"] else Text("---")

        outcome_styles = {
            "passed": "green",
            "failed": "bold red",
            "skipped": "yellow",
            "error": "bold magenta",
            "xfail": "red",
            "xpass": "bold yellow",
            "rerun": "yellow",
        }

        for key, value in outcome_styles.items():
            if key in outcome.plain.lower():
                outcome.stylize(value)
                name.stylize(value)
                break
        else:
            outcome.stylize("bold blue")
            name.stylize("bold blue")

        if stylize_last_line:
            if i == len(tally_tests) - 1:
                name = Status(name)
                table.add_row(name, Status(""), outcome)
            else:
                table.add_row(name, render(duration, "s"), outcome)
        else:
            table.add_row(name, render(duration, "s"), outcome)
            table.caption = Text(
                f"Test Session Duration: {Duration(test_session_data.session_duration)}",
                style="bold",
            )
    return table


def kb_input():
    while True:
        with term.cbreak():
            if event.is_set() and not persist:
                os._exit(0)
            key = term.inkey(timeout=1).lower()
            if key and key == "q":
                os._exit(0)


def table_render(filename: Path, max_rows: int, width: int) -> None:
    while True:
        test_session_data = get_test_session_data(filename)
        with Live(
            generate_table(filename, max_rows, width), vertical_overflow="visible"
        ) as live:
            while not test_session_data.session_finished:
                time.sleep(0.2)
                live.update(generate_table(filename, max_rows, width))
                test_session_data = get_test_session_data(filename)
            live.update(
                generate_table(filename, max_rows, width, stylize_last_line=False)
            )

        while True:
            test_session_data = get_test_session_data(filename)
            if not test_session_data.session_finished:
                break
            time.sleep(0.5)
            event.set()


def main():
    global console, event, table, term, test_session_data, lines, persist
    term = Terminal()
    console = Console()

    # Define CLI arguments and process them
    parser = argparse.ArgumentParser(prog="tally")
    parser.add_argument("filename", nargs="?", help="path to data file")
    parser.add_argument(
        "-f",
        "--fixed-width",
        action="store_true",
        default=False,
        help="make all table rows [f]ixed-width (default: False)",
    )
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
        "-r",
        "--rows",
        action="store",
        default=0,
        help="max number of [r]ows to display (default: no limit)",
    )
    args = parser.parse_args()
    lines = args.lines
    persist = args.persist
    filename = Path(args.filename) if args.filename else Path(DEFAULT_FILE)
    assert filename.suffix == ".json", "'filename', if specified, must end in '.json'"

    clear_file(filename)
    max_rows = int(args.rows) if args.rows else 0
    width = term.width if args.filename else 0
    console.clear()

    event = Event()
    t1 = Thread(target=table_render, args=(filename, max_rows, width))
    t2 = Thread(target=kb_input)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


if __name__ == "__main__":
    asyncio.run(main())
