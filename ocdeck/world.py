"""Living-world scene director. All state and drawing stay on the render thread."""

from datetime import date, datetime
import math
import time
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
from .world_catalog import SCENES
from .world_calendar import active_holiday, quiet, season
from .world_weather import local_country
from .world_art import sky
from .jelly_catalog import ACTIONS
from .world_interactions import Interaction
from .world_environment import SOURCED, layers as environment_layers

HELP_URL = "https://github.com/darkmatter2222/AgentStreamDeck/blob/main/docs/jelly/world.md#configuration"


def text_strip(image, text, now):
    font = ImageFont.load_default(size=10 if image.width >= 80 else 9)
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, image.width, 15), fill="#09111b")
    length = d.textlength(text, font=font)
    overflow = max(0, length - image.width + 8)
    elapsed = max(0, now)
    # Pause at each end, then repeat. Keep the entire sentence readable on a Mini.
    cycle = overflow / 18 + 4
    offset = min(overflow, max(0, (elapsed % cycle - 2) * 18)) if overflow else 0
    d.text((4 - offset, 2), text, font=font, fill="#dbfff1")


class World:
    def __init__(self, options, service, wall=time.time):
        self.options, self.service, self.wall = options, service, wall
        self.scene_id = ""
        self.group = ""
        self.last_bucket = None
        self.index = -1
        self.next_caption = 0.0
        self.next_hint = 0.0
        self.caption_until = 0.0
        self.caption_started = 0.0
        self.caption = ""
        self.help_until = 0.0
        self.previous_weather = ""
        self.after_rain_until = 0.0
        self.active = False
        self.status = {}
        self.last_date_key = None
        self.holiday = None
        self.interaction = Interaction()

    def hold(self, now):
        if now < self.help_until:
            self.help_until = 0
            return True
        self.help_until = now + 20
        return False

    def tick(self, now, jelly, available=None, blocked=False):
        o = self.options
        location, weather, error = self.service.snapshot()
        country = o["country"] if o["country"] != "auto" else (location.country if location else "") or local_country()
        zone = o["timezone"] if o["timezone"] != "auto" else (location.timezone if location else "")
        current = (
            datetime.fromtimestamp(self.wall(), ZoneInfo(zone))
            if zone
            else datetime.fromtimestamp(self.wall()).astimezone()
        )
        day = date.fromisoformat(o["date_override"]) if o["date_override"] else current.date()
        self.active = (
            o["enabled"] and not quiet(current.hour, o["quiet_start"], o["quiet_end"]) and not jelly.update_available
        )
        jelly.world_costume = ""
        jelly.world_phase = 0
        jelly.hop_style = jelly.options["hop_style"]
        if not self.active:
            self.interaction.cancel(now, jelly)
            self.scene_id = ""
            self.status = {"state": "inactive"}
            return
        condition = (o["weather_override"] or (weather.condition if weather else "")) if o["weather"] else ""
        if self.previous_weather == "rain" and condition == "clear":
            self.after_rain_until = now + 300
        if condition:
            self.previous_weather = condition
        key = (day, country)
        if key != self.last_date_key:
            self.holiday = active_holiday(day, o, country)
            self.last_date_key = key
        south = o["hemisphere"] == "south" or (
            o["hemisphere"] == "auto" and location is not None and location.latitude < 0
        )
        group = self.holiday or (condition if condition and condition != "clear" else "")
        if not group and o["seasons"]:
            group = (
                "after_rain"
                if now < self.after_rain_until
                else "night"
                if (weather and not weather.is_day) or current.hour < 6 or current.hour >= 20
                else "morning"
                if current.hour < 9
                else season(day, south)
            )
        disabled = {s.strip() for s in o["disabled_scenes"].split(",")}
        pool = [k for k, s in SCENES.items() if s.group == group and k not in disabled]
        override = o["scene_override"]
        if override:
            pool = [override] if override not in disabled else []
        bucket = int(now / o["scene_seconds"])
        changed = group != self.group or bucket != self.last_bucket
        if changed:
            self.index += 1
            self.group, self.last_bucket = group, bucket
        scene_id = pool[self.index % len(pool)] if pool else ""
        switched = scene_id != self.scene_id
        self.scene_id = scene_id
        scene = SCENES.get(scene_id)
        self.status = dict(
            scene=scene_id,
            holiday=self.holiday,
            condition=condition,
            weather_status="demo" if o["weather_override"] else "fresh" if weather else error or "unavailable",
            location_source=location.source if location else "unknown",
            country=country,
            timezone=zone or "system",
        )
        if (o["reduced_motion"] or now < self.help_until) and jelly.current is not None:
            jelly.settle(jelly.current, now)
            jelly.pose, jelly.face = "idle", "neutral"
        if scene:
            if scene.costume == "ghost" and o["costumes"]:
                jelly.hop_style = "floaty"
            jelly.world_costume = scene.costume if o["costumes"] else ""
            jelly.world_phase = 0 if o["reduced_motion"] else int(now * 8) % 8
            if (
                switched
                and not o["living_world"]
                and not o["reduced_motion"]
                and jelly.current is not None
                and jelly.state != "hop"
                and jelly.mind.target is None
            ):
                action = {"bob": "nod", "lean_back": "retreat"}.get(scene.action, scene.action)
                if action in ACTIONS or action in ("wave", "nod", "rest", "look_up", "edge_peek"):
                    jelly.start_action(action, now)
            if scene.costume == "ghost" and o["costumes"] and jelly.current is not None and jelly.state != "hop":
                jelly.y = jelly.geometry.anchor(jelly.current)[1] - (
                    4 if o["reduced_motion"] else 6 + 2 * math.sin(now * 2)
                )
        if available is not None:
            keys = sorted(available)
            if jelly.current in keys:
                keys.remove(jelly.current)
                keys.insert(0, jelly.current)
            self.interaction.tick(
                now, jelly, set(keys[: o["max_keys"]]), scene_id, scene, o, blocked=blocked or now < self.help_until
            )
            self.status["interaction"] = self.interaction.stage or "ambient"
        if o["captions"] and jelly.current is not None:
            text = ""
            if o["help"] and o["weather"] and not location and not o["weather_override"] and now >= self.next_hint:
                text = "Location unknown. Hold Jelly for setup."
                self.next_hint = now + o["hint_seconds"]
            elif now >= self.next_caption:
                if weather and o["weather"] and not o["weather_override"]:
                    unit = o["units"] if o["units"] != "auto" else "F" if country == "US" else "C"
                    temp = weather.temperature * 9 / 5 + 32 if unit == "F" else weather.temperature
                    text = f"Currently {round(temp)}{unit} - {weather.condition}."
                elif scene and scene.words:
                    text = scene.words
                elif o["weather"] and location and not weather:
                    text = "Weather unavailable. Hold Jelly for setup."
                if o["weather_override"]:
                    text = "Demo weather: " + o["weather_override"]
                if o["scene_override"]:
                    text = "Preview: " + SCENES[o["scene_override"]].title
                self.next_caption = now + o["caption_seconds"]
            if text:
                self.caption = text
                self.caption_started = now
                self.caption_until = now + max(8, len(text) * 0.42)

    def decorate(self, now, jelly, frames, available):
        if not self.active or not available:
            return frames
        o, g = self.options, jelly.geometry
        keys = sorted(available)
        if jelly.current in keys:
            keys.remove(jelly.current)
            keys.insert(0, jelly.current)
        keys = keys[: o["max_keys"]]
        scene = SCENES.get(self.scene_id)
        phase = 0 if o["reduced_motion"] else int(now * 8)
        scale = g.scale
        canvas = Image.new("RGBA", (math.ceil(g.size[0] / scale), math.ceil(g.size[1] / scale)))
        d = ImageDraw.Draw(canvas)
        if scene and o["particles"]:
            from .world_particles import LOCAL

            def atmosphere(kind):
                if kind in LOCAL or kind in ("sun", "sunrise", "rainbow", "tornado", "hurricane"):
                    targets = keys if kind in LOCAL else [next((k for k in keys if k not in frames), keys[0])]
                    for key in targets:
                        tile = Image.new("RGBA", (math.ceil(g.width / scale), math.ceil(g.height / scale)))
                        sky(
                            ImageDraw.Draw(tile),
                            kind,
                            *tile.size,
                            phase,
                            scene.color,
                            seconds=0 if o["reduced_motion"] else now,
                            seed=key + 17,
                        )
                        left, top, _, _ = g.bounds(key)
                        canvas.alpha_composite(tile, (left // scale, top // scale))
                else:
                    sky(d, kind, *canvas.size, phase, scene.color)

            if scene.sky not in SOURCED:
                atmosphere(scene.sky)
            # Weather keeps its own material timing around a holiday scene.
            _, weather, _ = self.service.snapshot()
            condition = o["weather_override"] or (weather.condition if weather else "")
            if o["weather"] and condition in ("rain", "snow") and condition != scene.sky:
                atmosphere(condition)
        world = canvas.resize((canvas.width * scale, canvas.height * scale), Image.Resampling.NEAREST)
        result = {k: im for k, im in frames.items() if k not in keys}
        for k in keys:
            bg = world.crop(g.bounds(k))
            if bg.getbbox():
                result[k] = bg
        for key, tile in (environment_layers(self.interaction, jelly, set(keys)) if o["particles"] else {}).items():
            result.setdefault(key, Image.new("RGBA", (g.width, g.height))).alpha_composite(tile)
        play_back, play_front = self.interaction.render_layers(jelly, set(keys))
        for key, tile in play_back.items():
            result.setdefault(key, Image.new("RGBA", (g.width, g.height))).alpha_composite(tile)
        # The character always owns the foreground, including its entire hop crop.
        for k in keys:
            if k in frames:
                bg = result.setdefault(k, Image.new("RGBA", (g.width, g.height)))
                bg.alpha_composite(frames[k])
        for key, tile in play_front.items():
            result.setdefault(key, Image.new("RGBA", (g.width, g.height))).alpha_composite(tile)
        if jelly.current in result and jelly.state != "hop":
            if now < self.help_until:
                tile = Image.new("RGBA", (g.width, g.height), "#09111b")
                draw = ImageDraw.Draw(tile)
                font = ImageFont.load_default(size=10)
                for i, line in enumerate(("JELLY SETUP", "jelly.ini", "Hold: docs", "Tap: close")):
                    draw.text(
                        (g.width / 2, 9 + i * 16), line, font=font, fill="#83e6d4" if i == 0 else "#dbfff1", anchor="mm"
                    )
                result[jelly.current] = tile
            elif now < self.caption_until and now >= jelly.touch_until:
                text_strip(result[jelly.current], self.caption, now - self.caption_started)
        return result
