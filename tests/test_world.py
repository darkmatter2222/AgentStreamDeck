"""World integration tests: real scene rendering, date boundaries, network isolation and input ownership."""

from datetime import date, datetime, timezone
import json
from pathlib import Path
import queue
import tempfile
import threading
import unittest
from unittest.mock import patch
from PIL import Image
from ocdeck.world_settings import settings, read_ini, DEFAULTS
from ocdeck.world_catalog import SCENES, EXTRAS
from ocdeck.world_weather import WeatherService, Location, Weather, parse_location, parse_weather
from ocdeck.world_calendar import active_holiday, dates, season, quiet
from ocdeck.world import World, HELP_URL
from ocdeck.world_cli import save
from ocdeck.jelly import Jelly, DeckGeometry
from ocdeck.device import DeviceLoop
from ocdeck.model import Registry
from ocdeck.broker import Broker

NOW = 1800000000


def weather_data(**changes):
    return {
        "current": {"temperature_2m": 34, "weather_code": 0, "wind_speed_10m": 10, "is_day": 1, "time": NOW, **changes}
    }


class CalendarTests(unittest.TestCase):
    def test_requested_windows(self):
        o = settings()
        for day in (3, 4, 5):
            self.assertEqual(active_holiday(date(2026, 7, day), o), "july4")
        self.assertIsNone(active_holiday(date(2026, 7, 6), o))
        self.assertEqual(active_holiday(date(2026, 10, 24), o), "halloween")
        self.assertIsNone(active_holiday(date(2026, 10, 23), o))
        self.assertEqual(active_holiday(date(2026, 12, 13), o), "christmas")

    def test_new_year_crosses_year_and_canada_thanksgiving(self):
        o = settings()
        self.assertEqual(active_holiday(date(2025, 12, 31), o), "newyear")
        self.assertEqual(active_holiday(date(2026, 1, 2), o), "newyear")
        self.assertEqual(active_holiday(date(2026, 10, 12), o, "CA"), "thanksgiving")
        self.assertEqual(active_holiday(date(2026, 11, 26), o, "US"), "thanksgiving")

    def test_movable_festivals_and_full_hanukkah(self):
        values = {name: day for name, day, _ in dates(2026, "US")}
        for name, day in [
            ("holi", date(2026, 3, 4)),
            ("easter", date(2026, 4, 5)),
            ("lunar", date(2026, 2, 17)),
            ("hanukkah", date(2026, 12, 5)),
        ]:
            self.assertEqual(values[name], day)
        o = settings({"holiday_ids": "hanukkah"})
        self.assertEqual(active_holiday(date(2026, 12, 12), o), "hanukkah")

    def test_day_of_beats_longer_window_and_priority(self):
        o = settings({"birthday": "12-25"})
        self.assertEqual(active_holiday(date(2026, 12, 25), o), "birthday")
        self.assertIsNone(active_holiday(date(2026, 7, 4), settings({"holidays": False})))
        self.assertIsNone(active_holiday(date(2026, 7, 4), settings({"holiday_ids": "christmas"})))

    def test_leap_day_seasons_and_quiet_hours(self):
        o = settings({"birthday": "02-29", "holiday_ids": "birthday", "before_days": 0, "after_days": 0})
        self.assertIsNone(active_holiday(date(2027, 2, 28), o))
        self.assertEqual(active_holiday(date(2028, 2, 29), o), "birthday")
        self.assertEqual(season(date(2026, 7, 1), True), "winter")
        self.assertEqual(season(date(2026, 12, 1), False), "winter")
        for hour in (22, 23, 0, 6):
            self.assertTrue(quiet(hour, 22, 7))
        self.assertFalse(quiet(7, 22, 7))


