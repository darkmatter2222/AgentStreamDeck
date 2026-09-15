"""Real actor/director integration: causal state, interruption, and input priority."""

import argparse
import tempfile
import unittest
from PIL import Image
from ocdeck.jelly import Jelly, DeckGeometry
from ocdeck.world import World
from ocdeck.world_settings import settings, read_ini
from ocdeck.world_weather import WeatherService
from ocdeck.world_catalog import SCENES
from ocdeck.world_interactions import RECIPES
from ocdeck.world_cli import add_parser, save


class InteractionTests(unittest.TestCase):
    def make(self, scene="autumn_rake", size=80, rows=2, cols=3, **changes):
        o = settings(dict(scene_override=scene, weather=False, auto_location=False, captions=False, **changes))
        world = World(o, WeatherService(o))
        jelly = Jelly(
            DeckGeometry(rows, cols, size, size), seed=2, options={"thoughts": "off", "needs": False, "travel": "rare"}
        )
        jelly.settle(0, 0)
        return jelly, world

    def step(self, jelly, world, now, free={0, 1}, blocked=False):
        jelly.update(now, free)
        world.tick(now, jelly, free, blocked=blocked)
        original = jelly.crops(free)
        before = {k: im.tobytes() for k, im in original.items()}
        frames = world.decorate(now, jelly, original, free)
        self.assertEqual(before, {k: im.tobytes() for k, im in original.items()})
        self.assertTrue(set(frames) <= free)
        return frames

    def test_each_manipulation_finishes_with_real_approach_and_stable_prop_key(self):
        seen = set()
        for scene, spec in SCENES.items():
            if spec.prop not in RECIPES or spec.prop in seen:
                continue
            seen.add(spec.prop)
            for size, rows, cols, free in ((72, 2, 3, {0}), (80, 3, 5, {0, 1}), (96, 4, 8, {0, 1})):
                with self.subTest(prop=spec.prop, size=size):
                    jelly, world = self.make(scene, size, rows, cols)
                    stages = set()
                    keys = set()
                    used_pixels = set()
                    for n in range(600):
                        frames = self.step(jelly, world, n / 12, free)
                        f = world.interaction.frame
                        if f:
                            stages.add(f.stage)
                            keys.add(f.key)
                            if f.stage == "use":
                                used_pixels.add(frames[f.key].tobytes())
                            if f.stage == "rest":
                                break
                    self.assertTrue({"notice", "position", "reach", "use", "putdown", "admire", "rest"} <= stages)
                    self.assertTrue(keys <= free)
                    self.assertGreater(len(used_pixels), 2)
                    if len(free) > 1:
                        self.assertIn("approach", stages)
        self.assertEqual(seen, {s.prop for s in SCENES.values() if s.prop})

    def test_rake_gathers_leaves_and_retains_pile_after_putting_tool_down(self):
        jelly, world = self.make()
        for n in range(600):
            self.step(jelly, world, n / 12)
            if world.interaction.stage == "rest":
                break
        director = world.interaction
        obj = director.objects[director.target]
        self.assertEqual(obj.data["gathered"], 1)
        self.assertEqual(obj.cell, obj.home)
        self.assertEqual(jelly.current, obj.home)
        self.assertIsNone(director.held)

    def test_cancel_on_ownership_loss_touch_focus_help_update_or_menu(self):
        for reason in (
            "ownership",
            "touch",
            "focus",
            "help",
            "update",
            "menu",
            "disabled",
            "props",
            "reduced",
        ):
            jelly, world = self.make()
            for n in range(600):
                self.step(jelly, world, n / 12)
                if world.interaction.stage == "use":
                    break
            self.assertEqual(world.interaction.stage, "use")
            now = (n + 1) / 12
            free = {0, 1}
            blocked = False
            if reason == "ownership":
                free = {0, 1} - {world.interaction.objects[world.interaction.target].home}
            elif reason == "touch":
                jelly.tap(now)
            elif reason == "focus":
                jelly.look_until = 20
            elif reason == "help":
                world.help_until = 20
            elif reason == "update":
                jelly.update_available = True
            elif reason == "menu":
                blocked = True
            elif reason == "disabled":
                world.options["interactions"] = False
            elif reason == "scene":
                world.options["scene_override"] = "cloudy"
            elif reason == "props":
                world.options["props"] = False
            else:
                world.options["reduced_motion"] = True
            self.step(jelly, world, now, free, blocked)
            with self.subTest(reason=reason):
                self.assertIsNone(world.interaction.frame)
                self.assertFalse(world.interaction.owns_actor)
                if reason == "touch":
                    self.assertGreater(jelly.touch_until, now)

    def test_no_crossing_occupied_or_disconnected_keys_and_max_keys(self):
        for free, options in (({0, 2}, {}), ({0, 1}, {"max_keys": 1}), (set(), {})):
            jelly, world = self.make(**options)
            destinations = set()
            for n in range(120):
                self.step(jelly, world, n / 12, free)
                if jelly.destination is not None:
                    destinations.add(jelly.destination)
            self.assertFalse(destinations)

    def test_scarf_keeps_face_pixels_visible_during_play(self):
        from ocdeck.jelly_art import logical_sprite, POSES
        from ocdeck.world_art import costume

        for pose in ("idle", "curious_lean", "bob", "scoot_front"):
            original = logical_sprite(pose, "focused")
            dressed = costume(original, "scarf", 3, 34 - POSES[pose][1])
            # Scarf belongs below the entire head/eye region.
            self.assertEqual(original.crop((8, 0, 32, 31)).tobytes(), dressed.crop((8, 0, 32, 31)).tobytes())

    def test_cli_ini_round_trip_and_validation(self):
        parser = argparse.ArgumentParser()
        add_parser(parser.add_subparsers())
        args = parser.parse_args(["world", "configure", "--no-interactions", "--interaction-seconds", "40"])
        self.assertFalse(args.interactions)
        self.assertEqual(args.interaction_seconds, 40)
        with tempfile.TemporaryDirectory() as root:
            o = settings({"interactions": False, "interaction_seconds": 40})
            save(root, o)
            self.assertEqual(read_ini(root), o)
        for changes in ({"interactions": "yes"}, {"interaction_seconds": 0}, {"interaction_seconds": 301}):
            with self.assertRaises(ValueError):
                settings(changes)


if __name__ == "__main__":
    unittest.main()
