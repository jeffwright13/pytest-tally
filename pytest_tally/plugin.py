import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest
from _pytest.config import Config, ExitCode
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.runner import CallInfo
from count_timer import CountTimer
from dataclasses_json import dataclass_json

FILE = Path("/Users/jwr003/coding/pytest-tally/pytest_tally/data.json")


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
    start_time: str
    end_time: str
    total_duration: float
    reports: dict
    session_finished: bool


def check_tally_enabled(config: Config) -> bool:
    return bool(config.option.tally) if hasattr(config.option, "tally") else False


def pytest_addoption(parser) -> None:
    group = parser.getgroup("tally")
    group.addoption(
        "--tally",
        action="store_true",
        help="Enable the pytest-tally plugin. Writes live summary results data to a JSON file for comsumption by a dashboard client.",
    )


def pytest_cmdline_main(config: Config) -> None:
    if not check_tally_enabled(config):
        return

    config._tally_session_start_time = (
        datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    )
    config._tally_timer = CountTimer()
    config._tally_timer.start()


def pytest_sessionstart(session: Session) -> None:
    if not check_tally_enabled(session.config):
        return

    session.test_session_data = TestSessionData(
        num_collected_tests=0,
        start_time=None,
        end_time=None,
        total_duration=0,
        reports={},
        session_finished=False,
    )
    with open(FILE, "w", encoding="utf-8") as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)


def pytest_collection_finish(session: Session) -> None:
    if not check_tally_enabled(session.config):
        return

    session.test_session_data = TestSessionData(
        num_collected_tests=0,
        start_time=None,
        end_time=None,
        total_duration=0,
        reports={},
        session_finished=False,
    )
    with open(FILE, "w") as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)

    session.test_session_data.num_collected_tests = len(session.items)
    with open(FILE, "w") as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call: CallInfo) -> None:
    if not check_tally_enabled(item.session.config):
        yield
    else:

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
        item.session.test_session_data.total_duration = (
            item.session.config._tally_timer.elapsed
        )
        with open(FILE, "w") as file:
            j = item.session.test_session_data.to_json()
            json.dump(j, file)


def pytest_sessionfinish(session: Session, exitstatus: ExitCode) -> None:
    if not check_tally_enabled(session.config):
        return

    session.config._tally_timer.pause()

    session.test_session_data.total_duration = session.config._tally_timer.elapsed
    session.test_session_data.session_finished = True
    with open(FILE, "w") as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)


def pytest_unconfigure(config: Config) -> None:
    if not check_tally_enabled(config):
        return

    config._tally_session_end_time = (
        datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    )
    config._tally_session_duration = datetime.strptime(
        config._tally_session_end_time, "%Y-%m-%d %H:%M:%S"
    ) - datetime.strptime(config._tally_session_start_time, "%Y-%m-%d %H:%M:%S")
