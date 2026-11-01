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


class StartupRegressionTests(unittest.TestCase):
    def test_jarvis_live_initializes_without_health_logger_crash(self):
        ui = _DummyUI()
        session = main.JarvisLive(ui)
        self.assertIsNotNone(session)
        self.assertGreaterEqual(session._watchdog.stall_after_seconds, 0)

    def test_loop_shutdown_error_is_detected(self):
        ui = _DummyUI()
        session = main.JarvisLive(ui)
        self.assertTrue(session._is_loop_shutdown_error(RuntimeError("cannot schedule new futures after shutdown")))
        self.assertTrue(session._is_loop_shutdown_error(RuntimeError("Event loop is closed")))
        self.assertFalse(session._is_loop_shutdown_error(RuntimeError("temporary network failure")))


if __name__ == "__main__":
    unittest.main()