class WeatherTests(unittest.TestCase):
    def test_wmo_mapping(self):
        for code, want in [
            (0, "hot"),
            (3, "hot"),
            (45, "fog"),
            (61, "rain"),
            (71, "snow"),
            (85, "snow"),
            (95, "storm"),
        ]:
            self.assertEqual(parse_weather(weather_data(weather_code=code), NOW).condition, want)
        self.assertEqual(parse_weather(weather_data(temperature_2m=20, wind_speed_10m=40), NOW).condition, "wind")

    def test_bad_provider_values(self):
        for changes in (
            {"temperature_2m": float("nan")},
            {"wind_speed_10m": -1},
            {"weather_code": 99.5},
            {"time": NOW + 99999},
            {"is_day": True},
            {"weather_code": 4},
        ):
            with self.assertRaises((ValueError, TypeError)):
                parse_weather(weather_data(**changes), NOW)
        with self.assertRaises(ValueError):
            parse_location({"success": False})

    def test_explicit_location_bypasses_ip_and_stale_data_expires(self):
        calls = []
        clock = [NOW]

        def fetch(url):
            calls.append(url)
            return weather_data()

        o = settings({"latitude": "34", "longitude": "-84"})
        service = WeatherService(o, fetch, lambda: clock[0])
        service.refresh()
        self.assertEqual(len(calls), 1)
        self.assertIn("api.open-meteo.com", calls[0])
        self.assertIsNotNone(service.snapshot()[1])
        clock[0] += o["stale_seconds"] + 1
        self.assertIsNone(service.snapshot()[1])
        self.assertEqual(service.snapshot()[2], "Weather expired")

    def test_auto_lookup_and_daily_reuse(self):
        calls = []

        def fetch(url):
            calls.append(url)
            if "ipwho.is" in url:
                return {
                    "success": True,
                    "latitude": 34,
                    "longitude": -84,
                    "country_code": "US",
                    "timezone": {"id": "America/New_York"},
                }
            return weather_data()

        service = WeatherService(settings(), fetch, lambda: NOW)
        service.refresh()
        service.refresh()
        self.assertEqual(sum("ipwho.is" in c for c in calls), 1)
        self.assertEqual(service.snapshot()[0].source, "ip")

    def test_failure_keeps_fresh_snapshot_without_crashing(self):
        service = WeatherService(
            settings({"latitude": "34", "longitude": "-84"}), lambda _: weather_data(), lambda: NOW
        )
        service.refresh()

        def broken(_):
            raise OSError("provider unavailable")

        service.fetch = broken
        service.refresh()
        self.assertIsNotNone(service.snapshot()[1])
        self.assertIn("unavailable", service.snapshot()[2])

    def test_offline_mode_and_close(self):
        service = WeatherService(settings({"auto_location": False, "weather": False}))
        service.start()
        self.assertIsNone(service.thread)
        service.close()
        self.assertTrue(service.stop.is_set())


