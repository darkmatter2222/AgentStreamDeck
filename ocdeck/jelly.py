"""One floor-dwelling companion in continuous deck-space. No worker threads or I/O."""

from dataclasses import dataclass
from collections import deque
import math
import random
from PIL import Image
from .jelly_art import ANCHOR, GRID, colored_sprite
from .jelly_catalog import ACTIONS, HOPS, MOOD_ACTIONS, MOOD_CATEGORY
from .jelly_mind import Mind, PRESETS
from .jelly_words import Thoughts


def settings(config):
    value = config.get("jelly", {})
    defaults = {
        "enabled": True,
        "virtual_gap": 8,
        "behavior_seed": None,
        "hop_style": "classic",
        "personality": "balanced",
        "mood_colors": True,
        "needs": True,
        "reactions": True,
        "thoughts": "normal",
        "local_movement": "normal",
        "travel": "normal",
        "persistent": False,
        "coffee": True,
        "coffee_rainbow": True,
    }
    if not isinstance(value, dict) or set(value) - set(defaults):
        raise ValueError("Unknown or invalid jelly configuration")
    result = {**defaults, **value}
    for name in ("enabled", "mood_colors", "needs", "reactions", "persistent", "coffee", "coffee_rainbow"):
        if type(result[name]) is not bool:
            raise ValueError(f"jelly.{name} must be boolean")
    if type(result["virtual_gap"]) is not int or not 0 <= result["virtual_gap"] <= 40:
        raise ValueError("jelly.virtual_gap must be 0..40 integer pixels")
    if result["behavior_seed"] is not None and type(result["behavior_seed"]) is not int:
        raise ValueError("jelly.behavior_seed must be an integer or null")
    for name, choices in {
        "hop_style": (*HOPS, "mood"),
        "personality": PRESETS,
        "thoughts": ("off", "quiet", "normal", "chatty"),
        "local_movement": ("low", "normal", "high"),
        "travel": ("rare", "normal", "frequent"),
    }.items():
        if not isinstance(result[name], str) or result[name] not in choices:
            raise ValueError(f"Invalid jelly.{name}")
    return result


def free_keys(views):
    return {k for k, view in enumerate(views) if view["state"] == "off" and not view.get("id")}


@dataclass(frozen=True)
class DeckGeometry:
    rows: int = 2
    columns: int = 3
    width: int = 80
    height: int = 80
    gap: int = 8

    def __post_init__(self):
        if min(self.rows, self.columns, self.width, self.height) < 1 or self.gap < 0:
            raise ValueError("Invalid deck geometry")

    @property
    def count(self):
        return self.rows * self.columns

    @property
    def size(self):
        return (self.columns * (self.width + self.gap) - self.gap, self.rows * (self.height + self.gap) - self.gap)

    @property
    def scale(self):
        return max(1, min(self.width, self.height) // GRID)

    def bounds(self, key):
        if key not in range(self.count):
            raise ValueError("Key outside deck")
        row, col = divmod(key, self.columns)
        x, y = col * (self.width + self.gap), row * (self.height + self.gap)
        return x, y, x + self.width, y + self.height

    def anchor(self, key):
        x, _, _, bottom = self.bounds(key)
        return x + self.width / 2, bottom - 3

    def adjacent(self, key):
        self.bounds(key)
        row, col = divmod(key, self.columns)
        return tuple(
            r * self.columns + c
            for r, c in ((row, col - 1), (row, col + 1), (row - 1, col), (row + 1, col))
            if 0 <= r < self.rows and 0 <= c < self.columns
        )

    def reachable(self, source, available):
        """Free connected component, including the actor's current cell."""
        free = set(available) & set(range(self.count))
        if source not in free:
            return set()
        seen, queue = {source}, deque([source])
        while queue:
            for key in self.adjacent(queue.popleft()):
                if key in free and key not in seen:
                    seen.add(key)
                    queue.append(key)
        return seen

    def route_to(self, source, target, available):
        """Shortest orthogonal path to the object itself; None means unreachable."""
        free = set(available) & set(range(self.count))
        if source not in free or target not in free:
            return None
        queue, seen = deque([(source, [])]), {source}
        while queue:
            key, path = queue.popleft()
            if key == target:
                return path
            for nxt in self.adjacent(key):
                if nxt in free and nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, path + [nxt]))
        return None

    def route_beside(self, source, target, available):
        """Shortest free-only route to a free orthogonal neighbor of an agent."""
        if source not in available or target not in range(self.count):
            return []
        goals = set(self.adjacent(target)) & set(available)
        queue = deque([(source, [])])
        seen = {source}
        while queue:
            key, path = queue.popleft()
            if key in goals:
                return path
            for nxt in self.adjacent(key):
                if nxt in available and nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, path + [nxt]))
        return []


