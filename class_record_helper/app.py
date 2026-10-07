import math
import os
import sys
import threading
from PySide6.QtCore import QObject, QLockFile, QStandardPaths, Qt, Signal, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)
from .core import Runner, Settings, parse_cells, plan_actions
from .desktop import NativeKeyboard, permission_status, start_hotkeys


class Events(QObject):
    start = Signal()
    stop = Signal()
    progress = Signal(int, object)
    countdown = Signal(float)
    finished = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self, keyboard_enabled=True):
        super().__init__()
        self.setWindowTitle("Online Class Record Helper")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(1040, 820)
        self.runner = None
        self.thread = None
        self.listener = None
        self.keyboard_enabled = keyboard_enabled
        self.events = Events()
        self.events.start.connect(self.start_run)
        self.events.stop.connect(self.stop_run)
        self.events.progress.connect(self.show_progress)
        self.events.countdown.connect(self.show_countdown)
        self.events.finished.connect(self.finish_run)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        title = QLabel("Online Class Record Helper")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)
        guidance = QLabel("1  Paste spreadsheet cells     →     2  Preview and configure     →     3  Start and focus the first web cell")
        guidance.setWordWrap(True)
        layout.addWidget(guidance)

        self.inputs = QWidget()
        input_layout = QVBoxLayout(self.inputs)
        input_layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        paste_panel = QWidget()
        paste_layout = QVBoxLayout(paste_panel)
        paste_layout.addWidget(QLabel("Spreadsheet data"))
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("Copy cells from Excel, then paste here (Ctrl+V / ⌘V).")
        paste_layout.addWidget(self.text)
        clipboard = QPushButton("From Clipboard")
        clipboard.clicked.connect(lambda: self.text.setPlainText(QApplication.clipboard().text()))
        paste_layout.addWidget(clipboard)
        splitter.addWidget(paste_panel)

        self.tabs = QTabWidget()
        self.cells = QTableWidget()
        self.actions = QTableWidget()
        for table in (self.cells, self.actions):
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
        self.tabs.addTab(self.cells, "Cell preview")
        self.tabs.addTab(self.actions, "Action preview")
        splitter.addWidget(self.tabs)
        splitter.setSizes([400, 600])
        input_layout.addWidget(splitter, 1)
        self.summary = QLabel("Paste data to see a preview.")
        input_layout.addWidget(self.summary)

        settings_box = QGroupBox("Entry settings")
        form = QFormLayout(settings_box)
        self.initial = QDoubleSpinBox()
        self.initial.setRange(0, 3600)
        self.initial.setDecimals(1)
        self.initial.setValue(3)
        self.initial.setSuffix(" s")
        self.delay = QDoubleSpinBox()
        self.delay.setRange(0, 60000)
        self.delay.setDecimals(1)
        self.delay.setValue(250)
        self.delay.setSuffix(" ms")
        self.advance = QComboBox()
        self.advance.addItems(["Enter", "Tab", "Down", "Right"])
        self.multi = QCheckBox("Multi-column mode")
        self.columns = QSpinBox()
        self.columns.setRange(1, 5)
        self.columns.setEnabled(False)
        self.skip = QCheckBox("Skip blank cells (advance without typing)")
        self.skip.setChecked(True)
        self.test = QCheckBox("Test mode — preview only, no keyboard input")
        form.addRow("Initial delay", self.initial)
        form.addRow("Key delay", self.delay)
        form.addRow("Single-column advance", self.advance)
        multi_row = QWidget()
        multi_layout = QHBoxLayout(multi_row)
        multi_layout.setContentsMargins(0, 0, 0, 0)
        multi_layout.addWidget(self.multi)
        multi_layout.addWidget(QLabel("Columns"))
        multi_layout.addWidget(self.columns)
        multi_layout.addStretch()
        form.addRow(multi_row)
        form.addRow(self.skip)
        form.addRow(self.test)
        warning = QLabel("Multi-column mode assumes Enter stays on the last student row. "
                         "Your pasted block must end there. Blank cells never clear existing grades.")
        warning.setWordWrap(True)
        form.addRow(warning)
        input_layout.addWidget(settings_box)
        layout.addWidget(self.inputs, 1)

        access_row = QHBoxLayout()
        self.access = QLabel()
        self.access.setWordWrap(True)
        access_row.addWidget(self.access, 1)
        recheck = QPushButton("Recheck access")
        recheck.clicked.connect(self.check_access)
        access_row.addWidget(recheck)
        self.recheck = recheck
        layout.addLayout(access_row)
        buttons = QHBoxLayout()
        self.start_button = QPushButton("Start (F9)")
        self.stop_button = QPushButton("Stop (F10 / Esc)")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_run)
        self.stop_button.clicked.connect(self.stop_run)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        layout.addLayout(buttons)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        layout.addWidget(self.progress_bar)
        self.status = QLabel("Ready. Mac function keys may require Fn.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(180)
        self.preview_timer.timeout.connect(self.refresh_preview)
        self.listener_timer = QTimer(self)
        self.listener_timer.setInterval(1000)
        self.listener_timer.timeout.connect(self.check_listener)
        self.listener_timer.start()
        self.text.textChanged.connect(self.queue_preview)
        for widget in (self.initial, self.delay, self.columns):
            widget.valueChanged.connect(self.queue_preview)
        self.advance.currentTextChanged.connect(self.queue_preview)
        for widget in (self.multi, self.skip, self.test):
            widget.toggled.connect(self.queue_preview)
        self.multi.toggled.connect(self.toggle_multi)
        self.check_access()

    def toggle_multi(self, enabled):
        self.columns.setEnabled(enabled)
        self.advance.setEnabled(not enabled)

    def queue_preview(self, *_):
        self.preview_timer.start()

    def settings(self):
        for spin in (self.initial, self.delay, self.columns):
            if not spin.hasAcceptableInput():
                raise ValueError("Enter valid, non-negative delays and a column count from 1–5.")
            spin.interpretText()
        return Settings(self.initial.value(), self.delay.value(), self.advance.currentText(),
                        self.skip.isChecked(), self.test.isChecked(),
                        self.multi.isChecked(), self.columns.value())

    def refresh_preview(self):
        try:
            matrix = parse_cells(self.text.toPlainText())
            settings = self.settings()
            actions = plan_actions(matrix, settings)
        except ValueError as exc:
            self.cells.setRowCount(0)
            self.actions.setRowCount(0)
            self.summary.setText(str(exc))
            return
        self.cells.setRowCount(len(matrix))
        self.cells.setColumnCount(max(map(len, matrix)))
        self.cells.setHorizontalHeaderLabels([str(i + 1) for i in range(self.cells.columnCount())])
        self.cells.clearContents()
        for r, row in enumerate(matrix):
            for c, value in enumerate(row):
                self.cells.setItem(r, c, QTableWidgetItem(value))
        self.actions.setColumnCount(4)
        self.actions.setHorizontalHeaderLabels(["Row", "Column", "Action", "Value / key"])
        self.actions.setRowCount(len(actions))
        for i, action in enumerate(actions):
            for j, value in enumerate((action.row, action.column, action.kind, action.value)):
                self.actions.setItem(i, j, QTableWidgetItem(str(value)))
        self.summary.setText(f"{len(matrix)} rows · {self.cells.columnCount()} columns · {len(actions)} actions"
                             + (f" · using {min(settings.columns, self.cells.columnCount())} columns" if settings.multi_column else ""))

    def check_access(self):
        if self.runner:
            return
        if not self.keyboard_enabled:
            self.access_ok = False
            self.access.setText("Diagnostic mode — keyboard input and global shortcuts disabled.")
            return
        self.access_ok, message = permission_status()
        if self.access_ok and self.listener is None:
            try:
                self.listener = start_hotkeys(self.events.start.emit, self.events.stop.emit)
            except Exception as exc:
                self.access_ok = False
                message = f"Global shortcuts unavailable: {exc}. Live entry is blocked; test mode is available."
        self.access.setText(message)

    def check_listener(self):
        if self.listener is not None and not self.listener.is_alive():
            self.listener = None
            self.access_ok = False
            self.access.setText("Keyboard shortcuts stopped. Live entry has been stopped. Recheck access before restarting.")
            if self.runner:
                self.stop_run()

    def start_run(self):
        if self.runner is not None:
            return
        try:
            settings = self.settings()
            actions = plan_actions(parse_cells(self.text.toPlainText()), settings)
            self.check_access()
            if not settings.test_mode and not self.access_ok:
                raise ValueError(self.access.text())
            backend = None if settings.test_mode else NativeKeyboard()
        except Exception as exc:
            QMessageBox.warning(self, "Cannot start", str(exc))
            return
        self.refresh_preview()
        self.runner = Runner(backend)
        runner = self.runner
        if backend is not None:
            backend.stop_requested = runner.cancelled.is_set
        self.inputs.setEnabled(False)
        self.recheck.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setRange(0, len(actions))
        self.progress_bar.setValue(0)

        def work():
            try:
                result = runner.run(actions, settings, self.events.progress.emit,
                                    self.events.countdown.emit)
                if result == "Done" and settings.test_mode:
                    result = "Test complete — no keys sent"
            except Exception as exc:
                result = f"Error: {exc}"
            self.events.finished.emit(result)

        self.thread = threading.Thread(target=work, name="grade-entry", daemon=False)
        self.thread.start()

    def stop_run(self):
        if self.runner:
            self.runner.stop()
            self.status.setText("Stopping…")

    def show_countdown(self, remaining):
        if self.runner and not self.runner.cancelled.is_set():
            self.status.setText(f"Starting in {math.ceil(remaining)} s — click the FIRST cell in the website.")

    def show_progress(self, index, action):
        self.progress_bar.setValue(index)
        if self.runner and not self.runner.cancelled.is_set():
            self.status.setText(f"Row {action.row}, column {action.column} · action {index}/{self.progress_bar.maximum()}")

    def finish_run(self, result):
        if self.runner and self.runner.cancelled.is_set() and not result.startswith("Error"):
            result = "Stopped"
        if self.thread:
            self.thread.join()
        self.runner = None
        self.thread = None
        self.inputs.setEnabled(True)
        self.recheck.setEnabled(True)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status.setText(result)
        if result == "Done":
            QApplication.beep()

    def closeEvent(self, event: QCloseEvent):
        self.stop_run()
        if self.thread:
            self.thread.join()
        if self.listener:
            self.listener.stop()
        event.accept()


def main():
    smoke = "--smoke-test" in sys.argv
    if smoke:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv)
    app.setApplicationName("Online Class Record Helper")
    app.setOrganizationName("OnlineClassRecordHelper")
    if smoke:
        from .diagnostics import smoke_test
        return smoke_test(app)
    lock = QLockFile(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
                     + "/online-class-record-helper-v1.lock")
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        if lock.error() == QLockFile.LockError.LockFailedError:
            QMessageBox.information(None, "Already running", "Online Class Record Helper is already open.")
            return 0
        QMessageBox.critical(None, "Cannot start", "Cannot create the instance lock in the system temporary folder. Check folder permissions.")
        return 1
    window = MainWindow()
    window.show()
    result = app.exec()
    lock.unlock()
    return result
