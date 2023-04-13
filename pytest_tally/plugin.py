import json
import logging
import os
from pathlib import Path

import pytest
from _pytest.config import Config, ExitCode
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.reports import TestReport
from _pytest.runner import CallInfo

from pytest_tally.classes import TallyReport, TallySession, TallyTest

DEFAULT_FILE = Path(os.getcwd()) / "data.json"

global_config = None

logger = logging.getLogger(__name__)


def check_tally_enabled(config: Config) -> bool:
    return bool(config.option.tally) if hasattr(config.option, "tally") else False


def get_data_file() -> Path:
    global global_config
    return (
        Path(global_config.option.tally_file)
        if hasattr(global_config.option, "tally_file")
        else DEFAULT_FILE
    )


def pytest_addoption(parser) -> None:
    group = parser.getgroup("tally")
    group.addoption(
        "--tally",
        action="store_true",
        help=(
            "Enable the pytest-tally plugin. Writes live summary results data to a JSON"
            " file for comsumption by a dashboard client."
        ),
    ),
    group.addoption(
        "--tally-file",
        action="store",
        default=DEFAULT_FILE,
        help=(
            "Specify the file path to write the pytest-tally data to. Defaults to"
            " data.json in the current working directory."
        ),
    )


def pytest_cmdline_main(config: Config) -> None:
    if not check_tally_enabled(config):
        return

    global global_config
    global_config = config

    if not hasattr(global_config, "_tally_session"):
        global_config._tally_session = TallySession(
            config=config,
        )


def write_to_file(session: Session, filename: Path) -> None:
    global global_config
    global_config = session.config

    session_data = global_config._tally_session.to_json()
    os.makedirs(filename.parent, exist_ok=True)
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(session_data, file)


def pytest_sessionstart(session: Session) -> None:
    if not check_tally_enabled(session.config):
        return

    global global_config
    global_config = session.config

    global_config._tally_session.timer.start()
    global_config._tally_session.session_duration = (
        global_config._tally_session.timer.elapsed
    )
    write_to_file(session, get_data_file())


def pytest_collection_finish(session: Session) -> None:
    if not check_tally_enabled(session.config):
        return

    global_config._tally_session.session_duration = (
        global_config._tally_session.timer.elapsed
    )
    write_to_file(session, get_data_file())


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item: Item):
    yield

    if not check_tally_enabled(item.session.config):
        return

    global global_config
    global_config = item.session.config

    tally_test = TallyTest(node_id=item.nodeid)
    tally_test.timer.reset()
    tally_test.timer.start()
    global_config._tally_session.tally_tests[item.nodeid] = tally_test


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_logreport(report: TestReport) -> None:
    yield

    if not global_config:
        return

    if report.when in ("setup", "teardown") and report.outcome == "failed":
        outcome = "error"
    elif hasattr(report, "wasxfail"):
        if report.outcome in ("passed", "failed"):
            outcome = "xpassed"
        elif report.outcome == "skipped":
            outcome = "xfailed"
    else:
        outcome = report.outcome

    tally_report = TallyReport(
        node_id=report.nodeid,
        when=report.when,
        outcome=report.outcome,
    )
    try:
        tally_test = global_config._tally_session.tally_tests[tally_report.node_id]
        tally_test.reports[tally_report.when] = tally_report
    except KeyError:
        logger.warning(f"Could not find tally test for node ID {tally_report.node_id}")
        return

    if tally_test.test_outcome:
        tally_test.timer.pause()
        tally_test.test_duration = tally_test.timer.elapsed
        return

    if tally_report.when == "setup" and outcome in ["error", "skipped"]:
        tally_test.timer.pause()
        tally_test.test_duration = tally_test.timer.elapsed
        tally_test.test_outcome = outcome.capitalize()
        return

    if tally_report.when == "call":
        tally_test.test_outcome = outcome.capitalize()
        return


@pytest.hookimpl(trylast=True)
def pytest_configure(config: Config) -> None:
    if not check_tally_enabled(config):
        return

    global global_config
    global_config = config

    if not hasattr(config, "_tally_session"):
        global_config._tally_session = TallySession(
            config=config,
        )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call: CallInfo) -> None:
    if not check_tally_enabled(item.session.config):
        yield

    else:
        global global_config
        global_config = item.session.config

        r = yield
        report = r.get_result()
        if report.when == "teardown":
            try:
                global_config._tally_session.tally_tests[item.nodeid].timer.pause()
            except KeyError:
                logger.warning(f"Could not find tally test for node ID {item.nodeid}")
                return
        global_config._tally_session.session_duration = (
            global_config._tally_session.timer.elapsed
        )
        write_to_file(item.session, get_data_file())


@pytest.hookimpl(
    tryfirst=True
)  # run our hookimpl before pytest-html does its own postprocessing
def pytest_sessionfinish(session: Session, exitstatus: ExitCode) -> None:
    if not check_tally_enabled(session.config):
        return

    global global_config
    global_config = session.config

    global_config._tally_session.timer.pause()
    global_config._tally_session.session_duration = (
        global_config._tally_session.timer.elapsed
    )
    global_config._tally_session.session_finished = True

    write_to_file(session, get_data_file())