class Jelly:
    PREPARE, FLIGHT, LANDING = 0.6, 0.7, 0.5

    def __init__(self, geometry, seed=None, hop_style="classic", options=None):
        self.geometry = geometry
        self.options = settings({"jelly": {**(options or {}), "hop_style": hop_style}})
        self.rng = random.Random(seed)
        self.hop_style = hop_style
        self.active_hop = "classic"
        self.state = "hidden"
        self.current = self.destination = None
        self.x = self.y = 0.0
        self.since = 0.0
        self.deadline = None
        self.pose, self.face, self.gaze = "idle", "neutral", "center"
        self.gesture, self.gesture_step, self.mirror = "", 0, False
        self.closed = False
        self.mind = Mind(self.rng, self.options)
        self.thoughts = Thoughts(self.rng, self.options["thoughts"])
        self.now = 0.0
        self.rotation = 0
        self.local_from = self.local_to = 0.0
        self.action_duration = 1.0
        self.flight_origin = (0.0, 0.0)
        self.look_target = None
        self.look_until = 0.0
        self.pending_speech = None
        self.last_mood = "content"
        self.touch_until = 0.0
        self.touch_text = ""
        self.update_available = False
        self.world_costume = ""
        self.world_phase = 0

    def tap(self, now):
        """A visible, short reaction, even when ambient thoughts are disabled."""
        if self.current is None or now < self.touch_until - 1.7:
            return
        self.settle(self.current, now)
        self.start_action(self.rng.choice(("reform", "cheer", "dance")), now)
        self.touch_text = self.rng.choice(("Ouch!", "Hehe!", "Boop!", "Hey!", "Tickles!"))
        self.touch_until = now + 2
        self.thoughts.clear()

    def close(self):
        self.closed = True
        self.hide()

    def hide(self):
        self.state, self.current, self.destination = "hidden", None, None
        self.deadline = None
        self.thoughts.clear()
        self.pending_speech = None
        self.look_target = None
        self.touch_until = 0.0

    def settle(self, key, now):
        self.current, self.destination = key, None
        self.x, self.y = self.geometry.anchor(key)
        self.state, self.since = "idle", now
        self.deadline = now + self.rng.uniform(2.0, 4.5)
        self.rotation = 0

    def hop(self, destination, now, available):
        if (
            self.closed
            or self.current is None
            or self.state == "hop"
            or self.current not in available
            or destination not in available
            or destination not in self.geometry.adjacent(self.current)
        ):
            return False
        style = self.hop_style
        if style == "mood":
            style = {
                "sleepy": "sleepy",
                "playful": "tuck_roll",
                "excited": "excited",
                "cautious": "nervous",
                "shy": "nervous",
                "overworked": "heavy",
                "mischievous": "vault",
                "restless": "running",
            }.get(self.mind.mood, self.rng.choice(("classic", "fluid", "bunny", "floaty", "sideways")))
        if style == "careful_drop" and destination < self.current:
            style = "classic"
        self.active_hop = style
        self.PREPARE, self.FLIGHT, self.LANDING = HOPS[style][:3]
        self.flight_origin = (self.x, self.y)
        self.destination, self.state, self.since = destination, "hop", now
        self.thoughts.clear()
        return True

    def start_action(self, action, now, target=None):
        if self.current is None or self.closed or self.state == "hop":
            return False
        self.state, self.since = action, now
        self.local_from = self.x
        self.action_duration = (
            ACTIONS[action][0] if action in ACTIONS else 0.5 if action == "blink" else 5 if action == "rest" else 1.4
        )
        self.deadline = now + self.action_duration
        center, _ = self.geometry.anchor(self.current)
        # Leave room for the widest 35px pose, including at 1x on 72px keys.
        span = max(0, self.geometry.width / 2 - 18 * self.geometry.scale)
        direction = self.rng.choice((-1, 1))
        if target is not None:
            direction = 1 if self.geometry.anchor(target)[0] >= self.x else -1
        if action == "retreat":
            direction *= -1
        self.local_to = center + span * direction
        if action not in ACTIONS or ACTIONS[action][2] not in ("move", "edge", "pace", "tumble"):
            self.local_to = self.local_from
        self.mirror = direction < 0
        return True

    def _point(self, target):
        if self.current is None:
            return
        tx, ty = self.geometry.anchor(target)
        dx, dy = tx - self.x, ty - self.y
        if abs(dy) > abs(dx):
            self.gaze, self.gesture = ("up", "up") if dy < 0 else ("down", "down")
            self.mirror = False
        else:
            self.gaze, self.gesture = "right", "point"
            self.mirror = dx < 0
        self.gesture_step = 3
        self.face = "curious"

    def update(self, now, available, views=None, events=()):
        dt = max(0.0, min(0.1, now - self.now))
        self.now = now
        if self.closed:
            return
        # Standalone animation previews have no session telemetry to infer needs from.
        if views is not None or events:
            self.mind.observe(now, views, events)
        available = set(available) & set(range(self.geometry.count))
        if (
            not available
            or self.current is not None
            and self.current not in available
            or self.destination is not None
            and self.destination not in available
        ):
            self.hide()
            return
        if self.state == "hidden":
            if self.deadline is None:
                self.deadline = now + self.rng.uniform(0.5, 1.3)
            elif now >= self.deadline:
                self.settle(self.rng.choice(sorted(available)), now)
            return
        self.pose, self.face, self.gaze = "idle", "neutral", "center"
        self.gesture, self.gesture_step, self.rotation = "", 0, 0
        if self.state == "hop":
            self._hop_pose(now)
            return
        if self.update_available:
            # The update UI schedules infrequent hops. Hold a breathing pose
            # between them so autonomous travel and reactions cannot add hops.
            self.state = "idle"
            self.deadline = now + 60
            self.thoughts.clear()
            self._idle_pose(now)
            return
        # Reaction bursts are coalesced; only the render thread changes the entity.
        reaction = self.mind.consume_reaction()
        if reaction and self.options["reactions"]:
            action, category, target = reaction
            self.look_target, self.look_until = target, now + 8
            self.pending_speech = (category, now + 12)
            self.thoughts.clear()
            self.start_action(action, now, target)
        if self.last_mood != self.mind.mood:
            self.last_mood = self.mind.mood
            if not reaction and self.mind.mood in ("waking", "asleep", "startled"):
                self.start_action({"waking": "reform", "asleep": "rest", "startled": "retreat"}[self.mind.mood], now)
        if self.deadline is not None and now >= self.deadline and not self.thoughts.active(now):
            if self.state != "idle":
                self.state, self.since = "idle", now
                self.deadline = now + self.rng.uniform(2, 5)
                self.y = self.geometry.anchor(self.current)[1]
            else:
                self._choose(now, available)
        if self.state in ACTIONS:
            self._local_pose(now)
        elif self.state == "hop":
            self._hop_pose(now)
            return
        else:
            self._idle_pose(now)
        target = self.mind.target if self.options["reactions"] else None
        if target is not None and self.state == "idle":
            # Re-evaluate free-only paths on every decision, never retain stale routes.
            route = self.geometry.route_beside(self.current, target, available)
            if route and not self.thoughts.active(now) and self.mind.mood not in ("overwhelmed", "overworked"):
                if self.hop(route[0], now, available):
                    self._hop_pose(now)
                    return
            self._point(target)
            # Scoot to the target-facing side while retaining a floor anchor.
            center, _ = self.geometry.anchor(self.current)
            span = max(0, self.geometry.width / 2 - 18 * self.geometry.scale)
            tx, _ = self.geometry.anchor(target)
            goal = center + (span if tx > center else -span if tx < center else 0)
            self.x += max(-24 * dt, min(24 * dt, goal - self.x))
        elif self.look_target is not None and now < self.look_until and self.state not in ACTIONS:
            self._point(self.look_target)
        elif self.look_target is not None:
            self.look_target = None
        self._talk(now, views)

    def _choose(self, now, available):
        assert self.current is not None
        neighbors = [k for k in self.geometry.adjacent(self.current) if k in available]
        quiet = ("blink", "look_left", "look_right", "look_up", "rest", "wave", "point_left", "point_right")
        mood = self.mind.mood
        preferred = MOOD_ACTIONS[mood]
        if self.options["needs"]:
            if self.mind.needs["stimulation"] < 25:
                preferred += ("pace", "scratch", "melt")
            if self.mind.needs["confidence"] < 35:
                preferred += ("tiptoe", "retreat", "edge_peek")
            if self.mind.needs["sociability"] > 70:
                preferred += ("wave", "nod", "look_left", "look_right")
        calm = mood in ("asleep", "sleepy", "overwhelmed", "overworked", "focused")
        if mood == "asleep":
            self.start_action("rest", now)
            return
        weights = [
            70.0,
            {"low": 8, "normal": 20, "high": 40}[self.options["local_movement"]],
            {"rare": 2, "normal": 10, "frequent": 25}[self.options["travel"]] if neighbors else 0,
        ]
        curiosity, play = PRESETS[self.options["personality"]]
        weights[1] *= play
        weights[2] *= curiosity
        if calm or self.mind.target is not None:
            weights[2] = 0
            weights[1] *= 0.2
        group = self.rng.choices(("quiet", "local", "travel"), weights)[0]
        if group == "travel":
            self.hop(self.rng.choice(neighbors), now, available)
        else:
            pool = quiet + preferred * 2 if group == "quiet" else tuple(ACTIONS) + preferred * 3
            self.start_action(self.rng.choice(pool), now)

    def _talk(self, now, views):
        calm_states = ("idle", "look_left", "look_right", "look_up", "point_left", "point_right", "blink")
        if self.state not in calm_states or self.mind.mood == "asleep":
            self.thoughts.clear()
            return
        category, event = MOOD_CATEGORY[self.mind.mood], False
        if self.pending_speech:
            if now <= self.pending_speech[1]:
                category, event = self.pending_speech[0], True
            else:
                self.pending_speech = None
        states = {v["state"] for v in views or () if v.get("id")}
        if (
            category == "running"
            and "running" not in states
            or category == "input"
            and "input" not in states
            or category == "concern"
            and "unknown" not in states
            or category in ("success", "failure", "resolved", "greetings", "departures", "reconnected")
            and not event
        ):
            category = "quiet"
        # Clear stale requests/observations as soon as their conditions disappear.
        if (
            self.thoughts.category == "input"
            and "input" not in states
            or self.thoughts.category == "running"
            and "running" not in states
            or self.thoughts.category == "concern"
            and "unknown" not in states
        ):
            self.thoughts.clear()
        if self.thoughts.say(category, now, self.geometry.width, self.geometry.scale, event):
            self.pending_speech = None
            self.deadline = max(self.deadline or now, self.thoughts.until + 0.3)

    def _idle_pose(self, now):
        elapsed = max(0, now - self.since)
        self.mirror = False
        if self.state == "idle":
            self.pose = "breathe" if 1.6 <= elapsed % 3.2 < 2.1 else "idle"
        elif self.state == "blink":
            self.face = ("neutral", "half", "closed", "closed", "half", "neutral")[min(5, int(elapsed * 12))]
        elif self.state.startswith("look_"):
            self.gaze, self.face = self.state[5:], "curious"
        elif self.state == "rest":
            self.pose = "sleep_curl"
            self.face = "half" if elapsed < 0.3 or elapsed > 4.6 else "sleepy"
        elif self.state == "wave" or self.state.startswith("point_"):
            self.face = "happy"
            self.mirror = self.state == "point_left"
            self.gaze = "right"
            if elapsed >= 0.25:
                self.gesture = "wave" if self.state == "wave" else "point"
                self.gesture_step = (1, 2, 3, 4, 3, 4, 3, 4, 3, 2, 1, 0)[min(11, int((elapsed - 0.25) * 12))]

    def _local_pose(self, now):
        _, poses, motion = ACTIONS[self.state]
        t = min(1.0, max(0.0, (now - self.since) / self.action_duration))
        # Quantized pose holds; position remains a continuous function of elapsed time.
        pose_t = math.floor(t * self.action_duration * 12) / (self.action_duration * 12)
        self.pose = poses[min(len(poses) - 1, int(pose_t * len(poses)))]
        base_y = self.geometry.anchor(self.current)[1]
        ease = t * t * (3 - 2 * t)
        self.y = base_y
        self.face = "happy" if self.state in ("dance", "cheer", "applaud", "spin", "roll") else "curious"
        if motion in ("move", "edge", "tumble"):
            self.x = self.local_from + (self.local_to - self.local_from) * ease
        elif motion == "pace":
            self.x = self.local_from + (self.local_to - self.local_from) * math.sin(math.pi * t) ** 2
            self.mirror = t > 0.5
        if motion in ("bounce", "cheer", "tumble"):
            u = max(0.0, min(1.0, (t - 0.2) / 0.6))
            self.y -= 10 * 4 * u * (1 - u)
        if motion == "dance":
            self.y -= 3 * abs(math.sin(t * math.pi * 4))
            self.mirror = int(t * 6) % 2 == 1
        if motion in ("turn", "shake"):
            self.mirror = int(t * (4 if motion == "shake" else 2)) % 2 == 1
        if self.state in ("roll", "spin", "somersault") and 0.2 < t < 0.8:
            self.rotation = int((t - 0.2) / 0.6 * 4) % 4
        if motion in ("scratch", "clap", "cheer"):
            self.gesture = motion
            self.gesture_step = (1, 2, 3, 4, 3, 2, 1)[min(6, int(t * 7))]
        if self.state in ("melt", "yawn"):
            self.face = "sleepy" if self.state == "melt" else "jump"

    def _hop_pose(self, now):
        assert self.current is not None and self.destination is not None
        elapsed = max(0, now - self.since)
        a, b = self.flight_origin, self.geometry.anchor(self.destination)
        dx, dy = b[0] - a[0], b[1] - a[1]
        self.mirror = dx < 0
        self.gaze = "right" if dx else "up" if dy < 0 else "down"
        self.face = "focused"
        profile = HOPS[self.active_hop]
        if elapsed < self.PREPARE:
            t = elapsed / self.PREPARE
            self.x, self.y = a
            self.pose = ("idle", "bob", "idle", "squash", "deep", "deep")[min(5, int(t * 6))]
            if self.active_hop in ("bunny", "excited"):
                self.y -= 3 * abs(math.sin(t * math.pi * 2))
            if self.active_hop == "running":
                self.x += (1 if dx >= 0 else -1) * 3 * math.sin(math.pi * t)
                self.pose = "scoot_front" if t < 0.6 else "deep"
            if self.active_hop == "careful_drop":
                self.pose = "curious_lean" if t < 0.7 else "drag_tail"
            if self.active_hop == "vault":
                self.gesture, self.gesture_step = "down", 3
        elif elapsed < self.PREPARE + self.FLIGHT:
            t = (elapsed - self.PREPARE) / self.FLIGHT
            ease = t * t * (3 - 2 * t)
            self.x = a[0] + dx * ease
            arc = self.geometry.height * (0.17 if abs(dx) > abs(dy) else 0.09) * profile[3]
            self.y = a[1] + dy * ease - arc * 4 * t * (1 - t)
            poses = profile[4]
            self.pose = poses[min(len(poses) - 1, int(t * len(poses)))]
            self.face = "jump"
            if self.active_hop == "sideways":
                self.gaze, self.mirror = "center", False
            if self.active_hop == "tuck_roll":
                self.rotation = int(t * 4) % 4
        elif elapsed < self.PREPARE + self.FLIGHT + self.LANDING:
            self.x, self.y = b
            t = (elapsed - self.PREPARE - self.FLIGHT) / self.LANDING
            poses = ("impact", "impact", "rebound", "jiggle", "idle")
            if self.active_hop in ("heavy", "tuck_roll"):
                poses = ("asym_impact", "side_flop", "puddle", "crown_ripple", "idle")
            self.pose = poses[min(4, int(t * 5))]
            self.face = "landing"
            if self.active_hop == "bunny":
                self.y -= 4 * math.sin(math.pi * t) ** 2
        else:
            self.settle(self.destination, now)
            self.pose, self.face, self.mirror = "idle", "happy", False

    def crops(self, available):
        if self.closed or self.current is None or self.state == "hidden":
            return {}
        if self.current not in available or self.destination is not None and self.destination not in available:
            return {}
        g = self.geometry
        mood, previous = (
            (self.mind.mood, self.mind.previous_mood) if self.options["mood_colors"] else ("content", "content")
        )
        blend = min(3, max(0, int((self.now - self.mind.mood_since) / 0.3)))
        im = colored_sprite(
            self.pose,
            self.face,
            self.gaze,
            self.gesture,
            self.gesture_step,
            g.scale,
            self.mirror,
            mood,
            previous,
            blend,
        )
        if self.world_costume:
            from .world_art import costume
            from .jelly_art import POSES

            logical = im.resize((GRID, GRID), Image.Resampling.NEAREST)
            im = costume(logical, self.world_costume, self.world_phase, 34 - POSES[self.pose][1]).resize(
                im.size, Image.Resampling.NEAREST
            )
        if self.rotation:
            rotated = im.rotate(90 * self.rotation, resample=Image.Resampling.NEAREST)
            box = rotated.getbbox()
            if box:
                aligned = Image.new("RGBA", im.size)
                aligned.paste(rotated, (0, ANCHOR[1] * g.scale - box[3]))
                im = aligned
        x, y = round(self.x - ANCHOR[0] * g.scale), round(self.y - ANCHOR[1] * g.scale)
        result = {}
        # Local life belongs to its own key. During hops, all free viewports share the world sprite.
        for key in sorted(available if self.state == "hop" else {self.current}):
            l, t, r, b = g.bounds(key)
            if x >= r or y >= b or x + im.width <= l or y + im.height <= t:
                continue
            viewport = Image.new("RGBA", (g.width, g.height))
            viewport.paste(im, (x - l, y - t))
            if viewport.getbbox():
                result[key] = viewport
        if self.current in result and self.now < self.touch_until:
            from .coffee import caption

            caption(result[self.current], self.touch_text)
        elif self.state != "hop" and self.thoughts.active(self.now) and self.current in result:
            result[self.current].paste(self.thoughts.render(g.width, g.scale, self.now), (0, 2))
        return result
