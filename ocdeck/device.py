"""HID adapter using the pip hidapi wheel, avoiding a manual hidapi.dll install."""

import logging
import queue
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .controls import Controls
from .art import frame
from .coffee import CoffeeBreak
from .errors import message
from .appearance import appearance, animation_phase, harness_id
from collections import OrderedDict
from .jelly import DeckGeometry, Jelly, free_keys, settings as jelly_settings

LOG = logging.getLogger(__name__)
MINI_PIDS = {0x0063, 0x0090, 0x00B3, 0x00B8}


class WheelTransport:
    """StreamDeck transport duck type backed by cython-hidapi's bundled library."""

    def __init__(self, info):
        self.info, self.handle = info, None
        self.lock = threading.RLock()

    def open(self):
        import hid

        with self.lock:
            if self.handle is None:
                h = hid.device()
                h.open_path(self.info["path"])
                h.set_nonblocking(True)
                self.handle = h

    def close(self):
        with self.lock:
            if self.handle:
                self.handle.close()
                self.handle = None

    def is_open(self):
        return self.handle is not None

    def connected(self):
        import hid

        return any(x["path"] == self.info["path"] for x in hid.enumerate(0x0FD9, self.product_id()))

    def path(self):
        return self.info["path"]

    def vendor_id(self):
        return self.info["vendor_id"]

    def product_id(self):
        return self.info["product_id"]

    def _call(self, method, *args):
        from StreamDeck.Transport.Transport import TransportError

        try:
            with self.lock:
                if self.handle is None:
                    raise OSError("Device is closed")
                return getattr(self.handle, method)(*args)
        except (OSError, ValueError) as e:
            raise TransportError(str(e)) from e

    def write(self, payload):
        result = self._call("write", bytes(payload))
        if result != len(payload):
            from StreamDeck.Transport.Transport import TransportError

            raise TransportError(f"Short HID write: {result}/{len(payload)}")
        return result

    def write_feature(self, payload):
        return self._call("send_feature_report", bytes(payload))

    def read_feature(self, report_id, length):
        return bytes(self._call("get_feature_report", report_id, length))

    def read(self, length):
        value = self._call("read", length)
        if not value:
            return None
        data = bytes(value)
        if len(data) == length:
            return data
        # cython-hidapi returns the number of bytes physically read, while the
        # StreamDeck transport contract expects a report-id byte at index zero.
        # Some Windows HID paths omit that zero report id for unnumbered reports.
        if len(data) == length - 1:
            return b"\x00" + data
        from StreamDeck.Transport.Transport import TransportError

        raise TransportError(f"Unexpected HID input report length: {len(data)}/{length}")


def device_types():
    from StreamDeck.Devices.StreamDeckMini import StreamDeckMini
    from StreamDeck.Devices.StreamDeckOriginal import StreamDeckOriginal
    from StreamDeck.Devices.StreamDeckOriginalV2 import StreamDeckOriginalV2
    from StreamDeck.Devices.StreamDeckXL import StreamDeckXL

    return {
        **{p: StreamDeckMini for p in MINI_PIDS},
        0x60: StreamDeckOriginal,
        **{p: StreamDeckOriginalV2 for p in (0x6D, 0x80, 0xA5, 0xB9)},
        **{p: StreamDeckXL for p in (0x6C, 0x8F, 0xBA)},
    }


def elgato_running():
    import psutil

    for process in psutil.process_iter(["name"]):
        try:
            if (process.info["name"] or "").lower() in ("streamdeck.exe", "stream deck.exe", "stream deck"):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def enumerate_devices():
    import hid

    types = device_types()
    result = []
    for d in hid.enumerate(0x0FD9, 0):
        if d["product_id"] in types:
            deck = types[d["product_id"]](WheelTransport(d))
            result.append({**d, "model": deck.deck_type(), "keys": deck.key_count()})
    return result


def enumerate_minis():
    import hid

    return [d for d in hid.enumerate(0x0FD9, 0) if d["product_id"] in MINI_PIDS]


