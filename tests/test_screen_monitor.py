import unittest

from control.coordinate_mapper import CoordinateMapper, MonitorInfo
from control.screen_monitor import ScreenSnapshot


class ScreenMappingTests(unittest.TestCase):
    def test_snapshot_origin_is_preserved_for_negative_monitor_layouts(self):
        snapshot = ScreenSnapshot(b"", 3840, 1080, -1920, 0, 1.0)
        mapper = CoordinateMapper(screenshot_size=(snapshot.width, snapshot.height))
        monitor = MonitorInfo(
            snapshot.left,
            snapshot.top,
            snapshot.left + snapshot.width,
            snapshot.top + snapshot.height,
            snapshot.width,
            snapshot.height,
        )
        self.assertEqual(
            mapper.vision_to_cursor(1920, 540, screenshot_size=(snapshot.width, snapshot.height), monitor=monitor),
            (0, 540),
        )


if __name__ == "__main__":
    unittest.main()
