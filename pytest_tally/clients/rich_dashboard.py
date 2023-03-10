import argparse
import json
import platform
import subprocess
import time

from blessed import Terminal
from quantiphy import Quantity, render
from rich.live import Live
from rich.status import Status
from rich.table import Table
from rich.text import Text


class Duration(Quantity):
    units = "s"
    prec = 2


from pytest_tally.plugin import FILE, TallySessionData
from pytest_tally.utils import human_time_duration


def clear_file() -> None:
    with open(FILE, "w") as jfile:
        jfile.write("")


def clear_terminal() -> None:
    if platform.system() == "Windows":
        subprocess.Popen("cls", shell=True).communicate()
    else:
        print("\033c", end="")


def get_test_session_data() -> TallySessionData:
    with open(FILE, "r") as jfile:
        try:
            j = json.load(jfile)
            return TallySessionData(**j)
        except json.decoder.JSONDecodeError:
            return TallySessionData(
                session_finished=False, session_duration=0.0, timer=None, tally_tests={}
            )


def generate_table(stylize_last_line: bool = True) -> Table:
    test_session_data = get_test_session_data()

    table = Table(highlight=True)
    if not table.columns:
        table.add_column("Test NodeId")
        table.add_column("Duration")
        table.add_column("Outcome")

    for i, test in enumerate(test_session_data.tally_tests):
        try:
            name = Text(
                test_session_data.tally_tests[test]["node_id"], style="bold cyan"
            )
        except AttributeError:
            continue

        if stylize_last_line:
            name = Status(name) if i == len(test_session_data.tally_tests) - 1 else name

        duration = (
            Duration(str(test_session_data.tally_tests[test]["test_duration"]))
            if test_session_data.tally_tests[test]["test_duration"]
            else 0.0
        )

        outcome = (
            Text(test_session_data.tally_tests[test]["final_outcome"])
            if test_session_data.tally_tests[test]["final_outcome"]
            else Text("---")
        )
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

        table.add_row(name, render(duration, "s"), outcome)

        if (
            hasattr(test_session_data, "session_duration")
            and test_session_data.session_duration >= 60
        ):
            table.caption = f"Test Session Duration: {human_time_duration(test_session_data.session_duration)}"
        else:
            table.caption = (
                f"Test Session Duration: {Duration(test_session_data.session_duration)}"
            )

    return table


def main():
    parser = argparse.ArgumentParser(prog="tally")
    parser.add_argument(
        "-n",
        action="store_true",
        default=False,
        help="do not delete existing data when starting a new run",
    )
    args = parser.parse_args().__dict__

    if not args["n"]:
        clear_file()

    term = Terminal()
    clear_terminal()

    while True:
        test_session_data = get_test_session_data()
        with Live(generate_table(), refresh_per_second=6) as live:
            while not test_session_data.session_finished:
                time.sleep(0.3)
                live.update(generate_table())
                test_session_data = get_test_session_data()
            live.update(generate_table(stylize_last_line=False))

        while True:
            test_session_data = get_test_session_data()
            if not test_session_data.session_finished:
                break
            time.sleep(0.25)

        clear_terminal()


if __name__ == "__main__":
    main()
