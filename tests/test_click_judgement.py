import unittest

from actions import computer_control


class ClickJudgementTests(unittest.TestCase):
    def test_close_tab_is_decided_as_hotkey_not_screen_click(self):
        plan = computer_control._build_click_plan("close this tab")
        self.assertEqual(plan["mode"], "hotkey")
        self.assertIn("w", plan["keys"])

    def test_generic_ui_target_is_screen_based(self):
        plan = computer_control._build_click_plan("search bar")
        self.assertEqual(plan["mode"], "screen")
        self.assertIn("search", plan["description"].lower())

    def test_dynamic_close_tab_uses_direct_hotkey(self):
        calls = []
        old = computer_control._hotkey
        computer_control._hotkey = lambda *keys: calls.append(keys) or "hotkey"
        try:
            result = computer_control.computer_control({"action": "smart_action", "description": "close this tab"})
            self.assertIn("close tab", result.lower())
            self.assertTrue(calls)
        finally:
            computer_control._hotkey = old


if __name__ == "__main__":
    unittest.main()
