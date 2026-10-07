import sys
import types
import unittest
from unittest.mock import patch
from class_record_helper.desktop import permission_status, NativeKeyboard, start_hotkeys


class PermissionsTests(unittest.TestCase):
    def test_windows(self):
        with patch('class_record_helper.desktop.sys.platform', 'win32'):
            self.assertTrue(permission_status()[0])

    def test_mac_permissions(self):
        for trusted, listen, post in ((True, True, True), (False, True, True),
                                       (True, False, True), (True, True, False)):
            with self.subTest(trusted=trusted, listen=listen, post=post):
                modules = {
                    'Quartz': types.SimpleNamespace(CGPreflightListenEventAccess=lambda: listen,
                                                   CGPreflightPostEventAccess=lambda: post),
                    'ApplicationServices': types.SimpleNamespace(AXIsProcessTrusted=lambda: trusted),
                }
                with patch('class_record_helper.desktop.sys.platform', 'darwin'), patch.dict(sys.modules, modules):
                    ready, message = permission_status()
                    self.assertEqual(ready, trusted and listen and post)
                    if not ready:
                        self.assertIn('Accessibility', message)
                        self.assertIn('Input Monitoring', message)

    def test_permission_error_blocks_live_mode(self):
        with patch('class_record_helper.desktop.sys.platform', 'darwin'), patch.dict(sys.modules, {'Quartz': None}):
            self.assertFalse(permission_status()[0])

    def test_native_unicode_and_cancellation(self):
        from unittest.mock import Mock
        controller = Mock()
        controller.type.side_effect = lambda _: setattr(controller, 'cancelled', True)
        controller.cancelled = False
        module = types.SimpleNamespace(Controller=lambda: controller,
                                       Key=types.SimpleNamespace(**{k: k for k in ('enter', 'tab', 'down', 'right', 'up')}))
        with patch.dict(sys.modules, {'pynput.keyboard': module}):
            keyboard = NativeKeyboard(lambda: controller.cancelled)
            keyboard.type_text('é漢')
            controller.type.assert_called_once_with('é')
            keyboard.press_key('Enter')
            controller.press.assert_called_once_with('enter')
            controller.release.assert_called_once_with('enter')

    def test_hotkeys_and_startup_failure(self):
        from unittest.mock import Mock
        listener = Mock()
        factory = Mock(return_value=listener)
        module = types.SimpleNamespace(GlobalHotKeys=factory)
        on_start, on_stop = Mock(), Mock()
        with patch.dict(sys.modules, {'pynput.keyboard': module}):
            self.assertIs(start_hotkeys(on_start, on_stop), listener)
            callbacks = factory.call_args.args[0]
            callbacks['<f9>']()
            callbacks['<f10>']()
            callbacks['<esc>']()
            on_start.assert_called_once()
            self.assertEqual(on_stop.call_count, 2)
            listener.is_alive.return_value = False
            with self.assertRaises(RuntimeError):
                start_hotkeys(on_start, on_stop)


if __name__ == '__main__':
    unittest.main()
