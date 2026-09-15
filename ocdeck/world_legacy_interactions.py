"""Bounded, interruptible scene play. State lives on the render thread, never in art.

The actor uses existing Jelly poses and the existing free-key hop implementation.
Props retain an identity, key, grip, timeline and outcome instead of following the
nearest free viewport each frame. No input actions, I/O or background threads.
"""

from dataclasses import dataclass
import math
from PIL import Image, ImageDraw
from .world_props import prop, leaf, INK, WHITE, GOLD, GREEN, BLUE, PINK

# Only objects with a readable physical action get a manipulation recipe.
RECIPES = {
    "rake": "rake",
    "broom": "sweep",
    "cocoa": "drink",
    "lemonade": "drink",
    "popsicle": "taste",
    "acorn": "inspect",
    "leaf": "inspect",
    "heart": "inspect",
    "clover": "inspect",
    "gift": "unwrap",
    "letter": "read",
    "eggs": "inspect",
    "beachball": "play",
    "snowball": "play",
    "dreidel": "spin",
    "seedling": "water",
    "flower": "water",
    "train": "push",
    "telescope": "observe",
    "pinwheel": "blow",
    "cake": "candles",
    "snowman": "build",
    "sandcastle": "build",
    "pie": "taste",
    "sweets": "taste",
    "candy": "taste",
}


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


@dataclass(frozen=True)
class PlayFrame:
    key: int
    name: str
    action: str
    stage: str
    progress: float
    elapsed: float
    color: str


