import json
from typing import Any, Dict

import pytest
from _pytest.pathlib import Path


def pytest_addoption(parser):
    group = parser.getgroup("terminal reporting", "report-log plugin options")
    group.addoption(
        "--report-log",
        action="store",
        metavar="path",
        default=None,
        help="Path to line-based json objects of test session events.",
    )


def pytest_configure(config):
    report_log = config.option.report_log
    if report_log and not hasattr(config, "workerinput"):
        config._report_log_plugin = ReportLogPlugin(config, Path(report_log))
        config.pluginmanager.register(config._report_log_plugin)


def pytest_unconfigure(config):
    report_log_plugin = getattr(config, "_report_log_plugin", None)
    if report_log_plugin:
        report_log_plugin.close()
        del config._report_log_plugin


class ReportLogPlugin:
    def __init__(self, config, log_path: Path):
        self._config = config
        self._log_path = log_path

        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = log_path.open("w", buffering=1, encoding="UTF-8")

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None

    def _write_json_data(self, data):
        try:
            json_data = json.dumps(data)
        except TypeError:
            data = cleanup_unserializable(data)
            json_data = json.dumps(data)
        self._file.write(json_data + "\n")
        self._file.flush()

    def pytest_sessionstart(self):
        data = {"pytest_version": pytest.__version__, "$report_type": "SessionStart"}
        self._write_json_data(data)

    def pytest_sessionfinish(self, exitstatus):
        data = {"exitstatus": exitstatus, "$report_type": "SessionFinish"}
        self._write_json_data(data)

    def pytest_runtest_logreport(self, report):
        data = self._config.hook.pytest_report_to_serializable(
            config=self._config, report=report
        )
        self._write_json_data(data)

    def pytest_collectreport(self, report):
        data = self._config.hook.pytest_report_to_serializable(
            config=self._config, report=report
        )
        self._write_json_data(data)

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.write_sep(
            "-", "generated report log file: {}".format(self._log_path)
        )


def cleanup_unserializable(d: Dict[str, Any]) -> Dict[str, Any]:
    # Credit to https://github.com/pytest-dev/pytest-reportlog
    """Return new dict with entries that are not json serializable by their str()."""
    result = {}
    for k, v in d.items():
        try:
            json.dumps({k: v})
        except TypeError:
            v = str(v)
        result[k] = v
    return result
