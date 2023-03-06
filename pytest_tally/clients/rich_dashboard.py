import json
import platform
import subprocess
import time

from quantiphy import Quantity, render
from rich.live import Live
from rich.table import Table
from rich.text import Text

from blessed import Terminal


class Duration(Quantity):
    units = "s"
    prec = 2


from pytest_tally.plugin import FILE, TallyTestSessionData, NULL_TALLY_TEST_SESSION_DATA
from pytest_tally.utils import human_time_duration


def clear_file() -> None:
    with open(FILE, "w") as jfile:
        jfile.write("")


def clear_terminal() -> None:
    if platform.system() == "Windows":
        subprocess.Popen("cls", shell=True).communicate()
    else:
        print("\033c", end="")


def get_test_session_data() -> TallyTestSessionData:
    try:
        with open(FILE, "r") as jfile:
            try:
                j = json.load(jfile)
            except json.decoder.JSONDecodeError:
                return NULL_TALLY_TEST_SESSION_DATA
        return TallyTestSessionData.from_json(j)

    except (FileNotFoundError, EOFError):
        print(
            "File not found error encountered during get_test_session_data() - returning null test_session_data."
        )
        return NULL_TALLY_TEST_SESSION_DATA


def generate_table() -> Table:
    test_session_data = get_test_session_data()

    table = Table(highlight=True)
    table.add_column("Test NodeId")
    table.add_column("Duration")
    table.add_column("Outcome")

    for test in test_session_data.tally_tests:
        name = Text(test_session_data.tally_tests[test]["node_id"], style="bold cyan")
        duration = (
            Duration(str(test_session_data.tally_tests[test]["duration"]))
            if test_session_data.tally_tests[test]["duration"]
            else "-"
        )
        outcome = Text(test_session_data.tally_tests[test]["final_outcome"])
        if "passed" in outcome.plain.lower():
            outcome.stylize("green")
        elif "failed" in outcome.plain.lower():
            outcome.stylize("red")
        elif "skipped" in outcome.plain.lower():
            outcome.stylize("yellow")
        elif "error" in outcome.plain.lower():
            outcome.stylize("magenta")
        else:
            outcome.stylize("blue")
        table.add_row(name, render(duration, "s"), outcome)

        if test_session_data.total_duration >= 60:
            table.caption = f"Test Session Duration: {human_time_duration(test_session_data.total_duration)}"
        else:
            table.caption = f"Test Session Duration: {Duration(test_session_data.total_duration)}"

    return table


def main():
    clear_file()
    term = Terminal()
    clear_terminal()

    while True:
        test_session_data = get_test_session_data()
        with Live(generate_table(), refresh_per_second=4) as live:
            while not test_session_data.session_finished:
                time.sleep(0.4)
                live.update(generate_table())
                test_session_data = get_test_session_data()

        while True:
            test_session_data = get_test_session_data()
            if not test_session_data.session_finished:
                break
            time.sleep(0.25)

        clear_terminal()


if __name__ == "__main__":
    main()
