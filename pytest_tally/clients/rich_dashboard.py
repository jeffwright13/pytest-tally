import argparse
import json
import os
import platform
import subprocess
import time
from pathlib import Path

from blessed import Terminal
from quantiphy import Quantity, render
from rich.live import Live
from rich.status import Status
from rich.table import Table
from rich.text import Text


class Duration(Quantity):
    units = "s"
    prec = 2


from pytest_tally.plugin import DEFAULT_FILE, TallySession
from pytest_tally.utils import clear_file, human_time_duration


def clear_terminal() -> None:
    _ = subprocess.call("clear" if os.name == "posix" else "cls")

    if platform.system() == "Windows":
        subprocess.Popen("cls", shell=True).communicate()
    else:
        print("\033c", end="")


def get_test_session_data(filename: Path) -> TallySession:
    os.makedirs(filename.parent, exist_ok=True)
    try:
        with open(filename, "r") as jfile:
            j = json.load(jfile)
            return TallySession(**j, config=None)
    except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
        clear_file(filename)
        return TallySession(
            session_finished=False,
            session_duration=0.0,
            timer=None,
            tally_tests={},
            config=None,
        )
    except Exception as e:
        raise e


def generate_table(
    filename: Path, max_rows: int = 0, width: int = 0, stylize_last_line: bool = True
) -> Table:
    test_session_data = get_test_session_data(filename)

    table = Table(highlight=True)
    if not table.columns:
        table.add_column("Node::TestId")
        table.add_column("Duration")
        table.add_column("Outcome")

    num_rows = len(test_session_data.tally_tests) if max_rows == 0 else max_rows
    if width:
        table.width = width
    tally_tests = list(test_session_data.tally_tests.values())[-num_rows:]

    for i, test in enumerate(tally_tests):
        try:
            name = Text(test["node_id"], style="bold cyan")
        except AttributeError:
            continue

        duration = (
            Duration(str(test["test_duration"])) if test["test_duration"] else 0.0
        )

        outcome = Text(test["test_outcome"]) if test["test_outcome"] else Text("---")

        if "passed" in outcome.plain.lower():
            outcome.stylize("green")
        elif "failed" in outcome.plain.lower():
            outcome.stylize("bold red")
        elif "skipped" in outcome.plain.lower():
            outcome.stylize("yellow")
        elif "error" in outcome.plain.lower():
            outcome.stylize("bold magenta")
        elif "xfail" in outcome.plain.lower():
            outcome.stylize("red")
        elif "xpass" in outcome.plain.lower():
            outcome.stylize("bold yellow")
        elif "rerun" in outcome.plain.lower():
            outcome.stylize("yellow ")
        else:
            outcome.stylize("bold blue")

        if stylize_last_line:
            name = Status(name) if i == len(tally_tests) - 1 else name
            table.add_row(name, Status(""), outcome) if i == len(
                tally_tests
            ) - 1 else table.add_row(name, render(duration, "s"), outcome)
        else:
            table.add_row(name, render(duration, "s"), outcome)

        if (
            hasattr(test_session_data, "session_duration")
            and test_session_data.session_duration >= 60
        ):
            table.caption = Text(
                f"Test Session Duration: {human_time_duration(test_session_data.session_duration)}",
                style="bold",
            )
        else:
            table.caption = Text(
                f"Test Session Duration: {Duration(test_session_data.session_duration)}",
                style="bold",
            )

    return table


def client(filename: Path, num_rows: int, width: int) -> None:
    while True:
        test_session_data = get_test_session_data(filename)
        with Live(
            generate_table(filename, num_rows, width), refresh_per_second=3
        ) as live:
            while not test_session_data.session_finished:
                time.sleep(0.2)
                live.update(generate_table(filename, num_rows, width))
                test_session_data = get_test_session_data(filename)
            live.update(
                generate_table(filename, num_rows, width, stylize_last_line=False)
            )

        while True:
            test_session_data = get_test_session_data(filename)
            if not test_session_data.session_finished:
                break
            time.sleep(0.6)


def main():
    term = Terminal()

    parser = argparse.ArgumentParser(prog="tally")
    parser.add_argument("filename", nargs="?", help="path to data file")
    parser.add_argument(
        "-c",
        "--clear",
        action="store_true",
        default=False,
        help="[c]lear existing data when starting a new run (default: False)",
    )
    parser.add_argument(
        "-f",
        "--fixed-width",
        action="store_true",
        default=False,
        help="make all table rows [f]ixed-width (default: False)",
    )
    parser.add_argument(
        "-r",
        "--rows",
        action="store",
        default=0,
        help="max number of [r]ows to display (default: no limit)",
    )

    args = parser.parse_args()
    filename = Path(args.filename) if args.filename else Path(DEFAULT_FILE)
    assert filename.suffix == ".json", "'filename', if specified, must end in '.json'"

    if args.clear:
        clear_file(filename)
    num_rows = int(args.rows) if args.rows else 0
    width = term.width if args.filename else 0
    clear_terminal()
    client(filename=filename, num_rows=num_rows, width=width)


if __name__ == "__main__":
    main()
