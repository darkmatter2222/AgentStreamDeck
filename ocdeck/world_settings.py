"""Strict world configuration, shared by INI, CLI and the broker."""

import configparser
import math
from pathlib import Path
from zoneinfo import ZoneInfo
from .world_catalog import SCENES

DEFAULTS: dict = dict(
    enabled=True,
    living_world=True,
    holidays=True,
    weather=True,
    seasons=True,
    costumes=True,
    particles=True,
    props=True,
    interactions=True,
    interaction_seconds=24,
    captions=True,
    help=True,
    auto_location=True,
    reduced_motion=False,
    country="auto",
    timezone="auto",
    latitude="",
    longitude="",
    hemisphere="auto",
    units="auto",
    poll_seconds=900,
    stale_seconds=3600,
    scene_seconds=24,
    caption_seconds=90,
    hint_seconds=1800,
    hold_ms=900,
    before_days=1,
    after_days=1,
    halloween_days=7,
    christmas_days=12,
    birthday="",
    quiet_start=-1,
    quiet_end=-1,
    max_keys=32,
    holiday_ids="july4,thanksgiving,christmas,holi,easter,halloween,newyear,valentine,lunar,diwali,eid,hanukkah,patrick,earth,birthday",
    disabled_scenes="",
    scene_override="",
    weather_override="",
    date_override="",
)
HOLIDAYS = set(DEFAULTS["holiday_ids"].split(","))
CONDITIONS = {"clear", "cloudy", "rain", "snow", "hot", "wind", "storm", "fog"}


def settings(raw=None):
    raw = {} if raw is None else raw
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise ValueError("Unknown world setting")
    value = {**DEFAULTS, **raw}
    for k, default in DEFAULTS.items():
        if type(default) is bool and type(value[k]) is not bool:
            raise ValueError(f"world.{k} must be boolean")
        if type(default) is str and not isinstance(value[k], str):
            raise ValueError(f"world.{k} must be text")
    for key, low, high in [
        ("poll_seconds", 300, 86400),
        ("stale_seconds", 300, 86400),
        ("scene_seconds", 8, 600),
        ("interaction_seconds", 12, 300),
        ("caption_seconds", 15, 86400),
        ("hint_seconds", 60, 86400),
        ("hold_ms", 300, 3000),
        ("before_days", 0, 30),
        ("after_days", 0, 30),
        ("halloween_days", 0, 31),
        ("christmas_days", 0, 31),
        ("quiet_start", -1, 23),
        ("quiet_end", -1, 23),
        ("max_keys", 1, 32),
    ]:
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ValueError(f"world.{key} must be {low}..{high}")
    if (value["quiet_start"] == -1) != (value["quiet_end"] == -1):
        raise ValueError("Set both quiet hours, or disable both with -1")
    for key, choices in [("units", {"auto", "C", "F"}), ("hemisphere", {"auto", "north", "south"})]:
        if value[key] not in choices:
            raise ValueError(f"Invalid world.{key}")
    if value["timezone"] != "auto":
        ZoneInfo(value["timezone"])
    if bool(value["latitude"]) != bool(value["longitude"]):
        raise ValueError("Set both latitude and longitude")
    for key, limit in [("latitude", 90), ("longitude", 180)]:
        if value[key]:
            n = float(value[key])
            if not math.isfinite(n) or abs(n) > limit:
                raise ValueError(f"Invalid {key}")
    if value["country"] != "auto":
        import holidays

        if value["country"] not in holidays.list_supported_countries():
            raise ValueError("Use a supported uppercase ISO country code")
        holidays.country_holidays(value["country"])
    if value["scene_override"] and value["scene_override"] not in SCENES:
        raise ValueError("Unknown scene_override")
    if value["weather_override"] and value["weather_override"] not in CONDITIONS:
        raise ValueError("Unknown weather_override")
    for key, choices in [("disabled_scenes", set(SCENES)), ("holiday_ids", HOLIDAYS)]:
        if {s.strip() for s in value[key].split(",") if s.strip()} - choices:
            raise ValueError(f"Unknown IDs in {key}")
    from datetime import date

    if value["date_override"]:
        date.fromisoformat(value["date_override"])
    if value["birthday"]:
        date.fromisoformat("2000-" + value["birthday"])
    return value


def read_ini(root):
    file = Path(root) / "jelly.ini"
    if not file.exists():
        return {}
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(file, encoding="utf-8-sig")
    if parser.defaults() or set(parser.sections()) - {"world"}:
        raise ValueError("jelly.ini supports only [world]")
    result = {}
    for key, text in parser.items("world") if parser.has_section("world") else ():
        if key not in DEFAULTS:
            raise ValueError(f"Unknown world.{key}")
        default = DEFAULTS[key]
        result[key] = (
            parser.getboolean("world", key) if type(default) is bool else int(text) if type(default) is int else text
        )
    settings(result)
    return result