class WorldTests(unittest.TestCase):
    def make(self, count=6, options=None):
        rows, cols = {6: (2, 3), 15: (3, 5), 32: (4, 8)}[count]
        g = DeckGeometry(rows, cols)
        jelly = Jelly(g, seed=1, options={"thoughts": "off"})
        jelly.settle(0, 0)
        o = settings({"auto_location": False, "weather": False, "captions": False, **(options or {})})
        service = WeatherService(o, clock=lambda: NOW)
        world = World(o, service, wall=lambda: datetime(2026, 7, 4, 12, tzinfo=timezone.utc).timestamp())
        return jelly, world

    def test_all_75_scenes_render_and_never_paint_occupied_keys(self):
        self.assertEqual(len(EXTRAS), 50)
        self.assertEqual(len(SCENES), 75)
        for count in (6, 15, 32):
            for scene in SCENES:
                with self.subTest(count=count, scene=scene):
                    jelly, world = self.make(count, {"scene_override": scene})
                    available = {0, 1, count - 1}
                    world.tick(1, jelly)
                    frames = world.decorate(1, jelly, jelly.crops(available), available)
                    self.assertTrue(set(frames) <= available)
                    self.assertTrue(frames)
                    self.assertTrue(all(im.size == (80, 80) for im in frames.values()))
                    self.assertEqual(world.decorate(1, jelly, {}, set()), {})

    def test_single_key_degradation_and_resize(self):
        for size in (72, 80, 96):
            for scene in ("thanksgiving_table", "christmas_lights", "sky_fireworks", "ghost_hover"):
                jelly, world = self.make(options={"scene_override": scene})
                jelly.geometry = DeckGeometry(2, 3, size, size)
                world.tick(1, jelly)
                frames = world.decorate(1, jelly, jelly.crops({0}), {0})
                self.assertEqual(set(frames), {0})
                self.assertEqual(frames[0].size, (size, size))

    def test_disabled_scene_and_switches(self):
        jelly, world = self.make(options={"scene_override": "christmas_santa", "disabled_scenes": "christmas_santa"})
        world.tick(1, jelly)
        self.assertEqual(world.scene_id, "")
        jelly, world = self.make(
            options={"scene_override": "christmas_santa", "particles": False, "props": False, "costumes": False}
        )
        world.tick(1, jelly)
        self.assertEqual(jelly.world_costume, "")
        frames = jelly.crops({0, 1, 2})
        result = world.decorate(1, jelly, frames, {0, 1, 2})
        self.assertEqual(set(result), set(frames))
        for key in frames:
            self.assertEqual(result[key].tobytes(), frames[key].tobytes())

    def test_ghost_floats_and_reduced_motion_holds_jelly(self):
        jelly, world = self.make(options={"scene_override": "ghost_hover"})
        world.tick(1, jelly)
        self.assertLess(jelly.y, jelly.geometry.anchor(0)[1])
        self.assertEqual(jelly.hop_style, "floaty")
        jelly, world = self.make(options={"scene_override": "sky_fireworks", "reduced_motion": True})
        world.tick(1, jelly)
        a = world.decorate(1, jelly, jelly.crops({0, 1}), {0, 1})
        jelly.update(3, {0, 1})
        world.tick(3, jelly)
        b = world.decorate(3, jelly, jelly.crops({0, 1}), {0, 1})
        self.assertEqual(jelly.state, "idle")
        self.assertEqual({k: v.tobytes() for k, v in a.items()}, {k: v.tobytes() for k, v in b.items()})

    def test_calendar_timezone_and_weather_caption_fahrenheit(self):
        jelly, world = self.make(
            options={"weather": True, "captions": True, "timezone": "America/New_York", "country": "US"}
        )
        world.service.location = Location(34, -84, "US", "America/New_York")
        world.service.weather = Weather(34, "hot", 0, True, NOW, NOW)
        world.wall = lambda: datetime(2026, 7, 5, 2, tzinfo=timezone.utc).timestamp()
        world.tick(1, jelly)
        self.assertEqual(world.holiday, "july4")
        self.assertIn("93F", world.caption)

    def test_unknown_location_hints_are_rate_limited_and_help_opens_only_on_second_hold(self):
        jelly, world = self.make(options={"weather": True, "captions": True})
        world.tick(1, jelly)
        self.assertIn("Location unknown", world.caption)
        next_hint = world.next_hint
        world.tick(100, jelly)
        self.assertEqual(world.next_hint, next_hint)
        self.assertFalse(world.hold(100))
        self.assertTrue(world.hold(102))
        self.assertFalse(world.hold(150))

    def test_update_and_quiet_hours_hide_world(self):
        jelly, world = self.make(options={"scene_override": "christmas_santa"})
        jelly.update_available = True
        world.tick(1, jelly)
        self.assertFalse(world.active)
        jelly, world = self.make(options={"quiet_start": 0, "quiet_end": 23, "timezone": "UTC"})
        world.tick(1, jelly)
        self.assertFalse(world.active)

    def test_after_rain_scene_requires_observed_transition(self):
        jelly, world = self.make(options={"holidays": False, "weather": True})
        world.service.weather = Weather(20, "rain", 0, True, NOW, NOW)
        world.tick(1, jelly)
        world.service.weather = Weather(20, "clear", 0, True, NOW, NOW)
        world.tick(2, jelly)
        self.assertEqual(world.group, "after_rain")

    def test_ini_round_trip_and_invalid_settings(self):
        with tempfile.TemporaryDirectory() as root:
            value = settings({"country": "US", "birthday": "12-25", "latitude": "34", "longitude": "-84"})
            save(root, value)
            self.assertEqual(read_ini(root), value)
            (Path(root) / "jelly.ini").write_text("[world]\nmade_up=true\n")
            with self.assertRaises(ValueError):
                read_ini(root)
        for change in (
            {"latitude": "nan", "longitude": "0"},
            {"poll_seconds": 2},
            {"enabled": "false"},
            {"scene_override": "missing"},
            {"disabled_scenes": "missing"},
            {"quiet_start": 22},
        ):
            with self.assertRaises(ValueError):
                settings(change)

    def test_five_short_released_taps_still_request_coffee_with_world_enabled(self):
        registry = Registry(lambda _: True)
        loop = DeviceLoop(
            registry,
            queue.Queue(),
            threading.Event(),
            {"jelly": {"thoughts": "off"}, "world": {"auto_location": False}},
            mock=True,
        )
        loop._start_jelly()
        loop.jelly.settle(0, 0)
        loop.coffee.next_at = 10000
        for i in range(5):
            now = 1 + i * 2
            views = registry.view()
            loop._jelly_frames(now, views)
            for key, view in enumerate(views):
                loop.presented[key] = loop._presented_view(key, view)
            key = loop.jelly.current
            with patch("ocdeck.device.time.monotonic", return_value=now):
                loop.press(key, True)
            with patch("ocdeck.device.time.monotonic", return_value=now + 0.1):
                loop.press(key, False)
            loop._jelly_frames(now + 0.1, views)
        self.assertIsNotNone(loop.coffee.key)
        self.assertTrue(loop.presses.empty())
        loop.world_service.close()

    def test_physical_hold_generation_and_synthetic_browser_guard(self):
        loop = DeviceLoop(Registry(lambda _: True), queue.Queue(), threading.Event(), {}, mock=True)
        _, loop.world = self.make()
        loop.world.active = True
        view = {"id": None, "generation": 1, "slot": 0, "_action": "tap"}
        loop.presented[0] = view
        with patch("ocdeck.device.time.monotonic", side_effect=[1, 2, 2]):
            loop.press(0, True)
            loop.press(0, False)
        self.assertEqual(loop.jelly_events.get_nowait()["kind"], "world_hold")
        with patch("ocdeck.device.time.monotonic", return_value=3):
            loop.press(0, True)
        loop.presented[0] = {**view, "id": "new-agent", "generation": 2}
        loop.press(0, False)
        self.assertTrue(loop.jelly_events.empty())
        with tempfile.TemporaryDirectory() as root:
            broker = Broker(root, mock=True)
            with patch("webbrowser.open") as browser:
                broker.handle_press({"_action": "open_world_help"}, synthetic=True)
                browser.assert_not_called()
                broker.handle_press({"_action": "open_world_help"})
                browser.assert_called_once_with(HELP_URL, new=2)


if __name__ == "__main__":
    unittest.main()
