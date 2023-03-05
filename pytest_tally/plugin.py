import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest
from _pytest._io.terminalwriter import TerminalWriter
from _pytest.config import Config, create_terminal_writer
from _pytest.nodes import Item
from _pytest.reports import TestReport
from dataclasses_json import dataclass_json
from rich.live import Live
from rich.progress import Progress
from rich.table import Table

FILE = Path("/Users/jwr003/coding/pytest-tally/pytest_tally/data.json")

from dataclasses import dataclass


@dataclass_json
@dataclass
class TestReportDistilled:
    duration: float
    modified_outcome: str
    node_id: str


@dataclass_json
@dataclass
class TestSessionData:
    num_collected_tests: int
    total_duration: float
    reports: dict
    session_finished: bool


# @pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_sessionstart(session):
    session.test_session_data = TestSessionData(
        total_duration=0, num_collected_tests=0, reports={}, session_finished=False
    )
    with open(FILE, "w", encoding='utf-8') as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)


# @pytest.hookimpl(hookwrapper=True)
def pytest_collection_finish(session):
    session.test_session_data = TestSessionData(
        total_duration=0, num_collected_tests=0, reports={}, session_finished=False
    )
    with open(FILE, "w") as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)


    session.test_session_data.num_collected_tests = len(session.items)
    with open(FILE, "w") as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    def _process_outcome(report):
        if report.when in ["setup", "teardown"] and report.outcome == "failed":
            return "Error"
        if hasattr(report, "wasxfail"):
            if report.outcome in ["passed", "failed"]:
                return "XPassed"
            if report.outcome == "skipped":
                return "XFailed"
        return report.outcome.capitalize()

    outcome = yield
    report = outcome.get_result()
    modified_outcome = _process_outcome(report)
    distilled = TestReportDistilled(
        duration=report.duration,
        modified_outcome=modified_outcome,
        node_id=report.nodeid,
    )
    item.session.test_session_data.reports[item.name] = distilled
    with open(FILE, "w") as file:
        j = item.session.test_session_data.to_json()
        json.dump(j, file)


# @pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish(session, exitstatus):
    session.test_session_data.total_duration = sum([session.test_session_data.reports[report].duration for report in session.test_session_data.reports])
    # session.test_session_data.total_duration = session.duration
    session.test_session_data.session_finished = True
    with open(FILE, "w") as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)
