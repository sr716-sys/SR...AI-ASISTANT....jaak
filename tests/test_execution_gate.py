import unittest

import main


class _DummyUI:
    def __init__(self):
        self._muted = False
        self._win = type("Win", (), {"_ready": True})()
        self.on_push_to_talk = None
        self.ptt_hold = None
        self.on_text_command = None
        self.on_remote_clicked = None
        self.on_interrupt = None
        self.on_voice_change = None
        self.on_audio_device_change = None
        self.get_plugins = None
        self.get_plugin_settings = None
        self.on_wake_toggle = None
        self.on_wake_manual = None
        self.on_wake_install = None
        self.wake_is_ready = lambda: True
        self.wake_get_state = lambda: {"enabled": False, "awake": True, "ready": True}
        self.request_say = None

    def write_log(self, *args, **kwargs):
        pass

    def set_state(self, *args, **kwargs):
        pass

    @property
    def muted(self):
        return self._muted


class ExecutionGateTests(unittest.TestCase):
    def test_app_launch_requires_verification(self):
        session = main.JarvisLive(_DummyUI())
        self.assertTrue(session._requires_verification("open_app", {"app_name": "Brave"}))

    def test_close_tab_requires_verification(self):
        session = main.JarvisLive(_DummyUI())
        self.assertTrue(session._requires_verification("computer_control", {"action": "smart_action", "description": "close this tab"}))

    def test_desktop_action_has_verification_gate(self):
        session = main.JarvisLive(_DummyUI())
        self.assertTrue(session._requires_verification("browser_control", {"action": "go_to", "url": "https://example.com"}))


if __name__ == "__main__":
    unittest.main()
