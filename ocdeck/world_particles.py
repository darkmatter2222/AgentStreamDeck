"""Deterministic, elapsed-time atmosphere with independent lifetimes per key.

No mutable particle pool, frame-count integration, shared RNG or I/O. A particle
lands on its own viewport floor; recycling happens only after its impact fades.
"""

from dataclasses import dataclass
from functools import lru_cache
import math

FALLING = frozenset(("rain", "snow", "leaves", "petals", "confetti"))
LOCAL = FALLING | {
    "smoke",
    "fog",
    "wind",
    "fireflies",
    "butterflies",
    "clouds",
    "balloons",
    "hearts",
    "fireworks",
    "fountain",
    "tornado",
    "hurricane",
}


@lru_cache(maxsize=4096)
def noise(seed, index, channel=0):
    value = (seed * 374761393 + index * 668265263 + channel * 2246822519 + 1274126177) & 0xFFFFFFFF
    value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((value ^ (value >> 16)) & 0xFFFFFFFF) / 4294967296


@dataclass(frozen=True)
class Particle:
    index: int
    cycle: int
    stage: str
    x: float
    y: float
    progress: float
    size: int
    alpha: int
    tilt: float
    depth: float


def particles(kind, width, height, seconds, seed=0, density=1):
    """Sample falling material, including contact and a finite ground lifetime."""
    if kind not in FALLING:
        raise ValueError("Not a falling material: " + kind)
    if width < 1 or height < 1:
        return ()
    count = max(3, min(24, round(width * height / (210 if kind == "rain" else 350 if kind == "snow" else 650))))
    count = max(0, min(64, round(count * density)))
    floor = height - 3
    result = []
    for i in range(count):
        depth = noise(seed, i, 1)
        speed = (85 + 95 * depth) if kind == "rain" else (10 + 12 * depth) if kind == "snow" else (10 + 8 * depth)
        fall = (height + 10) / speed
        contact = 0.24 if kind == "rain" else 0.35
        resting = 0 if kind == "rain" else 1.1 if kind == "snow" else 2.4 + noise(seed, i, 2) * 1.8
        lifetime = fall + contact + resting + 0.25
        clock = max(0, seconds) + noise(seed, i, 3) * lifetime
        cycle = math.floor(clock / lifetime)
        age = clock - cycle * lifetime
        # Each renewal gets a fresh start location, after the old image is gone.
        salt = i + cycle * 97
        base = 4 + noise(seed, salt, 4) * max(1, width - 9)
        drift = (noise(seed, i, 5) - 0.5) * (3 if kind == "rain" else 5)
        size = (1 if depth < 0.55 else 2) if kind in ("rain", "snow") else (2 if depth < 0.5 else 3)
        tilt = math.sin(age * (6 + noise(seed, i, 8) * 3) + i)
        if age < fall:
            u = age / fall
            sway = 0 if kind == "rain" else math.sin(age * 2.4 + i * 1.7) * (2 if kind == "snow" else 4)
            x = base + drift * u + sway * math.sin(math.pi * u)
            y = -8 + (floor + 8) * u
            result.append(Particle(i, cycle, "fall", x, y, u, size, round(120 + 110 * depth), tilt, depth))
        elif age < fall + contact:
            u = (age - fall) / contact
            result.append(
                Particle(
                    i,
                    cycle,
                    "impact",
                    base + drift,
                    floor,
                    u,
                    size,
                    round(210 * (1 - u)) if kind == "rain" else round(120 + 110 * depth),
                    tilt,
                    depth,
                )
            )
        elif resting and age < fall + contact + resting:
            u = (age - fall - contact) / resting
            alpha = round((165 + 65 * depth) * (1 - max(0, (u - 0.45) / 0.55)))
            result.append(Particle(i, cycle, "rest", base + drift, floor, u, size, alpha, 0, depth))
    return tuple(result)


@lru_cache(maxsize=64)
def rgb(hex_color):
    return tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))


def rgba(hex_color, alpha):
    return (*rgb(hex_color), max(0, min(255, round(alpha))))


