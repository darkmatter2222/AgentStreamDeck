"""Environment presentation synchronized to the activity that gives it a source."""

import math
from PIL import Image, ImageDraw
from .world_art import sky
from .world_objects import ATMOSPHERES

# These are made/operated objects or sourced effects, never anonymous overlays.
SOURCED = {"balloons", "confetti", "fountain", "hearts", "icicles", "lanterns", "lights", "smoke", "fireworks"}


def layers(director, jelly, keys):
    if director.target is None or not director.visible:
        return {}
    obj = director.objects[director.target]
    kind = director.sky
    if not kind or kind not in ATMOSPHERES:
        return {}
    g = jelly.geometry
    key = director.work_key if obj.name in ("rake", "broom", "kite", "lantern", "balloon") else obj.home
    if key not in keys:
        return {}
    scale = g.scale
    width, height = math.ceil(g.width / scale), math.ceil(g.height / scale)
    im = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(im)
    p = obj.progress
    active = director.stage in ("use", "water_pour", "admire", "rest")
    age = director.use_elapsed
    x, floor = width - 17, height - 3
    if kind in ("butterflies", "fireflies"):
        # Approach and land at the tended plant/viewing spot, then depart.
        u = min(1, max(0, (p - 0.2) / 0.3))
        depart = max(0, (p - 0.8) / 0.2)
        xx = round(5 + (x - 5) * u + depart * 12)
        yy = round(8 + (floor - 21) * u - depart * 15)
        wing = 2 if int(age * 8) % 2 else 1
        if kind == "butterflies":
            draw.ellipse((xx - wing - 2, yy - 2, xx, yy + 1), fill="#e9a0ca")
            draw.ellipse((xx, yy - 2, xx + wing + 2, yy + 1), fill="#c2b0ed")
        draw.point((xx, yy), fill="#ffe7a0")
    elif kind == "meteor" and active:
        # The same timeline drives target and gaze, including the waiting interval.
        sky(draw, "meteor", width, height, int(age * 8), obj.color)
    elif kind == "fireworks" and active and p > 0.3:
        sky(draw, "fireworks", width, height, int(age * 8), obj.color, seconds=age)
    elif kind == "confetti" and obj.name == "broom" and p < 0.3:
        # One burst preceding sweeping, not an endless replacement of swept paper.
        sky(draw, "confetti", width, height, int(age * 8), obj.color, seconds=age, seed=obj.id)
    elif kind == "hearts" and obj.name == "heart" and active and 0.25 < p < 0.8:
        xx, yy = x - 8, floor - 20 - round(8 * (p - 0.25))
        draw.line((xx - 2, yy, xx, yy + 2, xx + 2, yy), fill="#efa1c2", width=2)
    elif kind == "fog" and obj.data.get("lit", False):
        # A modest pool of warm light appears when the actual lamp is switched.
        draw.ellipse((x - 14, floor - 5, x + 10, floor + 1), fill=(194, 150, 70, 50))
    elif kind == "petals" and obj.name == "leaf":
        for i in range(round(5 * p)):
            draw.ellipse((x - 5 + i * 2, floor - 3, x - 3 + i * 2, floor - 1), fill="#eda1c3")
    elif kind == "snow" and obj.name in ("snowman", "snowball", "snowangel"):
        draw.line((x - 14, floor, x + 10, floor), fill="#dbeff2", width=2)
    elif kind in ("rain", "clouds", "hurricane", "tornado") and active:
        # Shelter becomes dry after closing, while outside precipitation continues.
        if obj.name == "window" and p > 0.6:
            draw.line((x - 12, floor, x + 8, floor), fill="#355065")
    return {key: im.resize((g.width, g.height), Image.Resampling.NEAREST)} if im.getbbox() else {}
