"""End-to-end material, cleanup, continuity and default-rendering contracts."""

import unittest
from ocdeck.jelly import Jelly, DeckGeometry
from ocdeck.world import World
from ocdeck.world_weather import WeatherService
from ocdeck.world_settings import settings
from ocdeck.world_objects import DEFINITIONS
from ocdeck.world_interactions import Interaction
from ocdeck.world_catalog import Scene, SCENES


class LifecycleTests(unittest.TestCase):
    def setup_activity(self, name, cells={0}):
        j = Jelly(DeckGeometry(), seed=3, options={"needs": False, "thoughts": "off"})
        j.settle(0, 0)
        return j, Interaction(), Scene(name, "demo", prop=name), cells

    def step(self, state, t):
        j, d, s, cells = state
        j.update(t, cells)
        d.tick(t, j, cells, "demo", s, settings({"scene_override": "autumn_rake"}))

    def run_to(self, state, stage, start=0):
        for n in range(start, start + 1600):
            self.step(state, n / 24)
            if state[1].stage == stage:
                return n
        self.fail((state[2].prop, stage, state[1].stage))

    def test_every_object_reaches_outcome_putdown_and_storage(self):
        for name in DEFINITIONS:
            with self.subTest(name=name):
                state = self.setup_activity(name)
                n = self.run_to(state, "rest")
                j, d, _, _ = state
                obj = d.objects[d.target]
                self.assertTrue(obj.applied)
                self.assertIsNone(d.held)
                self.assertEqual(obj.result, DEFINITIONS[name].result)
                self.run_to(state, "", n + 1)
                self.assertFalse(d.visible)
                self.assertFalse(d.owns_actor)
                self.assertEqual(d.render_layers(j, {0}), ({}, {}))
                self.assertEqual(obj.state, "stored")

    def test_ball_has_free_motion_then_pursuit_and_stop(self):
        state = self.setup_activity("beachball")
        n = self.run_to(state, "use")
        j, d, _, _ = state
        actor = j.x
        motion = []
        pursuit = []
        for k in range(n + 1, n + 195):
            self.step(state, k / 24)
            o = d.objects[d.target]
            motion.append(o.data.get("offset", 0))
            pursuit.append(j.x - actor)
        self.assertGreater(max(motion), 3)
        self.assertGreater(max(pursuit), 3)
        first = next(i for i, x in enumerate(motion) if x > 0.1)
        chase = next(i for i, x in enumerate(pursuit) if x > 0.1)
        self.assertLess(first, chase)
        self.assertTrue(o.data["stopped"])
        self.assertAlmostEqual(o.data["offset"], 0)

    def test_sled_boarding_and_kite_return(self):
        for name, key in [("sled", "boarded"), ("kite", "height")]:
            state = self.setup_activity(name)
            n = self.run_to(state, "use")
            j, d, _, _ = state
            values = []
            for k in range(n + 1, n + 300):
                self.step(state, k / 24)
                if not d.target:
                    break
                values.append(d.objects[d.target].data.get(key, 0))
            self.assertTrue(any(values))
            self.assertFalse(values[-1])
            self.assertEqual(j.y, j.geometry.anchor(j.current)[1])

    def test_fountain_visits_plant_before_awarding_water(self):
        state = self.setup_activity("fountain", {0, 1, 2})
        n = self.run_to(state, "water_carry")
        j, d, _, _ = state
        obj = d.objects[d.target]
        self.assertFalse(obj.applied)
        self.assertEqual(d.water, 1)
        self.assertNotEqual(obj.home, d.work_key)
        self.run_to(state, "rest", n + 1)
        self.assertEqual(obj.data["plant_water"], 1)
        self.assertEqual(d.water, 0)
        self.assertTrue(obj.applied)

    def test_gift_has_one_real_followup_toy(self):
        state = self.setup_activity("gift")
        n = self.run_to(state, "rest")
        j, d, _, _ = state
        gift = d.objects[d.target]
        identity = gift.data["gift_id"]
        d._outcome(j, gift)
        self.assertEqual(len([o for o in d.objects.values() if o.name == "beachball"]), 1)
        n = self.run_to(state, "", n + 1)
        self.run_to(state, "notice", n + 1)
        self.assertEqual(d.target, identity)

    def test_no_orphan_fallback_under_every_disable(self):
        for flag in ("living_world", "interactions", "props"):
            opts = settings(
                {
                    flag: False,
                    "particles": False,
                    "captions": False,
                    "weather": False,
                    "auto_location": False,
                    "scene_override": "autumn_rake",
                }
            )
            w = World(opts, WeatherService(opts))
            j = Jelly(DeckGeometry())
            j.settle(0, 0)
            for n in range(50):
                t = n / 12
                j.update(t, {0, 1})
                w.tick(t, j, {0, 1})
                original = j.crops({0, 1})
                result = w.decorate(t, j, original, {0, 1})
                self.assertEqual(
                    {k: v.tobytes() for k, v in result.items()}, {k: v.tobytes() for k, v in original.items()}
                )

    def test_every_scene_has_an_achievable_opportunity(self):
        from ocdeck.world_objects import ATMOSPHERES

        for name, s in SCENES.items():
            self.assertTrue(s.prop in DEFINITIONS or s.sky in ATMOSPHERES, name)

    def test_large_gap_cannot_complete_use(self):
        state = self.setup_activity("cocoa")
        n = self.run_to(state, "use")
        j, d, _, _ = state
        self.step(state, n / 24 + 1000)
        self.assertFalse(d.objects[d.target].applied)
        self.assertLess(d.objects[d.target].progress, 0.1)

    def test_frame_rates_agree_on_consumption_and_growth(self):
        for name in ("cocoa", "seedling", "rake"):
            results = []
            for fps in (12, 24, 30):
                state = self.setup_activity(name)
                for n in range(fps * 60):
                    self.step(state, n / fps)
                    d = state[1]
                    if d.stage == "rest":
                        obj = d.objects[d.target]
                        results.append((obj.amount, obj.progress, obj.result, obj.applied))
                        break
            self.assertEqual(len(results), 3)
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[1], results[2])

    def test_reset_marker_preserves_existing_saved_needs(self):
        import argparse
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from ocdeck.world_cli import run

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = {"needs": {"energy": 63}, "world": {"version": 1}}
            (root / "jelly-state.json").write_text(json.dumps(original))
            with patch("ocdeck.world_cli.home", return_value=root):
                run(argparse.Namespace(world_command="reset"))
            self.assertEqual(json.loads((root / "jelly-state.json").read_text()), original)
            self.assertEqual(len(json.loads((root / "world-reset.json").read_text())["generation"]), 32)
