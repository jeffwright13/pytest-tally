import logging
import os
import re
from pathlib import Path

import pytest
from _pytest.config import Config, ExitCode
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.reports import TestReport
from _pytest.runner import CallInfo
from _pytest.stash import Stash, StashKey
from _pytest.terminal import TerminalReporter
from strip_ansi import strip_ansi

from pytest_tally.classes import TallyReport, TallySession, TallyTest
from pytest_tally.utils import LocakbleJsonFileUtils

DEFAULT_FILE = Path(os.getcwd()) / "tally-data.json"
FLUSH_TIME = 0.05

pytest_tally_enabled = StashKey[bool]()
pytest_tally_json_file = StashKey[Path]()
pytest_tally_session = StashKey[TallySession]()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def check_tally_enabled(config: Config) -> bool:
    stash: Stash = config.stash
    stash["pytest_tally_enabled"] = (
        bool(config.option.tally) if hasattr(config.option, "tally") else False
    )
    return stash["pytest_tally_enabled"]


def pytest_addoption(parser) -> None:
    group = parser.getgroup("tally")
    group.addoption(
        "--tally",
        action="store_true",
        help=(
            "Enable the pytest-tally plugin. Writes live summary results data to a JSON"
            " file for consumption by a dashboard client."
        ),
    ),
    group.addoption(
        "--tally-file",
        action="store",
        default=DEFAULT_FILE,
        help=(
            "Specify the file path to write the pytest-tally data to. Defaults to"
            " tally-data.json in the current working directory."
        ),
    )


def pytest_cmdline_main(config: Config) -> None:
    # Define stash values here since this is one of the first pytest hooks to run in a sssion
    stash: Stash = config.stash
    stash["pytest_tally_enabled"] = (
        bool(config.option.tally) if hasattr(config.option, "tally") else False
    )
    if not stash["pytest_tally_enabled"]:
        return
    stash["pytest_tally_json_file"] = (
        Path(config.option.tally_file)
        if hasattr(config.option, "tally_file")
        else DEFAULT_FILE
    )

    pytest_tally_session = stash.get("pytest_tally_session", None)
    if not pytest_tally_session:
        stash["pytest_tally_session"] = TallySession(config=config)


def write_json_to_file(config: Config) -> None:
    stash: Stash = config.stash
    file_path = stash.get("pytest_tally_json_file", DEFAULT_FILE)
    os.makedirs(file_path.parent, exist_ok=True)
    session_data = stash["pytest_tally_session"].to_json()
    lock_utils = LocakbleJsonFileUtils(file_path=file_path)
    lock_utils.overwrite_json(session_data)


def pytest_sessionstart(session: Session) -> None:
    if not check_tally_enabled(session.config):
        return

    pytest_tally_session = session.config.stash["pytest_tally_session"]
    pytest_tally_session.timer.start()
    pytest_tally_session.session_started = True
    pytest_tally_session.session_duration = pytest_tally_session.timer.elapsed
    write_json_to_file(session.config)


def pytest_collection_finish(session: Session) -> None:
    if not check_tally_enabled(session.config):
        return

    pytest_tally_session = session.config.stash["pytest_tally_session"]
    pytest_tally_session.num_tests_to_run = len(session.items)
    pytest_tally_session.session_duration = pytest_tally_session.timer.elapsed
    write_json_to_file(session.config)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item: Item):
    if not check_tally_enabled(item.session.config):
        yield
        return

    tally_test = TallyTest(node_id=item.nodeid)
    tally_test.timer.reset()
    tally_test.timer.start()
    pytest_tally_session = item.session.config.stash["pytest_tally_session"]
    pytest_tally_session.tally_tests[item.nodeid] = tally_test

    if pytest_tally_session.num_tests_have_run == 0:
        write_json_to_file(item.session.config)
    pytest_tally_session.num_tests_have_run += 1
    yield


@pytest.hookimpl(trylast=True)  # do not remove!
def pytest_configure(config: Config) -> None:
    if not check_tally_enabled(config):
        # yield
        return

    assert config.pluginmanager.hasplugin("terminal")

    stash = config.stash
    pytest_tally_session = stash.get("pytest_tally_session", None)
    if not pytest_tally_session:
        stash["pytest_tally_session"] = TallySession(config=config)

    # This code exists solely to extract the single 'lastline' of the session for
    # display in the dashboard. It is a hacky way to do it, but it works.
    tr = config.pluginmanager.getplugin("terminalreporter")
    if tr is not None:
        oldwrite = tr._tw.write

        def tee_write(s, **kwargs):
            lastline_matcher = re.compile(r"^==.*in\s\d+.\d+s.*=+")
            oldwrite(s, **kwargs)
            match = re.search(lastline_matcher, s)
            if match:
                pytest_tally_session.lastline_ansi = match.string.replace(
                    "=", ""
                ).strip()
                pytest_tally_session.lastline = (
                    strip_ansi(match.string).replace("=", "").strip()
                )
                write_json_to_file(config)

        tr._tw.write = tee_write


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call: CallInfo) -> None:
    if not check_tally_enabled(item.session.config):
        yield
        return  # do we need both yield and return?

    else:
        session_config = item.session.config
        pytest_tally_session = session_config.stash["pytest_tally_session"]

        r = yield
        report = r.get_result()
        if report.when == "teardown":
            try:
                pytest_tally_session.tally_tests[item.nodeid].timer.pause()
            except KeyError:
                logger.warning(f"Could not find tally test for node ID {item.nodeid}")
                return
            pytest_tally_session.session_duration = pytest_tally_session.timer.elapsed
            write_json_to_file(item.session.config)

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
            tally_test = pytest_tally_session.tally_tests[tally_report.node_id]
            tally_test.reports[tally_report.when] = tally_report
        except KeyError:
            logger.warning(
                f"Could not find tally test for node ID {tally_report.node_id}"
            )
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


def pytest_sessionfinish(session: Session, exitstatus: ExitCode) -> None:
    # This called after whole test run finished, right before returning the exit status to the system.
    if not check_tally_enabled(session.config):
        return

    session_config = session.config
    pytest_tally_session = session_config.stash["pytest_tally_session"]

    pytest_tally_session.timer.pause()
    pytest_tally_session.session_duration = pytest_tally_session.timer.elapsed
    pytest_tally_session.session_finished = True
    write_json_to_file(session.config)
