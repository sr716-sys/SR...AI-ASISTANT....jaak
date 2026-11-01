import unittest

from actions import capcut_pipeline


class CapCutPipelineTests(unittest.TestCase):
    def test_pipeline_has_expected_capcut_sequence(self):
        steps = capcut_pipeline.build_capcut_tiktok_pipeline("aggressive TikTok edit")
        self.assertTrue(steps)
        self.assertEqual(steps[0]["tool"], "open_app")
        self.assertEqual(steps[1]["tool"], "focus_window")
        self.assertIn("screen_find", [s["tool"] for s in steps])
        self.assertIn("screen_click", [s["tool"] for s in steps])
        self.assertGreaterEqual(len(steps), 8)

    def test_execute_pipeline_calls_the_expected_actions(self):
        calls = []

        def fake_open_app(params=None, response=None, player=None, session_memory=None):
            calls.append(("open_app", params))
            return "Opened CapCut."

        def fake_computer_control(params=None, response=None, player=None, session_memory=None):
            calls.append(("computer_control", params))
            return "ok"

        old_open = capcut_pipeline.open_app_tool
        old_control = capcut_pipeline.computer_control
        capcut_pipeline.open_app_tool = fake_open_app
        capcut_pipeline.computer_control = fake_computer_control

        try:
            result = capcut_pipeline.execute_capcut_pipeline("aggressive TikTok edit")
            self.assertIn("CapCut pipeline completed", result)
            self.assertTrue(any(call[0] == "open_app" for call in calls))
            self.assertTrue(any(call[0] == "computer_control" for call in calls))
        finally:
            capcut_pipeline.open_app_tool = old_open
            capcut_pipeline.computer_control = old_control


if __name__ == "__main__":
    unittest.main()