class DeviceLoop:
    def __init__(self, registry, presses, stop, config, mock=False, root=None):
        self.registry, self.presses, self.stop, self.config, self.mock = registry, presses, stop, config, mock
        self.status = {
            "online": False,
            "mock": mock,
            "error": "Not connected",
            "frames": 0,
            "input_events": 0,
            "last_input": None,
        }
        self.presented: list[dict | None] = [None] * len(self.registry.slots)
        self.presented_lock = threading.Lock()
        self.deck = None
        self.jelly = None
        self.jelly_events = queue.Queue(maxsize=32)
        self.jelly_root = root
        self.jelly_saved_at = 0.0
        self.jelly_writer = None
        self.coffee = None
        self.overlay_actions: dict[int, dict] = {}
        self.controls: "Controls | None" = None
        self.key_down = {}
        self.world = None
        self.world_service = None
        self.world_down = {}

    def notify_jelly(self, kind, slot):
        """Metadata-only handoff; workers never touch the animation controller."""
        if kind == "focus":
            try:
                self.jelly_events.put_nowait({"kind": kind, "slot": slot})
            except queue.Full:
                pass

    def _save_jelly(self, wait=True):
        if not (self.jelly and self.jelly_root and self.jelly.options["persistent"]):
            return
        from pathlib import Path
        from copy import deepcopy
        from .common import atomic_json

        # At most one filesystem worker. Periodic saves can wait for the next
        # interval; disconnect saves join outside the frame composition path.
        if self.jelly_writer and self.jelly_writer.is_alive():
            if not wait:
                return
            self.jelly_writer.join()
        snapshot = deepcopy(self.jelly.mind.snapshot(self.jelly.thoughts.recent))
        from .world_interactions import Interaction

        if self.world and isinstance(self.world.interaction, Interaction):
            snapshot["world"] = self.world.interaction.snapshot()
        path = Path(self.jelly_root) / "jelly-state.json"

        def write():
            try:
                atomic_json(path, snapshot)
            except Exception:
                LOG.warning("Could not save Jelly's optional state", exc_info=True)

        if wait:
            write()
        else:
            self.jelly_writer = threading.Thread(target=write, name="jelly-state-writer", daemon=True)
            self.jelly_writer.start()

    def _start_jelly(self):
        self.jelly = None
        self.status["jelly"] = "disabled"
        self.coffee = None
        self.overlay_actions = {}
        try:
            options = jelly_settings(self.config)
            if not options["enabled"] or not self.config.get("animations", True):
                return
            if self.deck:
                rows, columns = self.deck.key_layout()
                width, height = self.deck.key_image_format()["size"]
            else:
                rows, columns = {6: (2, 3), 15: (3, 5), 32: (4, 8)}[len(self.registry.slots)]
                width = height = 80
            geometry = DeckGeometry(rows, columns, width, height, options["virtual_gap"])
            self.jelly = Jelly(geometry, options["behavior_seed"], options["hop_style"], options)
            self.coffee = CoffeeBreak(time.monotonic())
            from .world_settings import settings as world_settings
            from .world_weather import WeatherService
            from .world import World

            world_options = world_settings(self.config.get("world", {}))
            if self.world_service:
                self.world_service.close()
            self.world_service = WeatherService(world_options)
            self.world = World(world_options, self.world_service)
            if not self.mock:
                self.world_service.start()
            self.jelly.thoughts.next_at = time.monotonic() + 20
            if options["persistent"] and self.jelly_root:
                from pathlib import Path
                from .common import read_json

                saved = read_json(Path(self.jelly_root) / "jelly-state.json", {})
                recent = self.jelly.mind.restore(saved)
                from .world_interactions import Interaction

                if isinstance(self.world.interaction, Interaction) and isinstance(saved, dict):
                    reset = read_json(Path(self.jelly_root) / "world-reset.json", {})
                    generation = reset.get("generation", "") if isinstance(reset, dict) else ""
                    state = saved.get("world")
                    if isinstance(state, dict) and state.get("generation", "") == generation:
                        self.world.interaction.restore(state)
                    self.world.interaction.generation = generation
                self.jelly.thoughts.recent.extend(recent)
            self.jelly_saved_at = time.monotonic()
            self.status["jelly"] = "enabled"
        except Exception:
            self._fail_jelly()

    def _fail_jelly(self):
        self.overlay_actions = {}
        if self.world_service:
            self.world_service.close()
            self.world_service = None
        self.world = None
        LOG.exception("Experimental Jelly disabled; agent rendering continues")
        if self.jelly:
            self.jelly.close()
        self.jelly = None
        self.status["jelly"] = "failed"

    def _jelly_frames(self, now, views):
        self.overlay_actions = {}
        if self.jelly is None:
            return {}
        try:
            available = free_keys(views)
            coffee_blocked = not self.jelly.options["coffee"] or bool(getattr(self, "_jelly_update_info", None))
            events = []
            for _ in range(32):
                try:
                    events.append(self.jelly_events.get_nowait())
                except queue.Empty:
                    break
            for event in events:
                slot = event.get("slot")
                if event.get("kind") not in ("tap", "coffee", "world_hold") or slot not in available:
                    continue
                if event.get("generation") != views[slot].get("generation"):
                    continue
                if event["kind"] == "world_hold":
                    if self.world and self.world.hold(now):
                        try:
                            self.presses.put_nowait({"_action": "open_world_help"})
                        except queue.Full:
                            LOG.warning("Press queue full; help request dropped")
                elif event["kind"] == "coffee":
                    if (
                        self.coffee
                        and not coffee_blocked
                        and slot in (self.coffee.key, self.coffee.jelly_key)
                        and {self.coffee.key, self.coffee.jelly_key} <= available
                        and now < self.coffee.until
                        and event.get("serial") == self.coffee.serial
                    ):
                        self.coffee.finish(now)
                        if self.jelly.current in available:
                            self.jelly.settle(self.jelly.current, now)
                        try:
                            self.presses.put_nowait({"_action": "open_coffee"})
                        except queue.Full:
                            LOG.warning("Press queue full; coffee browser request dropped")
                else:
                    if self.world and now < self.world.help_until:
                        self.world.help_until = 0
                        continue
                    self.jelly.tap(now)
                    if self.coffee:
                        self.coffee.tap(event.get("pressed_at", now), available, blocked=coffee_blocked)
            if self.coffee:
                self.coffee.update(
                    now,
                    available,
                    self.jelly,
                    blocked=coffee_blocked,
                )
            coffee_key = self.coffee.key if self.coffee else None
            self.jelly.update(now, available - {coffee_key}, views, [e for e in events if e.get("kind") == "focus"])
            if coffee_key is not None and self.coffee:
                # Ambient reactions cannot move Jelly away from the coffee pair.
                self.jelly.settle(self.coffee.jelly_key, now)
                self.jelly.deadline = self.coffee.until + 1
                self.jelly._idle_pose(now)
                self.jelly._point(coffee_key)
                self.jelly.gesture_step = 2 + int(now * 3) % 2
                self.jelly.thoughts.clear()
                if now < self.jelly.touch_until:
                    self.jelly.pose = ("squash", "jiggle", "rebound", "idle")[int(now * 12) % 4]
                    self.jelly.face = "happy"
            self.status["jelly_life"] = {
                "mood": self.jelly.mind.mood,
                "action": self.jelly.state,
                "hop_style": self.jelly.active_hop,
                "needs": {k: round(v, 1) for k, v in self.jelly.mind.needs.items()},
            }
            if now - self.jelly_saved_at >= 60:
                self._save_jelly(wait=False)
                self.jelly_saved_at = now
            if self.world and coffee_key is None:
                # A visible Jelly stays under a held finger until release.
                if self.world_down and self.jelly.current in self.world_down:
                    self.jelly.settle(self.jelly.current, now)
                self.world.tick(
                    now,
                    self.jelly,
                    available,
                    blocked=bool(self.world_down)
                    or bool(self.controls and self.controls.enabled and self.controls.page),
                )
                self.status["jelly_world"] = self.world.status
            else:
                self.jelly.world_costume = ""
                if self.world:
                    self.world.interaction.cancel(now, self.jelly)
            frames = self.jelly.crops(available - {coffee_key})
            self.overlay_actions = {k: {"_action": "tap"} for k in frames}
            if self.coffee:
                frames = self.coffee.decorate(now, self.jelly, frames)
                if coffee_key is not None:
                    for key in (coffee_key, self.coffee.jelly_key):
                        if key is not None:
                            self.overlay_actions[key] = {"_action": "coffee", "serial": self.coffee.serial}
            if self.world and coffee_key is None:
                frames = self.world.decorate(now, self.jelly, frames, available)
                # Decorative scenery never becomes an agent action or a pet tap target.
            return frames
        except Exception:
            self._fail_jelly()
            return {}

    def press(self, key, state):
        """Route the action actually displayed; keep HID callbacks free of I/O."""
        if self.world and self.world.active and self.world.options["help"] and 0 <= key < len(self.presented):
            with self.presented_lock:
                current = dict(self.presented[key] or {})
                if state and current.get("_action") == "tap" and not current.get("id"):
                    self.world_down.setdefault(key, (time.monotonic(), current))
                    return
                pressed = self.world_down.pop(key, None) if not state else None
            if pressed:
                started, view = pressed
                if any(view.get(k) != current.get(k) for k in ("id", "generation", "_action")):
                    return
                held = time.monotonic() - started >= self.world.options["hold_ms"] / 1000
                try:
                    self.jelly_events.put_nowait(
                        {**view, "kind": "world_hold" if held else "tap", "slot": key, "pressed_at": time.monotonic()}
                    )
                except queue.Full:
                    LOG.warning("Jelly queue full; dropping press")
                return
        if self.controls and self.controls.enabled and 0 <= key < len(self.presented):
            with self.presented_lock:
                if state:
                    self.key_down.setdefault(key, (time.monotonic(), dict(self.presented[key] or {})))
                    return
                pressed = self.key_down.pop(key, None)
                if not pressed:
                    return
                started, view = pressed
                current = self.presented[key] or {}
                held = time.monotonic() - started >= self.config.get("controls", {}).get("hold_ms", 650) / 1000
                fields = ("id", "generation", "revision") if held else ("id", "generation", "revision", "_action")
                if any(view.get(k) != current.get(k) for k in fields):
                    return
            if view.get("_action") != "controls" and held:
                view["_action"] = "open_controls"
            try:
                if view.get("_action") in ("tap", "coffee") and not view.get("id"):
                    self.jelly_events.put_nowait(
                        {**view, "kind": view["_action"], "slot": key, "pressed_at": time.monotonic()}
                    )
                else:
                    self.presses.put_nowait(view)
            except queue.Full:
                LOG.warning("Press queue full; dropping press")
            return
        if not state or not 0 <= key < len(self.presented):
            return
        with self.presented_lock:
            view = dict(self.presented[key] or {})
        if not view:
            return
        action = view.get("_action") if not view.get("id") else None
        LOG.info("Button down key=%s action=%s", key + 1, action or "focus")
        try:
            if action in ("tap", "coffee"):
                self.jelly_events.put_nowait({**view, "kind": action, "slot": key, "pressed_at": time.monotonic()})
            else:
                self.presses.put_nowait(view)
        except queue.Full:
            LOG.warning("Press queue full; dropping press")

    def _presented_view(self, key, view):
        if view.get("_action") == "controls":
            return dict(view)
        if view.get("id"):
            return dict(view)
        return {**view, **self.overlay_actions.get(key, {})}

    def run(self):
        from PIL import Image

        while not self.stop.is_set():
            try:
                with self.presented_lock:
                    self.key_down.clear()
                if not self.mock:
                    from StreamDeck.ImageHelpers import PILHelper

                    devices = enumerate_devices()
                    serial = self.config.get("serial")
                    if serial:
                        devices = [d for d in devices if d.get("serial_number") == serial]
                    if len(devices) != 1:
                        raise RuntimeError(
                            f"Found {len(devices)} matching decks; select serial in config.json if multiple"
                        )
                    if elgato_running() and not self.config.get("allow_elgato", False):
                        raise RuntimeError(
                            "AD001: Elgato is running. Quit Stream Deck from its tray menu, then run ocdeck doctor."
                        )
                    self.deck = device_types()[devices[0]["product_id"]](WheelTransport(devices[0]))
                    self.deck.open()
                    if hasattr(self.deck, "set_poll_frequency"):
                        self.deck.set_poll_frequency(60)
                    self.registry.resize(self.deck.key_count())
                    self.presented = [None] * self.deck.key_count()
                    self.deck.set_brightness(int(self.config.get("brightness", 45)))
                    blank = PILHelper.to_native_key_format(self.deck, Image.new("RGB", (80, 80), "black"))
                    for k in range(len(self.registry.slots)):
                        self.deck.set_key_image(k, blank)

                    def on_key(_deck, key, state):
                        self.status["input_events"] = int(self.status.get("input_events", 0)) + 1
                        self.status["last_input"] = {"key": int(key), "pressed": bool(state), "time": time.time()}
                        self.press(key, state)

                    self.deck.set_key_callback(on_key)
                    self.status.update(serial=devices[0].get("serial_number"), productId=devices[0]["product_id"])
                self.status.update(online=True, error="", keys=len(self.registry.slots))
                last, native = {}, OrderedDict()
                styles = [appearance(self.config, k) for k in range(len(self.registry.slots))]
                next_probe = time.monotonic() + 2
                fps = max(1, min(30, int(self.config.get("fps", 24))))
                self._start_jelly()
                metrics = {
                    "requested_fps": fps,
                    "ticks": 0,
                    "late_frames": 0,
                    "composition_ms": 0.0,
                    "conversion_ms": 0.0,
                    "write_ms": 0.0,
                }
                metrics_start = time.monotonic()
                while not self.stop.is_set():
                    start = time.monotonic()
                    if not self.mock and start >= next_probe:
                        assert self.deck is not None
                        if not self.deck.is_open() or not self.deck.connected():
                            raise OSError("Stream Deck disconnected")
                        reader = getattr(self.deck, "read_thread", None) or getattr(self.deck, "_read_thread", None)
                        if reader is not None and not reader.is_alive():
                            raise OSError("Stream Deck input reader stopped")
                        next_probe = start + 2
                    views = self.registry.view()
                    if self.controls and self.controls.enabled:
                        waiting = self.controls.broker.permissions.waiting_owners()
                        for view in views:
                            if view["id"] in waiting:
                                view["state"] = "input"
                    if not any(v["id"] for v in views) and self.config.get("ready", True):
                        views[0] = {**views[0], "state": "ready"}
                    compose_start = time.monotonic()
                    overlays = self._jelly_frames(start, views)
                    tiles = self.controls.tiles() if self.controls else None
                    if tiles:
                        from .controls import control_frame

                        for k, tile in enumerate(tiles):
                            views[k] = {**views[k], **tile, "id": None}
                            overlays[k] = control_frame(
                                tile["title"],
                                tile["subtitle"],
                                tile["tone"],
                                int(start * 12) % 24 if self.config.get("animations", True) else 0,
                            )
                    elif self.controls and self.controls.enabled:
                        from .controls import hold_frame

                        with self.presented_lock:
                            held_keys = dict(self.key_down)
                        for k, (pressed_at, _) in held_keys.items():
                            elapsed = start - pressed_at
                            if elapsed >= 0.2:
                                duration = self.config.get("controls", {}).get("hold_ms", 650) / 1000
                                overlays[k] = hold_frame(min(24, int(elapsed / duration * 24)))
                    metrics["composition_ms"] += (time.monotonic() - compose_start) * 1000
                    for k, v in enumerate(views):
                        style = styles[k]
                        phase = animation_phase(start, style, self.config.get("animations", True))
                        key = (
                            v["state"],
                            v["label"],
                            k,
                            phase if v["state"] != "off" else 0,
                            (self.deck.key_image_format()["size"][0] if self.deck else 80),
                            style,
                            harness_id(v["label"], v.get("harness", "")),
                            v.get("detail", "") if "detail" in (style.primary, style.secondary) else "",
                            v.get("pending"),
                        )
                        base_key = key
                        jelly_image = overlays.get(k)
                        # Bounded shared native cache. Bytes reflect real crop changes,
                        # so blank keys and held poses do not incur device writes.
                        if jelly_image is not None:
                            key = ("jelly", k, jelly_image.tobytes())
                        # Assignment identity must refresh even when the pixels are identical.
                        if last.get(k) == key:
                            with self.presented_lock:
                                self.presented[k] = self._presented_view(k, v)
                            continue
                        if not self.mock:
                            assert self.deck is not None
                            if key not in native:
                                if len(native) >= 768:
                                    native.popitem(last=False)
                                convert_start = time.monotonic()
                                if jelly_image is not None:
                                    try:
                                        native[key] = PILHelper.to_native_key_format(
                                            self.deck, jelly_image.convert("RGB")
                                        )
                                    except Exception:
                                        self._fail_jelly()
                                        overlays = {}
                                        key = base_key
                                        native[key] = PILHelper.to_native_key_format(self.deck, frame(*base_key))
                                else:
                                    native[key] = PILHelper.to_native_key_format(self.deck, frame(*base_key))
                                metrics["conversion_ms"] += (time.monotonic() - convert_start) * 1000
                            native.move_to_end(key)
                            write_start = time.monotonic()
                            self.deck.set_key_image(k, native[key])
                            metrics["write_ms"] += (time.monotonic() - write_start) * 1000
                        with self.presented_lock:
                            self.presented[k] = self._presented_view(k, v)
                        last[k] = key
                        self.status["frames"] += 1
                    metrics["ticks"] += 1
                    if time.monotonic() - start > 1 / fps:
                        metrics["late_frames"] += 1
                    elapsed = time.monotonic() - metrics_start
                    if elapsed >= 1:
                        ticks = metrics["ticks"]
                        self.status["render_timing"] = {
                            "requested_fps": fps,
                            "effective_loop_fps": round(ticks / elapsed, 2),
                            "late_frames": metrics["late_frames"],
                            **{
                                name: round(metrics[name] / ticks, 3)
                                for name in ("composition_ms", "conversion_ms", "write_ms")
                            },
                            "mock": self.mock,
                        }
                    self.stop.wait(max(0, 1 / fps - (time.monotonic() - start)))
            except Exception as error:
                LOG.warning(message("AD002", str(error)))
                self.status.update(online=False, error=message("AD002", str(error)))
            finally:
                self.world_down.clear()
                if self.world_service:
                    self.world_service.close()
                    self.world_service = None
                if self.jelly:
                    self._save_jelly()
                    self.jelly.close()
                    self.jelly = None
                self.world = None
                if self.deck:
                    try:
                        if self.stop.is_set():
                            from StreamDeck.ImageHelpers import PILHelper

                            blank = PILHelper.to_native_key_format(self.deck, Image.new("RGB", (80, 80), "black"))
                            for k in range(len(self.registry.slots)):
                                self.deck.set_key_image(k, blank)
                    except Exception:
                        pass
                    try:
                        self.deck.close()
                    except Exception:
                        pass
                    self.deck = None
                with self.presented_lock:
                    self.presented = [None] * len(self.registry.slots)
            self.stop.wait(2)
