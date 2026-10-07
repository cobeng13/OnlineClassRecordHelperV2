"""Packaged startup check using synthetic values; never emits keyboard events."""
import time
from PySide6.QtCore import QLockFile, QTemporaryDir
from .app import MainWindow


def smoke_test(app):
    window = MainWindow(keyboard_enabled=False)
    try:
        window.show()
        window.text.setPlainText("90\t91\n92\t93")
        window.multi.setChecked(True)
        window.columns.setValue(2)
        window.test.setChecked(True)
        window.initial.setValue(0)
        window.delay.setValue(0)
        window.refresh_preview()
        if window.cells.rowCount() != 2 or window.actions.rowCount() != 10:
            return 1
        window.start_run()
        deadline = time.monotonic() + 5
        while window.runner is not None and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.005)
        if window.runner is not None or window.status.text() != "Test complete — no keys sent":
            return 2
        # Confirm the bundle contains the native modules, without emitting keys.
        from pynput.keyboard import Controller, GlobalHotKeys
        if Controller is None or GlobalHotKeys is None:
            return 3
        directory = QTemporaryDir()
        first = QLockFile(directory.path() + "/instance.lock")
        second = QLockFile(directory.path() + "/instance.lock")
        if not first.tryLock(0) or second.tryLock(0):
            return 4
        first.unlock()
        if not second.tryLock(0):
            return 5
        second.unlock()
        return 0
    finally:
        window.close()
