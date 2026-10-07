import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
import unittest
from unittest.mock import patch, Mock
try:
    from PySide6.QtWidgets import QApplication
    from class_record_helper.app import MainWindow
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, 'Install GUI dependencies to run UI tests')
class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.patches = [patch('class_record_helper.app.permission_status', return_value=(True, 'Ready')),
                        patch('class_record_helper.app.start_hotkeys', return_value=Mock())]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        self.window = MainWindow()
        self.addCleanup(self.window.close)

    def settle(self):
        deadline = time.monotonic() + 3
        while self.window.runner is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.app.processEvents()
        self.assertIsNone(self.window.runner)

    def test_defaults_and_clipboard_preview(self):
        self.assertEqual(self.window.initial.value(), 3)
        self.assertEqual(self.window.delay.value(), 250)
        self.assertTrue(self.window.skip.isChecked())
        self.assertFalse(self.window.test.isChecked())
        self.assertFalse(self.window.multi.isChecked())
        self.app.clipboard().setText('90\t91\n92\t93')
        from PySide6.QtWidgets import QPushButton
        next(b for b in self.window.findChildren(QPushButton) if b.text() == 'From Clipboard').click()
        self.window.refresh_preview()
        self.assertEqual(self.window.cells.rowCount(), 2)
        self.assertEqual(self.window.cells.item(1, 1).text(), '93')
        self.assertEqual(self.window.actions.rowCount(), 8)

    def test_test_mode_works_without_permissions_and_never_creates_keyboard(self):
        with (patch('class_record_helper.app.permission_status', return_value=(False, 'Permission needed')),
              patch('class_record_helper.app.NativeKeyboard') as keyboard):
            self.window.text.setPlainText('90\t91\n92\t93')
            self.window.initial.setValue(0)
            self.window.delay.setValue(0)
            self.window.multi.setChecked(True)
            self.window.columns.setValue(2)
            self.window.test.setChecked(True)
            self.window.start_run()
            runner = self.window.runner
            self.window.start_run()
            self.assertIs(self.window.runner, runner)
            self.assertFalse(self.window.inputs.isEnabled())
            self.settle()
            keyboard.assert_not_called()
            self.assertTrue(self.window.inputs.isEnabled())
            self.assertEqual(self.window.status.text(), 'Test complete — no keys sent')

    def test_stop_countdown(self):
        self.window.text.setPlainText('90')
        self.window.test.setChecked(True)
        self.window.start_run()
        self.window.stop_run()
        self.settle()
        self.assertEqual(self.window.status.text(), 'Stopped')
        self.assertEqual(self.window.progress_bar.value(), 0)

    def test_permission_blocks_live_run(self):
        self.window.text.setPlainText('90')
        with (patch('class_record_helper.app.permission_status', return_value=(False, 'Permission needed')),
              patch('class_record_helper.app.QMessageBox.warning') as warning,
              patch('class_record_helper.app.NativeKeyboard') as keyboard):
            self.window.start_run()
            warning.assert_called_once()
            keyboard.assert_not_called()
            self.assertIsNone(self.window.runner)

    def test_empty_input_warns(self):
        with patch('class_record_helper.app.QMessageBox.warning') as warning:
            self.window.start_run()
            warning.assert_called_once()
            self.assertIsNone(self.window.runner)

    def test_worker_errors_restore_controls(self):
        self.window.text.setPlainText('90')
        self.window.initial.setValue(0)
        self.window.delay.setValue(0)
        with patch('class_record_helper.app.NativeKeyboard') as keyboard:
            keyboard.return_value.type_text.side_effect = RuntimeError('Device unavailable')
            self.window.start_run()
            self.settle()
            self.assertIn('Device unavailable', self.window.status.text())
            self.assertTrue(self.window.start_button.isEnabled())


if __name__ == '__main__':
    unittest.main()
