import unittest

from control import windows_input
from actions import computer_settings


class WindowsInputHotkeyTests(unittest.TestCase):
    def test_hotkey_accepts_string_combo_tokens(self):
        keys = windows_input.normalize_key_sequence("alt + tab")
        self.assertEqual(keys, ["alt", "tab"])

        keys = windows_input.normalize_key_sequence("ctrl+shift+esc")
        self.assertEqual(keys, ["ctrl", "shift", "esc"])

    def test_hotkey_handles_alt_switch_combo(self):
        combo = windows_input.normalize_key_sequence("alt+tab")
        self.assertEqual(combo, ["alt", "tab"])

    def test_media_keys_have_native_virtual_key_codes(self):
        self.assertEqual(windows_input.VK_CODES["volumeup"], 0xAF)
        self.assertEqual(windows_input.VK_CODES["volumedown"], 0xAE)
        self.assertEqual(windows_input.VK_CODES["volumemute"], 0xAD)

    def test_invalid_mouse_buttons_are_rejected(self):
        with self.assertRaises(ValueError):
            windows_input.click(button="invalid")
        with self.assertRaises(ValueError):
            windows_input.mouse_down("invalid")
        with self.assertRaises(ValueError):
            windows_input.mouse_up("invalid")
        with self.assertRaises(ValueError):
            windows_input.click(clicks=0)

    def test_windows_window_management_uses_native_hotkeys(self):
        calls = []
        old_os = computer_settings._OS
        old_native = computer_settings._NATIVE_HOTKEY
        old_hotkey = computer_settings.native_hotkey
        try:
            computer_settings._OS = "Windows"
            computer_settings._NATIVE_HOTKEY = True
            computer_settings.native_hotkey = lambda *keys: calls.append(keys)
            computer_settings.minimize_window()
            computer_settings.maximize_window()
            computer_settings.snap_left()
            computer_settings.snap_right()
        finally:
            computer_settings._OS = old_os
            computer_settings._NATIVE_HOTKEY = old_native
            computer_settings.native_hotkey = old_hotkey
        self.assertEqual(calls, [
            ("win", "down"),
            ("win", "up"),
            ("win", "left"),
            ("win", "right"),
        ])

    def test_computer_control_exposes_mouse_button_hold_and_release(self):
        from actions import computer_control

        calls = []
        old_backend = computer_control._CONTROL_BACKEND
        old_down = computer_control.native_mouse_down
        old_up = computer_control.native_mouse_up
        try:
            computer_control._CONTROL_BACKEND = "windows-native"
            computer_control.native_mouse_down = lambda button: calls.append(("down", button))
            computer_control.native_mouse_up = lambda button: calls.append(("up", button))
            self.assertIn("down", computer_control.computer_control({
                "action": "mouse_down", "button": "left"
            }))
            self.assertIn("up", computer_control.computer_control({
                "action": "mouse_up", "button": "left"
            }))
        finally:
            computer_control._CONTROL_BACKEND = old_backend
            computer_control.native_mouse_down = old_down
            computer_control.native_mouse_up = old_up
        self.assertEqual(calls, [("down", "left"), ("up", "left")])


if __name__ == "__main__":
    unittest.main()
