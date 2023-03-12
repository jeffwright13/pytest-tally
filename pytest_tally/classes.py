from dataclasses import dataclass

from _pytest.config import Config
from count_timer import CountTimer


class TallyCountTimer(CountTimer):
    """
    Overriding CountTimer to add a to_json method. For tis module all we care
    about is duration, and if the counter is running or not.
    """

    def __init__(self, duration=0):
        super().__init__(duration)

    def to_json(self):
        return {
            "elapsed": self.elapsed,
            "running": self.running,
        }


class TallySession:
    """
    Class to hold pertinent info for the entire Pytest test session.
    A test session is made up of one or more tests.
    """

    def __init__(
        self,
        config: Config,
        session_finished: bool = False,
        session_duration: float = 0.0,
        timer: TallyCountTimer = TallyCountTimer(),
        tally_tests: dict = {},
    ) -> None:
        self.session_finished = session_finished
        self.session_duration = session_duration
        self.timer = timer
        self.tally_tests = tally_tests
        self.config = config

    def to_json(self):
        return {
            "session_finished": self.session_finished,
            "session_duration": self.session_duration,
            "timer": self.timer.to_json(),
            "tally_tests": {k: v.to_json() for k, v in self.tally_tests.items()},
        }


class TallyTest:
    """
    Class to hold pertinent info for each Pytest test executed.
    A test is made up of one or more test reports, usually one each
    corresponding to setup, call and teardown phases of the test.
    """

    def __init__(
        self,
        node_id: str = None,
        test_duration: float = 0.0,
        timer: TallyCountTimer = TallyCountTimer(),
        test_outcome: str = None,
        reports: dict = {},
    ) -> None:
        self.node_id = node_id
        self.test_duration = test_duration
        self.timer = timer
        self.test_outcome = test_outcome
        self.reports = reports

    def to_json(self):
        return {
            "node_id": self.node_id,
            "test_duration": self.test_duration,
            "test_outcome": self.test_outcome,
            "timer": self.timer.to_json(),
            "reports": {k: v.to_json() for k, v in self.reports.items()},
        }


class TallyReport:
    """
    Class to hold pertinent info for individual Pytest TestReport items.
    """

    def __init__(
        self,
        node_id: str = None,
        when: str = None,
        outcome: str = None,
    ) -> None:
        self.node_id = node_id
        self.when = when
        self.outcome = outcome

    def to_json(self):
        return {
            "node_id": self.node_id,
            "when": self.when,
            "outcome": self.outcome,
        }
