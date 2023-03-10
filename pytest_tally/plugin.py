import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest
from _pytest.config import Config, ExitCode
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.runner import CallInfo
from count_timer import CountTimer
from dataclasses_json import dataclass_json

from pytest_tally.utils import (
    lastline_matcher,
    test_session_starts_section_matcher,
    test_session_starts_test_matcher,
)

FILE = Path("/Users/jwr003/coding/pytest-tally/pytest_tally/data.json")


@dataclass_json
@dataclass
class TallyTest:
    """Dataclass to hold pertinent info for each Pytest test executed"""

    node_id: str
    test_duration: float
    final_outcome: str
    timer: CountTimer


@dataclass_json
@dataclass
class TallySessionData:
    """Dataclass to hold pertinent info for the entire Pytest test session"""

    session_finished: bool
    session_duration: float
    outcome_next: bool
    timer: CountTimer
    tally_tests: dict


def check_tally_enabled(config: Config) -> bool:
    return bool(config.option.tally) if hasattr(config.option, "tally") else False


def pytest_addoption(parser) -> None:
    group = parser.getgroup("tally")
    group.addoption(
        "--tally",
        action="store_true",
        help="Enable the pytest-tally plugin. Writes live summary results data to a JSON file for comsumption by a dashboard client.",
    )
    group.addoption(
        "--tally-file",
        "--tf",
        help="Specify a non-default name for the output file. Default is 'data.json'.",
    )


def pytest_cmdline_main(config: Config) -> None:
    if not check_tally_enabled(config):
        return

    config.option.verbose = 1
    config.option.reportchars = "AR" if hasattr(config.option, "reruns") else "A"

    config._tally_session_timer = CountTimer()
    config._tally_session_timer.start()
    config._tally_session_data = TallySessionData(
        session_finished=False,
        session_duration=0,
        outcome_next=False,
        timer=config._tally_session_timer,
        tally_tests={},
    )

    if not hasattr(config, "_tally_session_current_section"):
        config._tally_session_current_section = None

    if not hasattr(config, "_tally_session_test_outcome_next"):
        config._tally_session_test_outcome_next = False


def pytest_sessionstart(session: Session) -> None:
    if not check_tally_enabled(session.config):
        return

    session.config._tally_session_data.timer.start()

    session_data = json.dumps(
        session.config._tally_session_data, default=lambda x: x.__dict__
    )
    with open(FILE, "w", encoding="utf-8") as file:
        json.dump(session_data, file)


def pytest_collection_finish(session: Session) -> None:
    if not check_tally_enabled(session.config):
        return

    session_data = json.dumps(
        session.config._tally_session_data, default=lambda x: x.__dict__
    )
    with open(FILE, "w", encoding="utf-8") as file:
        json.dump(session_data, file)


def pytest_runtest_setup(item: Item):
    test = TallyTest(
        node_id=item.nodeid, test_duration=0.0, timer=CountTimer(), final_outcome=None
    )
    test.timer.start()
    item.config._tally_session_data.tally_tests[item.nodeid] = test
    print()


@pytest.hookimpl(trylast=True)
def pytest_configure(config: Config) -> None:
    if not check_tally_enabled(config):
        return

    tr = config.pluginmanager.getplugin("terminalreporter")
    if tr is not None:
        oldwrite = tr._tw.write

        def tee_write(s, **kwargs):
            if re.search(test_session_starts_section_matcher, s):
                config._tally_session_current_section = "test_session_starts"

            if re.search(lastline_matcher, s):
                config._tally_session_current_section = "lastline"

            if config._tally_session_current_section == "test_session_starts":
                if config._tally_session_test_outcome_next:
                    outcome = s.strip()

                    if not config._tally_session_data.tally_tests.get(
                        config._tally_session_current_fqtn
                    ):
                        tally_test = TallyTest(
                            node_id=config._tally_session_current_fqtn,
                            test_duration=0.0,
                            timer=CountTimer(),
                            final_outcome=None,
                        )
                        tally_test.timer.start()
                        config._tally_session_data.tally_tests[
                            config._tally_session_current_fqtn
                        ] = tally_test

                    tally_test = config._tally_session_data.tally_tests[
                        config._tally_session_current_fqtn
                    ]
                    tally_test.final_outcome = outcome
                    tally_test.timer.pause()
                    tally_test.test_duration = tally_test.timer.elapsed
                    config._tally_session_data.tally_tests[
                        config._tally_session_current_fqtn
                    ] = tally_test
                    config._tally_session_test_outcome_next = False

                match = re.search(test_session_starts_test_matcher, s, re.MULTILINE)
                if match:
                    node_id = re.search(
                        test_session_starts_test_matcher, s, re.MULTILINE
                    )[1].rstrip()
                    config._tally_session_current_fqtn = node_id
                    config._tally_session_test_outcome_next = True

            oldwrite(s, **kwargs)

        tr._tw.write = tee_write


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call: CallInfo) -> None:
    if not check_tally_enabled(item.session.config):
        yield

    else:
        r = yield
        report = r.get_result()

        if report.when == "teardown":
            try:
                item.session.config._tally_session_data.tally_tests[
                    item.nodeid
                ].timer.pause()
            except:
                print()

        session_data = json.dumps(
            item.session.config._tally_session_data,
            default=lambda x: x.__dict__,
        )
        with open(FILE, "w", encoding="utf-8") as file:
            json.dump(session_data, file)


def pytest_sessionfinish(session: Session, exitstatus: ExitCode) -> None:
    if not check_tally_enabled(session.config):
        return

    session.config._tally_session_timer.pause()
    session.config._tally_session_data.session_duration = (
        session.config._tally_session_timer.elapsed
    )
    session.config._tally_session_data.session_finished = True
    del session.config._tally_session_data.outcome_next

    session_data = json.dumps(
        session.config._tally_session_data, default=lambda x: x.__dict__
    )
    with open(FILE, "w", encoding="utf-8") as file:
        json.dump(session_data, file)
