"""Lazy native keyboard integration, so preview works without permissions."""
import sys


def permission_status() -> tuple[bool, str]:
    if sys.platform != "darwin":
        return True, "Keyboard access available."
    try:
        import Quartz
        from ApplicationServices import AXIsProcessTrusted
        trusted = AXIsProcessTrusted()
        listen = Quartz.CGPreflightListenEventAccess()
        post = Quartz.CGPreflightPostEventAccess()
        if trusted and listen and post:
            return True, "Keyboard access available."
        return False, (
            "Allow Online Class Record Helper in System Settings → Privacy & Security → "
            "Accessibility and Input Monitoring. Quit and reopen the app after granting "
            "access. When running source, grant access to your terminal/Python instead. "
            "Test mode remains available. Mac F9/F10 may require Fn."
        )
    except Exception as exc:
        return False, f"Cannot check macOS keyboard access: {exc}. Test mode remains available."


class NativeKeyboard:
    def __init__(self, stop_requested=lambda: False):
        from pynput.keyboard import Controller, Key
        self.controller = Controller()
        self.stop_requested = stop_requested
        self.keys = {name: getattr(Key, name.lower())
                     for name in ("Enter", "Tab", "Down", "Right", "Up")}

    def type_text(self, text):
        for character in text:
            if self.stop_requested():
                break
            self.controller.type(character)

    def press_key(self, name):
        key = self.keys[name]
        self.controller.press(key)
        self.controller.release(key)


def start_hotkeys(on_start, on_stop):
    from pynput.keyboard import GlobalHotKeys
    listener = GlobalHotKeys({"<f9>": on_start, "<f10>": on_stop, "<esc>": on_stop})
    listener.start()
    listener.wait()
    if not listener.is_alive():
        listener.join(timeout=1)
        raise RuntimeError("The keyboard listener could not start. Check system keyboard permissions.")
    return listener