class Interaction:
    def __init__(self):
        self.frame = None
        self.scene = ""
        self.key = None
        self.started = 0.0
        self.stage_started = 0.0
        self.next_at = 0.0
        self.stage = ""
        self.origin_x = 0.0
        self.home_key = None
        self.owns_actor = False

    def cancel(self, now, jelly):
        # Never settle an actor after a higher-priority reaction or user tap.
        if self.owns_actor and jelly.state == "world_play" and jelly.current is not None:
            jelly.settle(jelly.current, now)
        self.frame, self.key, self.stage = None, None, ""
        self.owns_actor = False
        self.next_at = now + 3

    def tick(self, now, jelly, available, scene_id, scene, options, blocked=False):
        allowed = (
            not blocked
            and options["interactions"]
            and options["props"]
            and not options["reduced_motion"]
            and scene is not None
            and scene.prop in RECIPES
            and jelly.current in available
            and not jelly.update_available
            and now >= jelly.touch_until
            and jelly.mind.target is None
            and now >= jelly.look_until
            and jelly.mind.mood not in ("asleep", "overwhelmed", "overworked")
        )
        if scene_id != self.scene:
            self.cancel(now, jelly)
            self.scene, self.next_at = scene_id, now + 0.6
        if not allowed or (self.key is not None and self.key not in available):
            self.cancel(now, jelly)
            return
        if self.owns_actor and jelly.state not in ("world_play", "hop", "idle"):
            self.cancel(now, jelly)
            return
        if self.key is None:
            if now < self.next_at or jelly.state == "hop":
                return
            g = jelly.geometry
            # A real one-hop approach; disconnected keys are never crossed.
            neighbors = [
                k for k in g.adjacent(jelly.current) if k in available and k // g.columns == jelly.current // g.columns
            ]
            self.home_key = jelly.current
            self.key = neighbors[0] if neighbors else jelly.current
            self.started = self.stage_started = now
            self.stage = "notice"
        action = RECIPES[scene.prop]
        elapsed = now - self.stage_started
        if self.stage == "notice":
            if jelly.state == "hop":
                self.cancel(now, jelly)
                return
            jelly.state = "world_play"
            jelly.deadline = now + 2
            jelly.face, jelly.gaze = "curious", "right" if self.key >= jelly.current else "left"
            self.owns_actor = True
            if elapsed >= 0.8:
                if self.key != jelly.current:
                    if not jelly.hop(self.key, now, available):
                        self.cancel(now, jelly)
                        return
                    self.stage = "approach"
                else:
                    self.stage = "position"
                    self.origin_x = jelly.x
                self.stage_started = now
        elif self.stage == "approach":
            if now - self.started > 5 or (jelly.state != "hop" and jelly.current != self.key):
                self.cancel(now, jelly)
                return
            if jelly.state != "hop":
                self.stage, self.stage_started, self.origin_x = "position", now, jelly.x
        elif self.stage == "position":
            g = jelly.geometry
            left = g.bounds(self.key)[0]
            target_x = left + max(14 * g.scale, g.width / 2 - 7 * g.scale)
            jelly.x = self.origin_x + (target_x - self.origin_x) * ease(elapsed / 0.8)
            jelly.state, jelly.deadline = "world_play", now + 2
            jelly.pose, jelly.face, jelly.gaze = "scoot_front", "curious", "right"
            jelly.mirror = False
            if elapsed >= 0.8:
                self.stage, self.stage_started = "reach", now
        else:
            durations = {"reach": 0.8, "use": 4.0, "release": 0.8, "admire": 2.0}
            if self.stage != "rest" and elapsed >= durations[self.stage]:
                if self.stage == "admire":
                    self.stage = "rest"
                    x = jelly.x
                    jelly.settle(self.key, now)
                    jelly.x = x
                    if self.home_key in available and self.home_key != self.key:
                        jelly.hop(self.home_key, now, available)
                    self.owns_actor = False
                    self.next_at = now + options["interaction_seconds"]
                elif self.stage != "rest":
                    order = ["reach", "use", "release", "admire"]
                    self.stage = order[order.index(self.stage) + 1]
                self.stage_started, elapsed = now, 0.0
            if self.stage != "rest":
                jelly.state, jelly.deadline = "world_play", now + 2
                jelly.mirror, jelly.rotation = False, 0
                jelly.y = jelly.geometry.anchor(self.key)[1]
                jelly.gaze = "right"
                jelly.face = "happy" if self.stage == "admire" else "focused"
                jelly.pose = "curious_lean" if self.stage in ("reach", "use") else "idle"
                jelly.gesture, jelly.gesture_step = (
                    ("point", 2) if self.stage in ("reach", "use", "release") else ("clap", 2)
                )
                if self.stage == "use":
                    phase = int(elapsed * 8) % 8
                    if action in ("rake", "sweep", "water", "push", "build"):
                        jelly.pose = ("idle", "curious_lean", "curious_lean", "bob")[phase // 2]
                    if action in ("drink", "taste"):
                        jelly.face = "happy" if phase > 3 else "focused"
                    if action in ("observe", "blow", "candles"):
                        jelly.face = "focused"
            elif now >= self.next_at:
                self.cancel(now, jelly)
                return
        elapsed = max(0.0, now - self.stage_started)
        duration = {"reach": 0.8, "use": 4.0, "release": 0.8, "admire": 2.0}.get(self.stage, 1.0)
        progress = min(1.0, elapsed / duration)
        if self.stage in ("admire", "rest"):
            progress = 1.0
        self.frame = PlayFrame(self.key, scene.prop, action, self.stage, progress, elapsed, scene.color)

    def layers(self, jelly):
        """Back layer, actor, foreground grip/effect: separate sprites, not baked art."""
        if self.frame is None:
            return None
        f, g = self.frame, jelly.geometry
        w, h = math.ceil(g.width / g.scale), math.ceil(g.height / g.scale)
        back, front = Image.new("RGBA", (w, h)), Image.new("RGBA", (w, h))
        d, fg = ImageDraw.Draw(back), ImageDraw.Draw(front)
        left, top, _, _ = g.bounds(f.key)
        floor = (g.height - 3) // g.scale
        cx = round((jelly.x - left) / g.scale) if jelly.current == f.key else w // 2 - 7
        gx, gy = cx + 12, floor - 7
        rest_x = min(w - 8, round(max(14 * g.scale, g.width / 2 - 7 * g.scale) / g.scale) + 19)
        used = f.stage in ("use", "release", "admire", "rest")
        done = f.stage in ("release", "admire", "rest")
        active = f.stage in ("reach", "use", "release")
        t = (
            ease(f.progress)
            if f.stage == "reach"
            else 1 - ease(f.progress)
            if f.stage == "release"
            else 1.0
            if f.stage == "use"
            else 0.0
        )
        beat = 0 if done else (0, 1, 2, 3, 3, 2, 1, 0)[int(f.elapsed * 8) % 8]
        # The grip stays fixed; articulate endpoints, never rotate scaled pixel art.
        if f.action in ("rake", "sweep"):
            strokes = min(3, int(f.elapsed) + ease((f.elapsed % 1) / 0.65)) if f.stage == "use" else 3 if done else 0
            for i in range(7):
                start = rest_x + 4 - (i % 4) * 3
                x = round(start + ((rest_x - 3) - start) * min(1.0, strokes / 3))
                y = floor - 2 - (i // 4 if strokes == 0 else i % 3)
                c = "#d39c51" if i % 2 else "#b86c42"
                d.polygon(
                    [(x - 2, y), (x - 2, y - 2), (x, y - 1), (x + 1, y - 3), (x + 2, y - 1), (x + 3, y), (x, y + 1)],
                    fill=c,
                )
                d.line((x - 1, y, x + 1, y), fill=GOLD)
            hx = round(rest_x * (1 - t) + (gx + 6 - beat if f.stage == "use" else gx + 5) * t)
            hy = floor - 1 - round((1 - t) * 3)
            draw = fg if active else d
            draw.line((gx if active else rest_x - 5, gy - 4 if active else floor - 18, hx, hy), fill="#b98a59", width=2)
            draw.line((gx if active else rest_x - 5, gy - 4 if active else floor - 18, hx - 1, hy), fill=GOLD)
            if f.action == "rake":
                draw.line((hx - 4, hy - 1, hx + 4, hy - 1), fill="#a4bec8")
                for dx in (-4, -2, 0, 2, 4):
                    draw.line((hx + dx, hy - 1, hx + dx - 1, hy + 2), fill=WHITE)
            else:
                draw.polygon(
                    [(hx - 2, hy - 4), (hx + 2, hy - 4), (hx + 5, hy + 2), (hx - 5, hy + 2)],
                    fill="#be944f",
                    outline=INK,
                )
                for dx in (-3, 0, 3):
                    draw.line((hx + dx, hy - 2, hx + dx, hy + 1), fill=GOLD)
        else:
            art_phase = int(f.elapsed * 8) % 8
            if f.action in ("blow", "spin") and f.stage != "use":
                art_phase = min(7, int(f.elapsed * 3)) if done else 0
            im = prop(f.name, art_phase, f.color).copy()
            # Outcome variants are separate from immutable cached idle sprites.
            draw = ImageDraw.Draw(im)
            if f.action == "candles" and (done or f.stage == "use" and f.progress > 0.3):
                draw.rectangle((11, 8, 29, 16), fill=(0, 0, 0, 0))
                if not done:
                    for x in (15, 20, 25):
                        draw.line((x, 14, x + beat // 2, 10 - beat), fill="#8c9ba8")
            if f.action in ("unwrap", "read") and used:
                if f.action == "unwrap":
                    draw.rectangle((10, 13, 30, 23), fill=(0, 0, 0, 0))
                    draw.rectangle((12, 21, 28, 23), fill=INK)
                    lift = 5 if done else round(5 * ease(min(1.0, f.progress * 3)))
                    draw.rectangle((10, 17 - lift, 30, 21 - lift), fill=f.color, outline=INK)
                    draw.line((19, 18 - lift, 21, 20 - lift), fill=GOLD, width=2)
                else:
                    draw.polygon([(11, 23), (20, 17), (29, 23)], fill="#d1b28a", outline=INK)
                    draw.rectangle((14, 19, 26, 28), fill="#f4e7c8", outline=INK)
                    draw.line((16, 22, 24, 22), fill="#8d817b")
                    draw.line((16, 25, 22, 25), fill="#8d817b")
            if f.action == "taste" and used:
                # A small bite cutout at the top edge, held until the scene resets.
                box = im.getbbox()
                if box:
                    draw.ellipse((box[2] - 7, box[1] - 2, box[2] + 2, box[1] + 7), fill=(0, 0, 0, 0))
            box = im.getbbox()
            if box:
                im = im.crop(box)
                limit = 14 if f.action not in ("inspect", "drink", "taste") else 11
                ratio = min(1.0, limit / im.width, 22 / im.height)
                im = im.resize(
                    (max(1, round(im.width * ratio)), max(1, round(im.height * ratio))), Image.Resampling.NEAREST
                )
                x, y = rest_x - im.width // 2, floor - im.height
                held = f.action in ("drink", "taste", "inspect", "read")
                if held:
                    x = round(x * (1 - t) + (gx - 2) * t)
                    y = round(y * (1 - t) + (gy - im.height + 3 - (beat // 2 if f.action == "drink" else 0)) * t)
                if f.action in ("inspect", "read", "taste") and f.stage == "use":
                    y -= beat // 2
                    x += 1 if beat == 3 else 0
                if f.action == "play" and f.stage == "use":
                    # Repeated push, airborne arc, return to Jelly's side.
                    u = (f.elapsed % 1.3) / 1.3
                    x = round(gx - 2 + 5 * math.sin(math.pi * u))
                    y -= round(8 * math.sin(math.pi * u))
                if f.action == "spin" and f.stage == "use":
                    x += (beat - 1) // 2
                if f.action == "push" and f.stage == "use":
                    x += round(3 * math.sin(f.elapsed * 2))
                if f.action == "build" and (not used or f.stage == "use" and f.progress < 0.55):
                    im = im.crop((0, im.height // 2, im.width, im.height))
                    y = floor - im.height
                (front if held and active else back).alpha_composite(im, (x, y))
            if f.action == "water" and active:
                # Held watering can; drops land at the plant's root.
                fg.rectangle((gx - 2, gy - 3, gx + 4, gy + 3), fill="#6c9dae", outline=INK)
                fg.arc((gx - 5, gy - 3, gx, gy + 3), 90, 270, fill=WHITE)
                fg.line((gx + 4, gy, gx + 7, gy - 2), fill=BLUE, width=2)
                if f.stage == "use":
                    for i in range(3):
                        yy = gy + 1 + (int(f.elapsed * 12) + i * 3) % 8
                        fg.point((rest_x - 2 + i % 2, yy), fill=BLUE)
                if done:
                    d.line((rest_x - 4, floor, rest_x + 3, floor), fill="#365c58")
            if f.action in ("blow", "candles") and f.stage == "use":
                for i in range(2):
                    fg.line((gx + i * 3, gy - 4, gx + i * 3 + 2, gy - 4), fill="#7596aa")
            if f.action == "observe" and f.stage == "use":
                d.point((rest_x - 2 + beat % 2, 7 + beat // 2), fill=GOLD)
                fg.line((gx - 5, gy - 3, gx + 3, gy - 6), fill=BLUE, width=2)
                fg.point((gx - 4, gy - 4), fill=WHITE)
            if f.action == "build" and f.stage == "use":
                fg.rectangle((gx, gy, gx + 3, gy + 3), fill=WHITE if f.name == "snowman" else GOLD, outline=INK)
        return tuple(
            im.resize((w * g.scale, h * g.scale), Image.Resampling.NEAREST).crop((0, 0, g.width, g.height))
            for im in (back, front)
        )
