"""World costume overlays and atmosphere, kept separate from Jelly body art."""

import math
from PIL import ImageDraw
from .world_props import prop, cloud, wave, INK, WHITE, GOLD, PINK, GREEN, BLUE


def costume(image, name, phase, head):
    """Draw on a logical 40px sprite; preserve eyes and floor-contact anatomy."""
    if not name:
        return image
    im = image.copy()
    d = ImageDraw.Draw(im)
    y = max(4, head)
    sway = wave(phase)
    if name in ("santa", "elf", "party", "witch", "nightcap"):
        color = {"santa": PINK, "elf": GREEN, "party": GOLD, "witch": "#8055b9", "nightcap": BLUE}[name]
        if name == "party":
            d.polygon([(13, y), (20, y - 11), (27, y)], fill=color, outline=INK)
            for x, h in ((17, -2), (21, -5), (23, -1)):
                d.point((x, y + h), fill=PINK)
            d.line((20, y - 12, 20 + sway, y - 14), fill=PINK)
        elif name == "witch":
            d.polygon([(12, y), (17, y - 10), (23, y - 11), (22, y - 7), (28, y)], fill=color, outline=INK)
            d.line((8, y + 1, 32, y + 1), fill=INK, width=2)
            d.line((13, y - 1, 27, y - 1), fill="#bd8c50", width=2)
            d.rectangle((19, y - 2, 22, y), outline=GOLD)
        else:
            d.polygon(
                [
                    (11, y),
                    (17, y - 9),
                    (23, y - 10),
                    (28, y - 6),
                    (29 + sway, y - 2),
                    (25 + sway, y - 3),
                    (22, y - 6),
                    (27, y),
                ],
                fill=color,
                outline=INK,
            )
            d.line([(13, y - 2), (18, y - 7), (21, y - 8)], fill=WHITE if name == "santa" else "#a7d4d2")
            d.ellipse((27 + sway, y - 3, 30 + sway, y), fill=WHITE if name != "elf" else GOLD)
            d.line((10, y, 28, y), fill=WHITE if name == "santa" else GOLD, width=2)
            if name == "nightcap":
                d.point((19, y - 4), fill=WHITE)
    elif name in ("beanie", "sunhat", "gardener"):
        if name == "beanie":
            d.pieslice((11, y - 9, 29, y + 7), 180, 360, fill=PINK, outline=INK)
            for x in (15, 19, 23, 27):
                d.line((x, y - 4, x, y - 1), fill="#c76580")
            d.line((11, y, 29, y), fill="#f5c5cd", width=3)
            d.ellipse((18 + sway, y - 11, 22 + sway, y - 7), fill="#f5c5cd")
        else:
            d.pieslice((12, y - 7, 28, y + 5), 180, 360, fill="#d2af71", outline=INK)
            d.line((13, y - 1, 27, y - 1), fill=GREEN if name == "gardener" else PINK, width=2)
            d.line((7, y + 1, 33, y + 1), fill=GOLD, width=2)
            d.line((10, y + 2, 30, y + 2), fill="#a78453")
    elif name == "bunny":
        d.ellipse((12, y - 12, 17, y + 1), fill=WHITE)
        d.ellipse((23, y - 12, 28, y + 1), fill=WHITE)
        d.line((14, y - 9, 14, y - 2), fill=PINK)
        d.line((25, y - 9, 25, y - 2), fill=PINK)
        d.line((12, y - 4, 12, y - 1), fill="#8eacb9")
    elif name == "ghost":
        # A translucent sheet with cutout eyes; hover is applied in the controller.
        d.polygon(
            [
                (8, 32),
                (10, y + 3),
                (16, y - 2),
                (24, y - 2),
                (30, y + 3),
                (33, 32),
                (28, 29),
                (24, 33),
                (20, 30),
                (15, 33),
            ],
            fill="#d5eee8",
        )
        d.ellipse((15, y + 6, 18, y + 10), fill=INK)
        d.ellipse((23, y + 6, 26, y + 10), fill=INK)
        d.line([(11, y + 10), (10, 29), (13, 30)], fill="#9ebdc5")
        d.line([(28, y + 11), (30, 28), (28, 29)], fill="#9ebdc5")
    elif name == "skeleton":
        d.line((20, 25, 20, 32), fill=WHITE)
        for h in (26, 29):
            d.line([(14, h), (17, h + 1), (23, h + 1), (26, h)], fill=WHITE)
    elif name == "reaper":
        d.line([(8, 29), (10, y + 2), (20, y - 4), (30, y + 2), (32, 29)], fill="#8055b9", width=4)
    elif name in ("mask", "shades"):
        d.rectangle((12, y + 7, 28, y + 10), fill="#8055b9" if name == "mask" else INK)
        d.point((15, y + 8), fill=WHITE)
        d.point((24, y + 8), fill=WHITE)
        d.line((13, y + 7, 15, y + 7), fill="#91b6c8")
        d.line((23, y + 7, 25, y + 7), fill="#91b6c8")
    elif name == "scarf":
        d.line((10, 32, 30, 32), fill=PINK, width=2)
        d.line((28, 32, 30 + sway, 35), fill=PINK, width=2)
        d.line((12, 31, 27, 31), fill="#ffc1cb")
        d.point((30 + sway, 36), fill=GOLD)
    elif name == "bow":
        d.polygon([(12, y), (18, y + 3), (12, y + 6), (24, y), (18, y + 3), (24, y + 6)], fill=PINK, outline="#a55c79")
        d.rectangle((17, y + 2, 19, y + 4), fill="#ffc1cb")
    elif name == "sweat":
        drop_y = y + 4 + phase % 4
        d.polygon([(30, drop_y), (28, drop_y + 3), (30, drop_y + 5), (32, drop_y + 3)], fill=BLUE)
        d.point((29, drop_y + 3), fill=WHITE)
    elif name == "umbrella":
        d.pieslice((5, 0, 35, 20), 180, 360, fill="#c4a7ff", outline=INK)
        d.line((20, 9, 20, y + 2), fill=WHITE)
        d.arc((11, 0, 29, 20), 180, 360, fill="#ebe2ff")
        d.line((20, 1, 20, 9), fill="#ebe2ff")
        d.line((6, 9, 34, 9), fill="#826eae")
    elif name == "boots":
        d.rectangle((9, 31, 16, 34), fill=GOLD)
        d.rectangle((24, 31, 31, 34), fill=GOLD)
        d.line((9, 34, 16, 34), fill=INK)
        d.line((24, 34, 31, 34), fill=INK)
        d.point((11, 32), fill=WHITE)
        d.point((26, 32), fill=WHITE)
    else:
        raise ValueError("Missing world costume: " + name)
    return im


