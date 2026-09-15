"""Contact-driven material and motion timelines for the living-world director.

Positions are local to one ground plane. Only the director calls advance after
arrival; drawing is a pure consumer. Durations include setup and cleanup.
"""

import math

DURATIONS = {
    "rake": 7.5,
    "sweep": 6,
    "harvest": 6,
    "drink": 7,
    "plant": 7,
    "water": 7,
    "fill_water": 5,
    "chase": 8,
    "roll_snow": 8,
    "drive": 8,
    "ride": 9,
    "fly": 10,
    "unwrap": 7,
    "aim": 8,
    "moonwatch": 8,
    "read_light": 9,
    "lullaby": 8,
    "catch_drips": 8,
}
DURABLE = {"acorn", "clover", "flower", "seedling", "tree", "snowman", "sandcastle", "rangoli"}


def duration(name, action):
    return DURATIONS.get(action, 6)


def advance(director, jelly, obj, dt):
    from .world_objects import DEFINITIONS

    action = DEFINITIONS[obj.name].action
    total = duration(obj.name, action)
    director.use_elapsed = min(total, director.use_elapsed + dt)
    p = obj.progress = director.use_elapsed / total
    obj.state = "in_use"
    data = obj.data
    data["phase"] = min(3, int(p * 4))
    # Every use starts from the same reached stance, never a moving previous frame.
    scale = jelly.geometry.scale
    floor = jelly.geometry.anchor(jelly.current)[1]
    jelly.y = floor
    if action in ("drink", "lick", "serve", "picnic", "unwrap_eat", "candles"):
        # First blow/unpack, then consume, then collect crumbs or wrapper.
        obj.amount = 1 - min(1, max(0, (p - 0.2) / 0.55))
        data["cleared"] = max(0, (p - 0.8) / 0.2)
        jelly.face = "happy" if 0.3 < p < 0.75 else "focused"
    elif action in ("water", "plant", "fill_water"):
        poured = min(1, max(0, (p - 0.2) / 0.6))
        director.water = 1 - poured if action != "fill_water" else poured
        obj.amount = poured
        data["moisture"] = poured
        if action == "plant":
            data["buried"] = min(1, p / 0.4)
        data["growth"] = min(1, data.get("previous_growth", 0) + poured * 0.3)
    elif action in ("rake", "sweep", "harvest"):
        cycle = director.use_elapsed % 1.5
        pulls = int(director.use_elapsed / 1.5) + min(1, cycle / 0.85)
        data["gathered"] = min(1, pulls / (total / 1.5))
    elif action in ("chase", "roll_snow", "drive"):
        # First contact, free deceleration, a visible pursuit, second contact,
        # then bring the toy back. Never roll a toy uphill between rows.
        u = min(1, max(0, (p - 0.12) / 0.4))
        outbound = 4 * (1 - (1 - u) ** 2)
        returned = min(1, max(0, (p - 0.72) / 0.28))
        data["offset"] = outbound * (1 - returned)
        data["angle"] = data["offset"] / 4
        chase = min(1, max(0, (p - 0.32) / 0.4))
        jelly.x = director.origin_x + scale * 4 * chase * (1 - returned)
        jelly.pose = "scoot_front" if 0.32 < p < 0.72 else "curious_lean"
        data["stopped"] = p >= 0.72
        if action == "roll_snow":
            data["radius"] = 3 + 3 * u
    elif action == "ride":
        board = min(1, p / 0.2)
        travel = min(1, max(0, (p - 0.2) / 0.5))
        dismount = min(1, max(0, (p - 0.72) / 0.15))
        retrieve = min(1, max(0, (p - 0.87) / 0.13))
        data["offset"] = 3 * (1 - (1 - travel) ** 2) * (1 - retrieve)
        data["boarded"] = 0.2 <= p <= 0.72
        center = jelly.geometry.anchor(jelly.current)[0]
        jelly.x = director.origin_x + (center - director.origin_x) * board * (1 - dismount) + scale * data["offset"]
        jelly.y = floor - scale * 5 * board * (1 - dismount)
        jelly.pose = "squash" if data["boarded"] else "idle"
    elif action == "fly":
        # Unfold, run, launch, hold against gusts, reel all the way in.
        data["height"] = 20 * min(1, max(0, (p - 0.12) / 0.22)) * (1 - min(1, max(0, (p - 0.7) / 0.3)))
        data["wind"] = math.sin(director.use_elapsed * 2) * min(1, data["height"] / 10)
        jelly.x = director.origin_x + scale * 4 * math.sin(min(1, p / 0.3) * math.pi)
        jelly.gaze = "up"
        data["folded"] = p >= 0.98
    elif action in ("spin", "spin_globe", "blow", "switch_fan"):
        data["turn"] = 18 * (1 - (1 - min(1, max(0, (p - 0.1) / 0.8))) ** 3)
        data["stopped"] = p > 0.9
        jelly.gaze = "right"
    elif action in ("splash", "snow_angel"):
        jelly.pose = "puddle" if action == "snow_angel" else "rebound"
        jelly.y = floor - (scale * 5 * abs(math.sin(p * math.tau * 2)) if action == "splash" else 0)
        data["contact"] = abs(jelly.y - floor) < scale * 1.5
        data["imprint"] = min(1, p * 1.5)
    elif action in ("aim", "moonwatch", "shelter", "lullaby"):
        jelly.gaze, jelly.face = "up", "curious"
    elif action == "unwrap":
        data["lid"] = min(1, p / 0.5)
        data["wrapping"] = max(0, 1 - (p - 0.65) / 0.35)
    elif action in ("build_sand", "build_snow"):
        data["tier"] = min(3, int(p * 4))
    elif action == "launch":
        flight = min(1, max(0, (p - 0.2) / 0.6))
        data["height"] = 25 * math.sin(math.pi * flight)
        data["landed"] = p >= 0.8
        jelly.gaze = "up" if 0.2 < p < 0.8 else "down"
    elif action == "close_window":
        data["opening"] = p if director.sky == "sunrise" else 1 - p
    elif action == "catch_drips":
        obj.amount = p
        data["ice"] = 1 - p * 0.35
    elif action in ("tend_wick", "light_candles", "tend_pumpkin", "hang", "read_light"):
        data["lit"] = p > 0.2 and not (action == "read_light" and p > 0.9)
        if action == "read_light" and 0.35 < p < 0.85:
            jelly.pose, jelly.face = "sleep_curl", "half"
    elif action == "wind_clock":
        data["hand"] = p * math.tau
        jelly.face = "surprised" if 0.75 < p < 0.85 else "curious"
    elif action == "catch_flake":
        data["height"] = max(0, 12 * (1 - p * 2))
        obj.amount = max(0, 1 - max(0, p - 0.5) * 2)
    elif action == "lullaby":
        jelly.pose = "sleep_curl"
    if director.sky in ("fireflies", "butterflies") and 0.4 < p < 0.85:
        jelly.gesture, jelly.pose, jelly.gaze = "", "idle", "up"
    if director.sky in ("meteor", "fireworks") and action in ("aim", "launch"):
        jelly.gaze = "up"
        if director.sky == "fireworks" and int(director.use_elapsed * 2) % 6 == 0:
            jelly.pose = "squash"
    if director.sky == "rainbow" and p > 0.7:
        jelly.gaze, jelly.pose = "up", "proud"
    if director.sky == "sunrise" and p < 0.25:
        jelly.pose = "stretch"
    return director.use_elapsed >= total
