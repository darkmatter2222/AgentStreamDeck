"""Material lifetimes, local ground contact, elapsed timing and key ownership."""

import unittest
from PIL import Image, ImageDraw
from ocdeck.world_particles import particles, atmosphere, FALLING, LOCAL
from ocdeck.world import World
from ocdeck.world_settings import settings
from ocdeck.world_weather import WeatherService
from ocdeck.jelly import Jelly, DeckGeometry


class ParticleTests(unittest.TestCase):
    def test_falls_contact_then_recycles_without_crossing_floor(self):
        for kind in FALLING:
            tracks = {}
            stages = set()
            for i in range(1000):
                for p in particles(kind, 40, 40, i / 60, seed=17):
                    self.assertLessEqual(p.y, 37)
                    stages.add(p.stage)
                    identity = (p.index, p.cycle)
                    old = tracks.get(identity)
                    if old and old.stage == "fall" and p.stage == "fall":
                        self.assertGreaterEqual(p.y, old.y)
                    if old and old.stage != "fall":
                        self.assertNotEqual(p.stage, "fall")
                    tracks[identity] = p
            self.assertTrue({"fall", "impact"} <= stages)
            if kind != "rain":
                self.assertIn("rest", stages)

    def test_leaf_lands_sideways_and_fades_without_sinking(self):
        previous = {}
        rest_count = 0
        for i in range(1200):
            for p in particles("leaves", 40, 40, i / 60, seed=19):
                if p.stage != "rest":
                    continue
                rest_count += 1
                self.assertEqual(p.y, 37)
                self.assertEqual(p.tilt, 0)
                key = p.index, p.cycle
                if key in previous:
                    self.assertLessEqual(p.alpha, previous[key])
                previous[key] = p.alpha
        self.assertGreater(rest_count, 10)
        self.assertLess(min(previous.values()), 10)

    def test_rain_varies_depth_arrival_and_shape_with_fast_fall(self):
        a = {p.index: p for p in particles("rain", 72, 72, 1.2, seed=17) if p.stage == "fall"}
        b = {p.index: p for p in particles("rain", 72, 72, 1.25, seed=17) if p.stage == "fall"}
        speeds = [(b[k].y - a[k].y) / 0.05 for k in a.keys() & b.keys() if a[k].cycle == b[k].cycle]
        self.assertGreater(len(speeds), 3)
        self.assertGreater(max(speeds) - min(speeds), 20)
        self.assertGreater(min(speeds), 70)
        self.assertGreater(len({p.size for p in a.values()}), 1)
        self.assertGreater(len({round(p.progress, 1) for p in a.values()}), 3)

    def test_elapsed_sampling_is_reproducible_not_frame_count_dependent(self):
        expected = particles("snow", 40, 40, 8.5, seed=7)
        for fps in (12, 24, 30, 60):
            for i in range(int(8.5 * fps)):
                particles("snow", 40, 40, i / fps, seed=7)
            self.assertEqual(expected, particles("snow", 40, 40, 8.5, seed=7))
        self.assertNotEqual(expected, particles("snow", 40, 40, 8.5, seed=8))

    def test_rain_impact_is_finite_and_has_airborne_splash_pixels(self):
        impact = False
        for i in range(120):
            ps = particles("rain", 40, 40, i / 60, seed=17)
            if any(p.stage == "impact" and 0.2 < p.progress < 0.7 for p in ps):
                impact = True
                im = Image.new("RGBA", (40, 40))
                atmosphere(ImageDraw.Draw(im), "rain", 40, 40, i / 60, seed=17)
                self.assertIsNotNone(im.crop((0, 33, 40, 38)).getbbox())
        self.assertTrue(impact)
        self.assertFalse(any(p.stage == "rest" for p in particles("rain", 40, 40, 20, seed=17)))

    def test_all_effects_are_bounded_and_render_at_native_geometry(self):
        for size, rows, cols in ((72, 2, 3), (80, 3, 5), (96, 4, 8)):
            g = DeckGeometry(rows, cols, size, size)
            for kind in LOCAL:
                im = Image.new("RGBA", (size, size))
                self.assertTrue(atmosphere(ImageDraw.Draw(im), kind, size, size, 2.3, seed=27))
            o = settings(dict(scene_override="rain", weather=False, auto_location=False, props=False, captions=False))
            w = World(o, WeatherService(o))
            j = Jelly(g, seed=1)
            j.settle(0, 0)
            w.tick(1, j)
            free = {0, cols, rows * cols - 1}
            rendered = w.decorate(1.3, j, {}, free)
            self.assertTrue(set(rendered) <= free)
            for key in free:
                self.assertIn(key, rendered)
                self.assertEqual(rendered[key].size, (size, size))
            self.assertNotEqual(rendered[0].tobytes(), rendered[cols].tobytes())
            self.assertEqual(w.decorate(2, j, {}, set()), {})

    def test_production_motion_updates_between_old_eighth_second_ticks(self):
        o = settings(dict(scene_override="rain", weather=False, auto_location=False, props=False, captions=False))
        w = World(o, WeatherService(o))
        j = Jelly(DeckGeometry(), seed=1)
        j.settle(0, 0)
        w.tick(1, j)
        a = w.decorate(1.0, j, {}, {0})[0]
        b = w.decorate(1.0 + 1 / 24, j, {}, {0})[0]
        self.assertEqual(int(1.0 * 8), int((1.0 + 1 / 24) * 8))
        self.assertNotEqual(a.tobytes(), b.tobytes())

    def test_reduced_motion_freezes_particles(self):
        o = settings(
            dict(
                scene_override="snow",
                weather=False,
                auto_location=False,
                props=False,
                captions=False,
                reduced_motion=True,
            )
        )
        w = World(o, WeatherService(o))
        j = Jelly(DeckGeometry(), seed=1)
        j.settle(0, 0)
        w.tick(1, j)
        a = w.decorate(1, j, {}, {0, 1})
        b = w.decorate(50, j, {}, {0, 1})
        self.assertEqual({k: v.tobytes() for k, v in a.items()}, {k: v.tobytes() for k, v in b.items()})


if __name__ == "__main__":
    unittest.main()
