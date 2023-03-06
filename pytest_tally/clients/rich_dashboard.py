import json
import time

from quantiphy import Quantity, render
from rich.live import Live
from rich.table import Table
from rich.text import Text


class Duration(Quantity):
    units = "s"
    prec = 3


from pytest_tally.plugin import FILE, TestSessionData


def get_test_session_data() -> TestSessionData:
    try:
        with open(FILE, "r") as jfile:
            try:
                j = json.load(jfile)
            except json.decoder.JSONDecodeError:
                # print("JSON decode error encountered during get_test_session_data() - returning null test_session_data.")
                return TestSessionData(
                    num_collected_tests=0,
                    total_duration=0,
                    reports={},
                    session_finished=False,
                )
        test_session_data = TestSessionData.from_json(j)
        return test_session_data
    except (FileNotFoundError, EOFError):
        print("File not found error encountered during get_test_session_data() - returning null test_session_data.")
        return TestSessionData(
            num_collected_tests=0,
            total_duration=0,
            reports={},
            session_finished=False,
        )


def generate_table() -> Table:
    table = Table(highlight=True)
    table.add_column("Test NodeId")
    table.add_column("Duration")
    table.add_column("Outcome")

    test_session_data = get_test_session_data()

    for report in test_session_data.reports:
        name = Text(test_session_data.reports[report]["node_id"], style="bold cyan")
        duration = Duration(str(test_session_data.reports[report]["duration"])) if test_session_data.reports[report]["duration"] else "-"
        outcome = Text(test_session_data.reports[report]["modified_outcome"])
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

        table.add_row(name, render(duration, 's'), outcome)
    return table


def main():
    table = generate_table()
    while True:
        # print("True loop 1")
        test_session_data = get_test_session_data()
        with Live(generate_table(), refresh_per_second=4) as live:
            while not test_session_data.session_finished:
                # print("True loop 2")
                time.sleep(0.4)
                live.update(generate_table())
                test_session_data = get_test_session_data()

        while True:
            # print("True loop 3")
            test_session_data = get_test_session_data()
            if not test_session_data.session_finished:
                break
            time.sleep(2)

if __name__ == "__main__":
    main()
