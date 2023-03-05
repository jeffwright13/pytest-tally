import json
import time
from pathlib import Path
from typing import Dict

from dataclasses_json import dataclass_json
from quantiphy import Quantity
from rich.live import Live
from rich.progress import Progress
from rich.table import Table

from pytest_tally.plugin import FILE, TestReportDistilled, TestSessionData


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
    table = Table()
    table.add_column("Test NodeId")
    table.add_column("Duration")
    table.add_column("Outcome")

    test_session_data = get_test_session_data()

    for report in test_session_data.reports:
        table.add_row(test_session_data.reports[report]["node_id"], str(test_session_data.reports[report]["duration"]) if test_session_data.reports[report]["duration"] else "-", test_session_data.reports[report]["modified_outcome"])
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
