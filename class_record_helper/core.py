"""Pure parsing/planning and interruptible execution; no desktop dependencies."""
from dataclasses import dataclass
import math
import threading
import time
from typing import Callable, Protocol


@dataclass(frozen=True)
class Settings:
    initial_delay: float = 3
    key_delay_ms: float = 250
    advance: str = "Enter"
    skip_blanks: bool = True
    test_mode: bool = False
    multi_column: bool = False
    columns: int = 1

    def validate(self):
        for value, name in ((self.initial_delay, "Initial delay"),
                            (self.key_delay_ms, "Key delay")):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be a finite, non-negative number.")
        if self.advance not in {"Enter", "Tab", "Down", "Right"}:
            raise ValueError("Unsupported advance key.")
        if self.columns not in range(1, 6):
            raise ValueError("Choose between 1 and 5 columns.")


@dataclass(frozen=True)
class Action:
    kind: str
    value: str
    row: int
    column: int
    delay: float


def parse_cells(text: str) -> list[list[str]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    if not text.strip():
        raise ValueError("Paste some spreadsheet data first.")
    return [[cell.strip() for cell in row.split("\t")] for row in text.split("\n")]


def plan_actions(matrix: list[list[str]], settings: Settings) -> list[Action]:
    settings.validate()
    if not matrix or not any(matrix):
        raise ValueError("No cells to type.")
    delay = settings.key_delay_ms / 1000
    actions: list[Action] = []

    def cell(value, row, column, advance):
        if value or not settings.skip_blanks:
            actions.append(Action("text", value, row, column, delay))
        actions.append(Action("key", advance, row, column, delay))

    if not settings.multi_column:
        for r, row in enumerate(matrix, 1):
            for c, value in enumerate(row, 1):
                cell(value, r, c, settings.advance)
    else:
        columns = min(settings.columns, max(map(len, matrix)))
        for c in range(columns):
            if c:
                actions.append(Action("key", "Right", len(matrix), c + 1, delay))
                for r in range(len(matrix) - 1, 0, -1):
                    actions.append(Action("key", "Up", r, c + 1, delay))
            for r, row in enumerate(matrix, 1):
                cell(row[c] if c < len(row) else "", r, c + 1, "Enter")
    return actions


class KeyboardBackend(Protocol):
    def type_text(self, text: str): ...
    def press_key(self, key: str): ...


class Runner:
    """One run per instance. Stop and keyboard emission share a synchronization gate."""
    def __init__(self, backend: KeyboardBackend | None):
        self.backend = backend
        self.cancelled = threading.Event()
        self._gate = threading.Lock()

    def stop(self):
        self.cancelled.set()
        with self._gate:
            pass  # Wait for any in-flight emission to finish before returning.

    def run(self, actions: list[Action], settings: Settings,
            progress: Callable[[int, Action], None] = lambda *_: None,
            countdown: Callable[[float], None] = lambda *_: None) -> str:
        settings.validate()
        deadline = time.monotonic() + settings.initial_delay
        while True:
            remaining = deadline - time.monotonic()
            if self.cancelled.is_set():
                return "Stopped"
            if remaining <= 0:
                break
            countdown(remaining)
            if self.cancelled.wait(min(remaining, 0.1)):
                return "Stopped"
        for index, action in enumerate(actions, 1):
            with self._gate:
                if self.cancelled.is_set():
                    return "Stopped"
                if not settings.test_mode:
                    if self.backend is None:
                        raise RuntimeError("Keyboard backend is unavailable.")
                    if action.kind == "text":
                        self.backend.type_text(action.value)
                    else:
                        self.backend.press_key(action.value)
            progress(index, action)
            if self.cancelled.wait(action.delay):
                return "Stopped"
        with self._gate:
            return "Stopped" if self.cancelled.is_set() else "Done"
