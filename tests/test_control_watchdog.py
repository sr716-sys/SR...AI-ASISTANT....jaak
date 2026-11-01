import time
import unittest

from control.watchdog import Watchdog, HealthRecord
from control.recovery import RecoveryPolicy


class WatchdogTests(unittest.TestCase):
    def test_health_record_tracks_progress(self):
        rec = HealthRecord()
        rec.note_progress("receive")
        rec.note_progress("tool")
        self.assertEqual(rec.last_progress_kind, "tool_call")
        self.assertGreaterEqual(rec.last_progress_ts, 0)

    def test_health_record_tracks_alias_progress(self):
        rec = HealthRecord()
        rec.note_progress("tool")
        rec.note_progress("screen")
        self.assertGreater(rec.last_tool_call_ts, 0)
        self.assertGreater(rec.last_screen_capture_ts, 0)
        self.assertEqual(rec.current_task, "IDLE")

    def test_watchdog_detects_stall(self):
        wd = Watchdog(stall_after_seconds=0.05, idle_after_seconds=0.02)
        wd.mark_progress("receive")
        time.sleep(0.08)
        self.assertTrue(wd.is_stalled())

    def test_recovery_policy_restarts_retry_budget(self):
        policy = RecoveryPolicy(max_retries=2, backoff_seconds=1.0)
        plan = policy.build_plan(strategy="RECONNECT_STALL")
        plan.record_retry("stalled_session")
        plan.record_retry("stalled_session")
        self.assertFalse(policy.should_retry(plan))
        plan.reset()
        self.assertTrue(policy.should_retry(plan))
        self.assertEqual(plan.retry_count, 0)


if __name__ == "__main__":
    unittest.main()