def sky(draw, kind, width, height, phase, color, density=1, *, seconds=None, seed=0):
    """Elapsed-time local particles plus authored stars and supported fixtures."""
    from .world_particles import atmosphere

    if atmosphere(draw, kind, width, height, phase / 8 if seconds is None else seconds, seed, density):
        return
    p = phase
    if kind == "stars":
        count = max(3, width * height // 1100) * density
        for i in range(count):
            # Fixed coordinates are essential: a starfield must not look like rain.
            x, y = (i * 47 + 9) % width, (i * 29 + 6) % max(1, height - 10)
            bright = (p // 2 + i * 3) % 12 < 3
            draw.point((x, y), fill=GOLD if bright else "#61788e")
            if bright and i % 4 == 0:
                draw.line((x - 1, y, x + 1, y), fill=GOLD)
                draw.line((x, y - 1, x, y + 1), fill=WHITE)
    elif kind in ("lights", "lanterns", "icicles"):
        for y in range(3, height, 48):
            for x in range(0, width, 24):
                draw.line([(x, y), (x + 6, y + 2), (x + 12, y + 3), (x + 18, y + 2), (x + 24, y)], fill="#43536a")
                if kind == "icicles":
                    for dx, h in ((5, 5), (12, 9), (19, 6)):
                        draw.polygon([(x + dx - 1, y + 2), (x + dx + 2, y + 2), (x + dx, y + h)], fill="#8bb6cc")
                        draw.point((x + dx, y + 3), fill=WHITE)
                    if p % 8 < 2:
                        draw.point((x + 12, y + 8), fill=WHITE)
                elif kind == "lanterns":
                    draw.line((x + 12, y + 3, x + 12, y + 5), fill=GOLD)
                    draw.ellipse((x + 8, y + 5, x + 16, y + 13), fill="#ba5864", outline=INK)
                    draw.line((x + 12, y + 6, x + 12, y + 12), fill=GOLD if p % 8 < 5 else "#dca460", width=2)
                    draw.line((x + 12, y + 14, x + 12 + wave(p), y + 16), fill=GOLD)
                else:
                    for dx in (6, 18):
                        c = (PINK, GOLD, GREEN, BLUE)[(x // 6 + dx // 6) % 4]
                        draw.rectangle((x + dx, y + 3, x + dx + 1, y + 5), fill=c)
                        if (p // 3 + x + dx) % 8 < 2:
                            draw.point((x + dx, y + 4), fill=WHITE)
    elif kind in ("sun", "sunrise"):
        x, y = width - 13, 10
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#d5a563")
        draw.ellipse((x - 5, y - 5, x + 4, y + 4), fill=GOLD)
        draw.line((x - 3, y - 3, x, y - 4), fill="#ffe8aa")
        for i in range(8):
            a = i * math.pi / 4
            r = 9 + (1 if (p // 4 + i) % 8 < 2 else 0)
            draw.line(
                (
                    round(x + r * math.cos(a)),
                    round(y + r * math.sin(a)),
                    round(x + (r + 2) * math.cos(a)),
                    round(y + (r + 2) * math.sin(a)),
                ),
                fill="#b59059",
            )
        if kind == "sunrise":
            for i in range(3):
                draw.line((x - 16 + i * 4, y + 6 + i * 3, x + 16 - i * 4, y + 6 + i * 3), fill="#675264")
    elif kind == "rainbow":
        # A small sky arc, never a full-deck opaque wash.
        cx = width // 2
        for i, c in enumerate(("#b77181", "#b99a62", "#639e85", "#638eaf", "#8b7daa")):
            draw.arc((cx - 28 + i * 2, 5 + i * 2, cx + 28 - i * 2, 49 - i * 2), 180, 360, fill=c, width=2)
        cloud(draw, cx - 27, 29)
        cloud(draw, cx + 27, 29)
        draw.point((cx - 15 + (p // 3) % 4, 33), fill="#719cad")
    elif kind == "meteor":
        sky(draw, "stars", width, height, p, color, density)
        age = p % 48
        if age < 20:
            x = round(width * age / 20)
            y = 5 + age // 2
            for tail in range(9):
                draw.point((x - tail, y - tail // 2), fill=(WHITE, GOLD, "#a98963", "#5e5961")[min(3, tail // 2)])
    elif kind:
        raise ValueError("Missing world sky: " + kind)


WOOD_COLOR = "#a98c68"
