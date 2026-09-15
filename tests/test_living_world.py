"""Semantic checks for the opt-in director. Visual coverage is tracked separately."""

import json
from pathlib import Path
import unittest
from ocdeck.jelly import Jelly, DeckGeometry
from ocdeck.world import World
from ocdeck.world_settings import settings
from ocdeck.world_weather import WeatherService
from ocdeck.world_interactions import Interaction
from ocdeck.world_catalog import Scene
from ocdeck.world_objects import DEFINITIONS
from ocdeck.world_object_art import grip


class LivingWorldTests(unittest.TestCase):
    def make(self, name="rake", seed=6, size=80, rows=2, cols=3):
        jelly = Jelly(DeckGeometry(rows, cols, size, size), seed=seed, options={"thoughts": "off", "needs": True})
        jelly.settle(0, 0)
        return jelly, Interaction(), Scene(name, "demo", prop=name)

    def step(self, j, d, scene, now, free, blocked=False):
        j.update(now, free)
        d.tick(now, j, free, "test", scene, settings({"living_world": True, "scene_override": "autumn_rake"}), blocked)

    def complete(self, j, d, s, free):
        for i in range(2400):
            self.step(j, d, s, i / 24, free)
            if d.stage == "rest":
                return
        self.fail("Activity did not finish")

    def test_path_targets_actual_cell_and_never_crosses_sessions(self):
        g = DeckGeometry(2, 3)
        self.assertEqual(g.route_to(0, 5, {0, 1, 2, 5}), [1, 2, 5])
        self.assertIsNone(g.route_to(0, 5, {0, 2, 5}))
        self.assertEqual(g.reachable(0, {0, 2, 3, 5}), {0, 3})

    def test_seeded_placement_varies_across_entire_reachable_component(self):
        destinations = set()
        for seed in range(100):
            j, d, _ = self.make(seed=seed)
            destinations.add(d._choose_cell(j, set(range(6))))
            j2, d2, _ = self.make(seed=seed)
            self.assertEqual(d.locations[-1], d2._choose_cell(j2, set(range(6))))
        self.assertEqual(destinations, set(range(6)))

    def test_rake_travels_to_tool_then_work_and_returns_before_rest(self):
        j, d, s = self.make()
        hops = []
        tool_home = None
        for i in range(1800):
            self.step(j, d, s, i / 24, set(range(6)))
            if d.target:
                obj = d.objects[d.target]
                if tool_home is None:
                    tool_home = obj.home
                self.assertEqual(obj.home, tool_home)
                if j.state == "hop":
                    self.assertIn(j.destination, j.geometry.adjacent(j.current))
                    if not hops or hops[-1] != (j.current, j.destination):
                        hops.append((j.current, j.destination))
            if d.stage == "rest":
                break
        self.assertGreaterEqual(len(hops), 4)
        obj = d.objects[d.target]
        self.assertEqual(obj.result, "pile")
        self.assertEqual(obj.data["gathered"], 1)
        self.assertEqual(obj.cell, obj.home)
        self.assertIsNone(d.held)
        self.assertFalse(d.owns_actor)
        pickup = next(e for e in d.events if e[0] == "pickup")
        self.assertEqual(pickup[2], obj.home)
        self.assertEqual(len([e for e in d.events if e[0] == "outcome"]), 1)

    def test_claim_or_menu_at_every_stage_releases_actor_and_visuals(self):
        for stage in ("notice", "approach", "reach", "carry", "use", "return", "putdown", "admire"):
            for blocked in (True, False):
                j, d, s = self.make()
                for i in range(1800):
                    self.step(j, d, s, i / 24, set(range(6)))
                    if d.stage == stage:
                        break
                self.assertEqual(d.stage, stage)
                free = set(range(6)) if blocked else set(range(6)) - {d.objects[d.target].home}
                self.step(j, d, s, (i + 1) / 24, free, blocked)
                self.assertIsNone(d.frame)
                self.assertFalse(d.owns_actor)
                self.assertEqual(d.render_layers(j, free), ({}, {}))

    def test_cup_amount_and_need_effect_apply_once(self):
        j, d, s = self.make("cocoa")
        before = j.mind.needs["nourishment"]
        self.complete(j, d, s, {0})
        obj = d.objects[d.target]
        self.assertEqual(obj.amount, 0)
        self.assertEqual(j.mind.needs["nourishment"], before + 5)
        d._outcome(j, obj)
        self.assertEqual(j.mind.needs["nourishment"], before + 5)
        self.assertEqual(obj.cell, obj.home)

    def test_scene_change_preserves_in_progress_identity(self):
        j, d, s = self.make("cocoa")
        for i in range(48):
            self.step(j, d, s, i / 24, {0})
        identity = d.target
        self.step(j, d, Scene("ball", "demo", prop="beachball"), 2, {0})
        self.assertEqual(d.target, identity)
        self.assertEqual(d.objects[identity].name, "cocoa")

    def test_saved_state_is_bounded_and_restores_without_stale_cells(self):
        j, d, s = self.make("cocoa")
        self.complete(j, d, s, {0})
        restored = Interaction()
        restored.restore(json.loads(json.dumps(d.snapshot())))
        obj = next(iter(restored.objects.values()))
        self.assertEqual(obj.amount, 0)
        self.assertTrue(obj.applied)
        self.assertIsNone(obj.cell)
        self.assertEqual(obj.state, "stored")
        restored.restore({"version": 1, "objects": [{"id": 1, "name": "cocoa", "progress": float("nan"), "amount": 1}]})
        self.assertEqual(restored.objects, {})

    def test_every_definition_renders_without_mutating_state_or_cached_art(self):
        from ocdeck.world_props import prop

        for size, rows, cols in ((72, 2, 3), (80, 3, 5), (96, 4, 8)):
            for name in DEFINITIONS:
                j, d, s = self.make(name, size=size, rows=rows, cols=cols)
                prior = prop(name).tobytes()
                sampled = set()
                for i in range(480):
                    self.step(j, d, s, i / 24, {0})
                    if d.stage not in sampled and d.frame:
                        sampled.add(d.stage)
                        before = json.dumps(d.snapshot(), sort_keys=True)
                        back, front = d.render_layers(j, {0})
                        self.assertTrue(set(back) | set(front) <= {0})
                        self.assertEqual(before, json.dumps(d.snapshot(), sort_keys=True))
                    if d.stage == "rest":
                        break
                self.assertEqual(prior, prop(name).tobytes())
                self.assertIn("rest", sampled, name)

    def test_grip_is_mirrored_and_uses_actual_pose(self):
        j, _, _ = self.make()
        for pose in ("idle", "deep", "stretch", "impact"):
            j.pose = pose
            j.mirror = False
            a = grip(j)
            j.mirror = True
            b = grip(j)
            self.assertEqual(a[0] - j.x, j.x - b[0])
            self.assertEqual(a[1], b[1])

    def test_no_free_cells_and_disconnected_regions(self):
        j, d, s = self.make()
        self.step(j, d, s, 1, set())
        self.assertIsNone(d.target)
        j, d, s = self.make()
        self.complete(j, d, s, {0, 2, 5})
        self.assertEqual(d.work_key, 0)

    def test_coverage_inventory_matches_source(self):
        data = json.loads((Path(__file__).parents[1] / "docs/jelly/world-coverage.json").read_text())
        self.assertEqual(set(data["props"]), set(DEFINITIONS))
        self.assertEqual(len(data["scenes"]), 75)

    def test_default_uses_living_director(self):
        o = settings({"weather": False, "auto_location": False})
        w = World(o, WeatherService(o))
        self.assertIsInstance(w.interaction, Interaction)
        o["living_world"] = True
        self.assertIsInstance(World(o, WeatherService(o)).interaction, Interaction)
