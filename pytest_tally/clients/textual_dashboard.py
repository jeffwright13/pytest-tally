import json
import platform
import subprocess

from blessed import Terminal
from quantiphy import Quantity, render
from rich.status import Status
from rich.table import Table
from rich.text import Text
from textual.scroll_view import ScrollView
from textual.widgets._data_table import DataTable
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header
from textual import events

from pytest_tally.plugin import FILE, TallySession
from pytest_tally.utils import human_time_duration


class Duration(Quantity):
    units = "s"
    prec = 2


class TerminalUtils:
    @staticmethod
    def clear_file() -> None:
        with open(FILE, "w") as jfile:
            jfile.write("")

    @staticmethod
    def clear_terminal() -> None:
        if platform.system() == "Windows":
            subprocess.Popen("cls", shell=True).communicate()
        else:
            print("\033c", end="")


class TallyUtils:
    @staticmethod
    def get_test_session_data() -> TallySession:
        with open(FILE, "r") as jfile:
            try:
                j = json.load(jfile)
                return TallySession(**j, config=None)
            except json.decoder.JSONDecodeError:
                return TallySession(
                    session_finished=False,
                    session_duration=0.0,
                    timer=None,
                    tally_tests={},
                    config=None,
                )


class TallyApp(App):
    TITLE = "Pytest Tally - Live Results"
    BINDINGS = [
        Binding("d", "toggle_dark", "Toggle dark mode"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def on_load(self, event: events.Load) -> None:
        """Called when the app is mounted."""
        self.test_session_data = TallyUtils.get_test_session_data()
        print()

    async def on_mount(self) -> None:
        """Called when the app is mounted."""
        # await self.generate_table()
        # self.scroll = ScrollView(
        #     self.table,
        # )
        # await self.view.dock(self.scroll)
        self.datatable = DataTable()
        await self.dock(self.datatable)


    async def generate_table(self, max_rows: int = 0, stylize_last_line: bool = True) -> Table:
        self.table = Table(highlight=True)
        if not self.table.columns:
            self.table.add_column("Test NodeId")
            self.table.add_column("Duration")
            self.table.add_column("Outcome")

        num_rows = len(self.test_session_data.tally_tests) if max_rows == 0 else max_rows
        tally_tests = list(self.test_session_data.tally_tests.values())[-num_rows:]

        for i, test in enumerate(tally_tests):
            try:
                name = Text(test["node_id"], style="bold cyan")
            except AttributeError:
                continue

            duration = (
                Duration(str(test["test_duration"])) if test["test_duration"] else 0.0
            )

            outcome = Text(test["test_outcome"]) if test["test_outcome"] else Text("---")

            if "passed" in outcome.plain.lower():
                outcome.stylize("green")
            elif "failed" in outcome.plain.lower():
                outcome.stylize("bold red")
            elif "skipped" in outcome.plain.lower():
                outcome.stylize("yellow")
            elif "error" in outcome.plain.lower():
                outcome.stylize("bold magenta")
            elif "xfail" in outcome.plain.lower():
                outcome.stylize("red")
            elif "xpass" in outcome.plain.lower():
                outcome.stylize("bold yellow")
            elif "rerun" in outcome.plain.lower():
                outcome.stylize("yellow ")
            else:
                outcome.stylize("bold blue")

            if stylize_last_line:
                name = Status(name) if i == len(tally_tests) - 1 else name
                self.table.add_row(name, Status(""), outcome) if i == len(
                    tally_tests
                ) - 1 else self.table.add_row(name, render(duration, "s"), outcome)
            else:
                self.table.add_row(name, render(duration, "s"), outcome)

            if (
                hasattr(self.test_session_data, "session_duration")
                and self.test_session_data.session_duration >= 60
            ):
                self.table.caption = Text(
                    f"Test Session Duration: {human_time_duration(self.test_session_data.session_duration)}",
                    style="bold",
                )
            else:
                self.table.caption = Text(
                    f"Test Session Duration: {Duration(self.test_session_data.session_duration)}",
                    style="bold",
                )
        return self.table

def main():
    app = TallyApp()
    app.run()


if __name__ == "__main__":
    main()