def draw_falling(draw, kind, width, height, seconds, seed=0, density=1):
    for p in particles(kind, width, height, seconds, seed, density):
        x, y = round(p.x), round(p.y)
        a = p.alpha
        if kind == "rain":
            color = rgba("#82bddb" if p.depth > 0.5 else "#49768f", a)
            if p.stage == "fall":
                length = 2 + round(p.depth * 4)
                # Small beads, short streaks and brighter foreground drops.
                draw.line((x, y - length, x - 1, y), fill=color)
                if p.size == 2:
                    draw.point((x - 1, y), fill=rgba("#c5e6ed", a))
            else:
                radius = 1 + round(p.progress * 4)
                rise = round(3 * math.sin(math.pi * p.progress))
                draw.point((x - radius, y - rise), fill=color)
                draw.point((x + radius, y - rise), fill=color)
                if p.progress < 0.7:
                    draw.point((x, y - 1), fill=color)
                if p.progress > 0.4:
                    draw.line((x - 1, y, x + 1, y), fill=rgba("#618b9f", a * 0.7))
        elif kind == "snow":
            color = rgba("#d6ebef" if p.depth > 0.4 else "#799baa", a)
            if p.stage == "fall":
                draw.point((x, y), fill=color)
                if p.size == 2:
                    draw.line((x - 1, y, x + 1, y), fill=color)
                    draw.line((x, y - 1, x, y + 1), fill=color)
                    if p.index % 4 == 0:
                        draw.point((x - 1, y - 1), fill=rgba("#accdd9", a * 0.7))
            else:
                draw.line((x - p.size, y, x + p.size, y), fill=color)
                if p.stage == "impact":
                    draw.point((x + round(p.progress * 3), y - 1), fill=color)
        else:
            colors = (
                ("#ca8148", "#dcaa60", "#ad6343")
                if kind == "leaves"
                else ("#dc9eb9", "#edbed2", "#b989b5")
                if kind == "petals"
                else ("#dd8c9e", "#d8b36a", "#78b5c8", "#7fc59b")
            )
            color = rgba(colors[p.index % len(colors)], a)
            if p.stage != "fall":
                # Sideways silhouette, then pigment fades rather than sinking.
                flatten = 1 if p.stage == "rest" else max(1, round(2 * (1 - p.progress)))
                draw.polygon([(x - p.size, y), (x - 1, y - flatten), (x + p.size + 1, y), (x, y + 1)], fill=color)
                if kind == "leaves":
                    draw.line((x - 1, y, x + p.size + 2, y), fill=rgba("#97754d", a))
            elif kind == "leaves":
                span = max(1, round(p.size * abs(p.tilt)))
                draw.polygon(
                    [
                        (x, y - p.size),
                        (x + span, y - 1),
                        (x + span + 1, y + 1),
                        (x, y + p.size),
                        (x - span, y + 1),
                        (x - span, y - 1),
                    ],
                    fill=color,
                )
                draw.line((x, y - p.size + 1, x, y + p.size + 1), fill=rgba("#e5b776", a))
            elif kind == "petals":
                draw.polygon([(x - 1, y - 2), (x + 2, y - 1), (x + round(p.tilt), y + 2), (x - 1, y + 1)], fill=color)
            else:
                draw.line((x, y, x + round(2 * p.tilt), y + 1), fill=color)


