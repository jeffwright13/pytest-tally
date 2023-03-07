import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from _pytest.config import Config, ExitCode
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.reports import TestReport
from _pytest.runner import CallInfo
from count_timer import CountTimer
from dataclasses_json import dataclass_json

FILE = Path("/Users/jwr003/coding/pytest-tally/pytest_tally/data.json")


@dataclass_json
@dataclass
class TallyTest:
    """Dataclass to hold pertinent info for each Pytest test executed"""

    collect: TestReport
    setup: TestReport
    call: TestReport
    teardown: TestReport
    timer: CountTimer
    final_outcome: str
    node_id: str


NULL_TALLY_TEST = TallyTest(
    collect=None,
    setup=None,
    call=None,
    teardown=None,
    timer=None,
    final_outcome=None,
    node_id=None,
)


@dataclass_json
@dataclass
class TallyTestSessionData:
    """Dataclass to hold pertinent info for the entire Pytest test session"""

    num_collected_tests: int
    start_time: str
    end_time: str
    total_duration: float
    tally_tests: dict
    session_finished: bool


NULL_TALLY_TEST_SESSION_DATA = TallyTestSessionData(
    num_collected_tests=0,
    start_time="",
    end_time="",
    total_duration=0,
    tally_tests={},
    session_finished=False,
)


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

    config._tally_timer = CountTimer()
    config._tally_timer.start()

    # A dictionary of TallyTests using nodeid as keys
    # Required to determine per-test durations and outcomes
    config._tally_tests = {}


def pytest_sessionstart(session: Session) -> None:
    if not check_tally_enabled(session.config):
        return

    session.test_session_data = NULL_TALLY_TEST_SESSION_DATA
    with open(FILE, "w", encoding="utf-8") as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)


def pytest_collection_finish(session: Session) -> None:
    if not check_tally_enabled(session.config):
        return

    session.test_session_data = NULL_TALLY_TEST_SESSION_DATA
    with open(FILE, "w") as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)

    session.test_session_data.num_collected_tests = len(session.items)
    with open(FILE, "w") as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)


def process_reports(report: TestReport, item: Item) -> None:
    if report.nodeid in item.session.config._tally_tests:
        tally_test = item.session.config._tally_tests[item.nodeid]
    else:
        tally_test = NULL_TALLY_TEST
        tally_test.node_id = item.nodeid
        tally_test.timer = CountTimer()
        tally_test.timer.start()
        item.session.config._tally_tests[item.nodeid] = tally_test

    if report.when == "collect":
        tally_test.collect = report
    elif report.when == "setup":
        tally_test.setup = report
    elif report.when == "call":
        tally_test.call = report
        tally_test.call.outcome = report.outcome
    elif report.when == "teardown":
        tally_test.teardown = report
        tally_test.timer.pause()
    else:
        raise RuntimeError(f"Unknown report 'when' value: {report.when}")


def finalize_test(item: Item) -> dict:
    tally_test = item.session.config._tally_tests[item.nodeid]
    tally_test.final_outcome = (
        tally_test.call.outcome.capitalize()
        if hasattr(tally_test.call, "outcome")
        else "Error"
    )
    for report in [
        tally_test.collect,
        tally_test.setup,
        tally_test.teardown,
    ]:
        if hasattr(report, "when") and report.when == "failed":
            tally_test.final_outcome = "Error"
    for report in [
        tally_test.collect,
        tally_test.setup,
        tally_test.call,
        tally_test.teardown,
    ]:
        if hasattr(report, "wasxfail"):
            if report.outcome in ["passed", "failed"]:
                tally_test.final_outcome = "XPassed"
            if report.outcome == "skipped":
                tally_test.final_outcome = "XFailed"
    return {
        "node_id": tally_test.node_id,
        "final_outcome": tally_test.final_outcome,
        "duration": tally_test.timer.elapsed,
    }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call: CallInfo) -> None:
    if not check_tally_enabled(item.session.config):
        yield

    else:
        # Determining the final outcome of a Pytest test is a bitch. What we are doing
        # here is gathering all TestReport items for a given test (uniquely identified
        # by nodeid), and assigning the final outcome based on some information gleaned
        # from Pytests's source code (e.g. reports.py), word-of-mouth (BeyondEvil), etc.
        # This does not take into account reruns. Fuck it, we do the best we can.
        r = yield
        report = r.get_result()

        # Push individual reports onto a dictionary of TallyTest objects, then
        # when each test has reached its end (indicated by 'when' = teardown)
        # we have enough info to finalize outcome & duration
        process_reports(report, item)

        item.session.test_session_data.total_duration = (
            item.session.config._tally_timer.elapsed
        )

        if report.when == "teardown":
            finalized_info = finalize_test(item)
            item.session.test_session_data.tally_tests[item.name] = finalized_info

        with open(FILE, "w") as file:
            jdata = item.session.test_session_data.to_json()
            json.dump(jdata, file)


def pytest_sessionfinish(session: Session, exitstatus: ExitCode) -> None:
    if not check_tally_enabled(session.config):
        return

    session.config._tally_timer.pause()

    session.test_session_data.total_duration = session.config._tally_timer.elapsed
    session.test_session_data.session_finished = True
    with open(FILE, "w") as file:
        j = session.test_session_data.to_json()
        json.dump(j, file)
