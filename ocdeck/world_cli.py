"""All world controls are available through CLI and the same validated INI schema."""

import argparse
import configparser
import io
import json
import os
from pathlib import Path
import tempfile
from .common import home, load_config
from .world_settings import DEFAULTS, read_ini, settings
from .world_catalog import SCENES


def add_parser(sub):
    parser = sub.add_parser("world", help="Configure Jelly holidays, weather and seasonal scenes")
    actions = parser.add_subparsers(dest="world_command", required=True)
    configure = actions.add_parser("configure", help="Save jelly.ini; restart broker to apply")
    for key, value in DEFAULTS.items():
        kwargs: dict = {"default": None}
        if type(value) is bool:
            kwargs["action"] = argparse.BooleanOptionalAction
        else:
            kwargs["type"] = int if type(value) is int else str
        configure.add_argument("--" + ("hold-help" if key == "help" else key.replace("_", "-")), dest=key, **kwargs)
    actions.add_parser("reset", help="Reset world memory on next broker restart; preserve Jelly needs")
    actions.add_parser("show", help="Show effective world settings")
    actions.add_parser("catalog", help="List scene IDs, contexts and artwork recipes")
    actions.add_parser("validate", help="Validate world settings without network access")
    preview = actions.add_parser("preview", help="Render an offline scene GIF")
    preview.add_argument("scene", choices=sorted(SCENES))
    preview.add_argument("--output", required=True)
    preview.add_argument("--keys", type=int, choices=(6, 15, 32), default=6)


def save(root, value):
    value = settings(value)
    parser = configparser.ConfigParser(interpolation=None)
    parser["world"] = {k: str(v).lower() if type(v) is bool else str(v) for k, v in value.items()}
    stream = io.StringIO()
    parser.write(stream)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=root, prefix=".jelly-", suffix=".ini")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(stream.getvalue())
        os.replace(temp, root / "jelly.ini")
    finally:
        Path(temp).unlink(missing_ok=True)


def preview(scene, output, count=6):
    from .jelly import Jelly, DeckGeometry
    from .world import World
    from .world_weather import WeatherService
    from PIL import Image

    rows, cols = {6: (2, 3), 15: (3, 5), 32: (4, 8)}[count]
    g = DeckGeometry(rows, cols)
    options = settings(dict(scene_override=scene, auto_location=False, weather=False, captions=False))
    world = World(options, WeatherService(options))
    jelly = Jelly(g, seed=1, options={"thoughts": "off", "needs": False, "travel": "rare"})
    jelly.settle(cols, 0)
    images = []
    for frame in range(168):
        now = frame / 12
        jelly.update(now, set(range(count)))
        world.tick(now, jelly, set(range(count)))
        crops = world.decorate(now, jelly, jelly.crops(set(range(count))), set(range(count)))
        im = Image.new("RGB", g.size, "#09111b")
        for key in range(count):
            tile = Image.new("RGBA", (g.width, g.height), "#050910")
            if key in crops:
                tile.alpha_composite(crops[key])
            im.paste(tile.convert("RGB"), g.bounds(key)[:2])
        images.append(im)
    images[0].save(output, save_all=True, append_images=images[1:], duration=83, loop=0)


def run(args):
    from dataclasses import asdict

    if args.world_command == "catalog":
        print(json.dumps({k: asdict(v) for k, v in SCENES.items()}, indent=2))
        return 0
    if args.world_command == "preview":
        preview(args.scene, args.output, args.keys)
        print(str(Path(args.output).resolve()))
        return 0
    root = home()
    if args.world_command == "reset":
        from uuid import uuid4
        from .common import atomic_json

        atomic_json(root / "world-reset.json", {"generation": uuid4().hex})
        print("World memory reset scheduled. Restart the broker to apply; Jelly needs are preserved.")
        return 0
    value = settings({**load_config(root).get("world", {}), **read_ini(root)})
    if args.world_command == "configure":
        value.update({k: getattr(args, k) for k in DEFAULTS if getattr(args, k) is not None})
        save(root, value)
        print("Saved jelly.ini. Restart the broker to apply.")
        return 0
    if args.world_command == "validate":
        print("World settings valid. No network requests made.")
    else:
        print(json.dumps(value, indent=2))
    return 0