def atmosphere(draw, kind, width, height, seconds, seed=0, density=1):
    """Natural local effects; return False for authored celestial/fixture motifs."""
    if kind in FALLING:
        draw_falling(draw, kind, width, height, seconds, seed, density)
        return True
    if kind not in LOCAL:
        return False
    t = max(0, seconds)
    count = max(2, min(9, round(width * height / 650)))
    for i in range(count):
        n = lambda channel: noise(seed, i, channel)
        offset = n(0) * 20
        if kind in ("smoke", "fog", "clouds"):
            if kind == "clouds":
                if i >= max(1, width // 45):
                    continue
                from .world_props import cloud

                x = (n(1) * (width + 38) + t * (1.5 + n(2) * 2)) % (width + 38) - 19
                cloud(draw, round(x), round(12 + n(3) * max(1, height * 0.3)))
                continue
            life = 5 + n(1) * 4
            age = (t + offset) % life
            u = age / life
            alpha = round((55 if kind == "fog" else 115) * math.sin(math.pi * u))
            x = n(2) * width + math.sin(age * 0.7 + i) * 3 + (age * 1.5 if kind == "fog" else 0)
            y = height - 5 - n(4) * 10 if kind == "fog" else height - 8 - u * (height * 0.65)
            radius = round(3 + u * (10 if kind == "fog" else 5))
            # Broken wisps with separate birth/death, no full-width strip.
            draw.arc(
                (round(x - radius), round(y - 2), round(x + radius), round(y + 2)),
                175,
                330,
                fill=rgba("#8fa5b5", alpha),
            )
        elif kind == "wind":
            life = 2 + n(1) * 2
            age = (t + offset) % life
            x = -8 + (width + 16) * age / life
            y = 6 + n(2) * max(1, height - 14) + math.sin(age * 2 + i) * 2
            alpha = 100 * math.sin(math.pi * age / life)
            draw.line((round(x - 2), round(y), round(x), round(y)), fill=rgba("#789bab", alpha))
            draw.point((round(x - 6), round(y + 1)), fill=rgba("#789bab", alpha * 0.5))
        elif kind in ("fireflies", "butterflies"):
            x = 5 + n(1) * max(1, width - 10) + math.sin(t * (0.5 + n(2)) + i) * 4
            y = 7 + n(3) * max(1, height - 17) + math.sin(t * 0.8 + i * 2) * 3
            x, y = round(x), round(y)
            if kind == "fireflies":
                a = 45 + 190 * max(0, math.sin(t * (1 + n(4)) + offset)) ** 3
                draw.point((x, y), fill=rgba("#e8cb79", a))
                if a > 160:
                    draw.point((x + 1, y), fill=rgba("#a4b871", a * 0.4))
            else:
                wing = max(1, round(3 * abs(math.sin(t * (8 + n(5) * 4) + offset))))
                draw.ellipse((x - wing, y - 2, x - 1, y + 1), fill=rgba("#ca9bbd", 200))
                draw.ellipse((x + 1, y - 2, x + wing, y + 1), fill=rgba("#dfbd80", 200))
                draw.line((x, y - 1, x, y + 1), fill="#64818e")
        elif kind in ("balloons", "hearts"):
            life = 6 + n(1) * 5
            age = (t + offset) % life
            u = age / life
            x = round(6 + n(2) * max(1, width - 12) + math.sin(age + i) * 2)
            y = round(height + 8 - u * (height + 18))
            a = 220 * min(1, u * 6, (1 - u) * 6)
            if kind == "balloons":
                draw.ellipse((x - 3, y - 5, x + 3, y + 3), fill=rgba(("#ba748f", "#80b4c1", "#d7b57a")[i % 3], a))
                draw.line((x, y + 4, x + round(math.sin(age * 2)), y + 9), fill=rgba("#91a7b5", a * 0.8))
            else:
                draw.polygon(
                    [(x, y + 2), (x - 3, y - 1), (x - 2, y - 3), (x, y - 1), (x + 2, y - 3), (x + 3, y - 1)],
                    fill=rgba("#cc8296", a),
                )
        elif kind in ("tornado", "hurricane"):
            for speck in range(5):
                u = (n(speck + 10) + t * (0.14 + n(7) * 0.08)) % 1
                radius = (3 + (1 - u) * 11) if kind == "tornado" else 10 + 3 * math.sin(u * math.pi)
                angle = t * (3 + n(6)) + n(speck + 20) * math.tau + u * 5
                x = round(width / 2 + math.cos(angle) * radius)
                y = round(7 + u * max(1, height - 12))
                draw.point((x, y), fill=rgba("#8ba2b0", 65 + 100 * (1 + math.sin(angle)) / 2))
        elif kind in ("fireworks", "fountain"):
            if i >= max(1, width // 50):
                continue
            life = 3.2 + n(1) * 1.8
            age = (t + offset) % life
            cx = round(8 + n(2) * max(1, width - 16))
            floor = height - 3
            if kind == "fireworks":
                cy = round(10 + n(3) * max(1, height * 0.35))
                if age < 0.65:
                    y = round(floor - (floor - cy) * age / 0.65)
                    draw.line((cx, y, cx, y + 3), fill="#d2ba82")
                    continue
                if age > 2.5:
                    continue
                age -= 0.65
                for spark in range(11):
                    a = spark * math.tau / 11 + n(4)
                    v = 7 + noise(seed, i * 17 + spark, 7) * 7
                    x = round(cx + math.cos(a) * v * age)
                    y = round(cy + math.sin(a) * v * age + 4 * age * age)
                    draw.point((x, y), fill=rgba(("#db9bb2", "#e0c080", "#8dbbcf")[spark % 3], 220 * (1 - age / 1.85)))
            else:
                for spark in range(7):
                    a = (t * 1.4 + noise(seed, spark + i * 11, 8)) % 1
                    vx = (noise(seed, spark + i * 11, 9) - 0.5) * 20
                    x = round(cx + vx * a)
                    y = round(floor - 36 * a + 36 * a * a)
                    draw.point((x, y), fill=rgba("#e1c58c", 220 * (1 - a)))
    return True
