"""Composite production renderers into photographed LCDs; no network at render time.

Photo sources and calibration notes: docs/hardware/README.md.
"""

from pathlib import Path
import sys
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw, ImageFont
from ocdeck.appearance import Appearance, PRESETS, animation_phase
from ocdeck.art import frame as agent_frame
from ocdeck.jelly import DeckGeometry, Jelly
from ocdeck.world import World
from ocdeck.world_settings import settings
from ocdeck.world_weather import WeatherService

OUT = ROOT / "docs/hardware"
FPS = 12
# Photo-native screen rectangles. Row-specific spacing follows photographic perspective.
MODELS = {
    "mini": (2, 3, (105, 170, 1095, 785), [(309, 289, 214, 158, 108), (299, 450, 219, 165, 116)]),
    "mk2": (
        3,
        5,
        (68, 325, 1530, 1245),
        [(265, 489, 226, 166, 126), (253, 672, 231, 174, 128), (239, 856, 237, 177, 133)],
    ),
    "xl": (
        4,
        8,
        (30, 285, 1170, 865),
        [(163, 391, 113, 82, 58), (155, 480, 115, 85, 58), (148, 567, 116, 86, 61), (141, 657, 118, 88, 64)],
    ),
}
NAMES = {"mini": "Stream Deck Mini", "mk2": "Stream Deck MK.2", "xl": "Stream Deck XL"}
HARNESSES = ("opencode", "claude", "codex", "copilot", "gemini", "cursor")


def font(size, bold=False):
    path = "/usr/share/fonts/truetype/dejavu/DejaVuSans" + ("-Bold" if bold else "") + ".ttf"
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default(size=size)


def photo(model, tiles):
    rows, cols, crop, screens = MODELS[model]
    im = Image.open(OUT / (model + ".jpg")).convert("RGB")
    if model == "mk2":
        im = im.resize((1600, 1600), Image.Resampling.LANCZOS)
    for key, tile in tiles.items():
        row, col = divmod(key, cols)
        x, y, step, w, h = screens[row]
        mask = Image.new("L", (w, h))
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=12, fill=255)
        im.paste(tile.resize((w, h), Image.Resampling.NEAREST), (x + col * step, y), mask)
    return im.crop(crop)


def card(model, tiles, title, subtitle):
    im = Image.new("RGB", (1200, 700), "white")
    d = ImageDraw.Draw(im)
    d.text((52, 32), "AGENTSTREAMDECK", font=font(16, True), fill="#17786e")
    d.text((50, 68), title, font=font(38, True), fill="#101c2c")
    d.text((52, 121), subtitle, font=font(18), fill="#526174")
    device = photo(model, tiles)
    device.thumbnail((1060, 435), Image.Resampling.LANCZOS)
    im.paste(device, ((1200 - device.width) // 2, 179 + (435 - device.height) // 2))
    d.text(
        (52, 650),
        NAMES[model] + f"  /  {MODELS[model][0] * MODELS[model][1]} keys",
        font=font(18, True),
        fill="#182536",
    )
    d.text((1148, 655), "Actual UI rendered onto a product photo", anchor="ra", font=font(13), fill="#697587")
    return im


def segment(model, scene, title, subtitle, seconds=4, appearance=False):
    rows, cols, _, _ = MODELS[model]
    size = {"mini": 80, "mk2": 72, "xl": 96}[model]
    g = DeckGeometry(rows, cols, size, size)
    j = Jelly(g, seed=6, options={"thoughts": "off", "needs": False})
    occupied = cols if not appearance else g.count
    free = set(range(occupied, g.count))
    j.settle(occupied if free else 0, 0)
    o = settings(dict(scene_override=scene, auto_location=False, weather=False, captions=False))
    world = World(o, WeatherService(o))
    warmup = 0
    for i in range(warmup + round(FPS * seconds)):
        now = i / FPS
        j.update(now, free)
        world.tick(now, j, free)
        crops = world.decorate(now, j, j.crops(free), free)
        if i < warmup:
            continue
        tiles = {}
        for key in range(g.count):
            if key < occupied:
                style = Appearance(layout="harness", show_slot=False)
                if appearance:
                    # Each row compares the same three motion styles; columns vary presets.
                    style = Appearance(**list(PRESETS.values())[key % 5])
                    style = replace(style, effect=("breathe", "glow", "steady")[key // cols % 3], alias="Builder")
                tiles[key] = agent_frame(
                    ("running", "idle", "input")[key % 3],
                    ("API", "WEB", "TEST")[key % 3],
                    key,
                    animation_phase(now, style),
                    size,
                    style,
                    HARNESSES[key % 6],
                )
            else:
                tile = Image.new("RGB", (size, size), "#050910")
                if key in crops:
                    tile.paste(crops[key], (0, 0), crops[key])
                tiles[key] = tile
        yield card(model, tiles, title, subtitle)


def save(path, frames):
    frames = list(frames)
    # Sample the entire reel for a stable palette, preventing frame-to-frame color shimmer.
    sheet = Image.new("RGB", (300, 175 * len(frames[::12])))
    for i, f in enumerate(frames[::12]):
        sheet.paste(f.resize((300, 175)), (0, i * 175))
    palette = sheet.quantize(colors=256)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    indexed[0].save(
        path,
        save_all=True,
        append_images=indexed[1:],
        duration=[80, 80, 90] * ((len(indexed) + 2) // 3) if len(indexed) % 3 == 0 else 83,
        loop=0,
        optimize=True,
    )
    print(path.relative_to(ROOT), path.stat().st_size)
    return frames


def main():
    hero = []
    for model, scene, title, sub, appearance in [
        (
            "mini",
            "rain",
            "Your agents. One glance away.",
            "Live status, one-touch focus, and a little companion on your spare keys.",
            False,
        ),
        (
            "mk2",
            "autumn_rake",
            "Make every button your own.",
            "Studio / Neon / Focus / Readable / Marquee   •   Breathe / Glow / Steady",
            True,
        ),
        (
            "xl",
            "winter_snowball",
            "More room for work. And wonder.",
            "32 keys for your sessions, with holidays and a living world in the free space.",
            False,
        ),
    ]:
        frames = list(segment(model, scene, title, sub, appearance=appearance))
        hero.extend(frames)
        save(OUT / (model + "-showcase.gif"), frames)
        frames[12].save(OUT / (model + "-showcase.png"))
    save(ROOT / "docs/jelly/readme_hero.gif", hero)
    weather = []
    for scene, title, sub in [
        (
            "rain",
            "Rain that falls and splashes.",
            "Individual drops, varied speed, and little impacts on the key floor.",
        ),
        ("winter_snowball", "A little winter on your desk.", "Drifting snow and a playful seasonal companion."),
        (
            "autumn_rake",
            "Leaves fall. Jelly gets to work.",
            "Fluttering leaves, grounded props, and purposeful activities.",
        ),
    ]:
        weather.extend(segment("mini", scene, title, sub, seconds=6))
    save(OUT / "weather-showcase.gif", weather)


if __name__ == "__main__":
    main()
