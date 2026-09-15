"""State-only pixel actors. Drawing never consumes materials or applies outcomes."""

import math
from PIL import Image, ImageDraw
from .jelly_art import POSES
from .world_props import prop, INK, WHITE, GOLD, GREEN, BLUE, PINK, WOOD
from .world_objects import DEFINITIONS


def grip(jelly):
    """Pose-aware lower side anchor, below the face, in absolute deck pixels."""
    width, height, _ = POSES[jelly.pose]
    side = -1 if jelly.mirror else 1
    return jelly.x + side * (width // 2 - 1) * jelly.geometry.scale, jelly.y - max(
        3, height // 4
    ) * jelly.geometry.scale


def render_layers(director, jelly, available):
    if not director.visible or director.target is None:
        return {}, {}
    g = jelly.geometry
    scale = g.scale
    w, h = math.ceil(g.size[0] / scale), math.ceil(g.size[1] / scale)
    back, front = Image.new("RGBA", (w, h)), Image.new("RGBA", (w, h))
    obj = director.objects[director.target]
    f = director.frame
    if f is None:
        return {}, {}
    action = DEFINITIONS[obj.name].action
    active = f.stage == "use"
    pouring = f.stage == "water_pour"
    done = obj.applied
    p = obj.progress
    beat = int(director.use_elapsed * 8) % 8 if active else 0
    gx, gy = (round(v / scale) for v in grip(jelly))
    side = -1 if jelly.mirror else 1
    d, fg = ImageDraw.Draw(back), ImageDraw.Draw(front)

    def place(cell):
        left, top, _, bottom = g.bounds(cell)
        # 80px/96px keys use a 40px art grid; 72px keys keep native 1x sprites.
        return round(left / scale + g.width / scale - 9), round((bottom - 3) / scale)

    def support(cell, kind):
        x, y = place(cell)
        d.ellipse((x - 8, y - 1, x + 7, y + 1), fill="#20303b")
        if kind in ("rack", "post", "hook"):
            d.line((x + 4, y, x + 4, y - 22, x - 3, y - 22), fill=WOOD, width=2)
            d.line((x - 5, y, x + 7, y), fill=WOOD)
        elif kind in ("wall", "ledge"):
            d.line((x - 10, y - 22, x + 7, y - 22), fill=WOOD, width=2)
            d.line((x + 7, y - 22, x + 7, y), fill="#344451")
        elif kind in ("coaster", "plate", "tray", "mat", "basket", "soil", "snow", "water", "basin", "track"):
            color = {"soil": "#684832", "snow": WHITE, "water": BLUE, "basin": BLUE, "track": "#718797"}.get(
                kind, "#738e99"
            )
            d.line((x - 8, y, x + 7, y), fill=color, width=2)

    def icon(name, x, y, phase=0, limit=17, layer=back):
        im = prop(name, phase, obj.color).copy()
        box = im.getbbox()
        if not box:
            return
        im = im.crop(box)
        ratio = min(1, limit / im.width, 23 / im.height)
        im = im.resize((max(1, round(im.width * ratio)), max(1, round(im.height * ratio))), Image.Resampling.NEAREST)
        layer.alpha_composite(im, (round(x - im.width / 2), round(y - im.height)))

    home = obj.home
    if home is None or home not in range(g.count):
        return {}, {}
    x, y = place(home)
    support(home, DEFINITIONS[obj.name].support)
    if director.work_key != home:
        support(director.work_key, "soil" if obj.name in ("rake", "scythe", "broom") else DEFINITIONS[obj.name].support)
    held = director.held == obj.id
    reach = f.stage == "reach"
    putdown = f.stage == "putdown"
    target_x, target_y = place(director.work_key if obj.name in ("balloon", "lantern", "kite") and putdown else home)
    t = min(1, f.elapsed / 0.8)
    # Reach/lower interpolate the object to/from the same grip used while hopping.
    if held:
        x, y = gx, gy + 3
        if putdown:
            x, y = round(x + (target_x - x) * t), round(y + (target_y - y) * t)
    elif reach and DEFINITIONS[obj.name].carry:
        x, y = round(x + (gx - x) * t), round(y + (gy + 3 - y) * t)
    elif obj.cell is not None:
        x, y = place(obj.cell)
    layer = front if held or reach and DEFINITIONS[obj.name].carry else back
    draw = ImageDraw.Draw(layer)

    if obj.name in ("rake", "broom", "scythe"):
        wx, wy = place(director.work_key)
        gathered = obj.data.get("gathered", 0)
        for i in range(7):
            start = wx - 15 + i * 3
            lx = round(start + (wx - 3 - start) * gathered)
            ly = wy - (i % 3 if gathered else 0)
            d.polygon(
                [(lx - 2, ly - 1), (lx, ly - 3), (lx + 2, ly - 1), (lx + 1, ly + 1), (lx - 1, ly)],
                fill=GOLD if i % 2 else "#c17a42",
            )
        if held or reach:
            if active:
                stroke = min(1, (director.use_elapsed % 1.5) / 0.85)
                hx, hy = wx + 2 - round(stroke * 9), wy - 1
                if director.use_elapsed % 1.5 > 0.85:
                    hy -= 3
            else:
                hx, hy = x + side * 3, y + 5
            topx, topy = x - side * 2, y - 9
            draw.line((topx, topy, x, y, hx, hy), fill=WOOD, width=2)
        else:
            hx, hy, topx, topy = x - 3, y - 1, x + 4, y - 22
        if not (held or reach):
            draw.line((topx, topy, hx, hy), fill=WOOD, width=2)
        if obj.name == "rake":
            draw.line((hx - 5, hy - 1, hx + 5, hy - 1), fill="#a6bdc5")
            for dx in (-5, -2, 1, 4):
                draw.line((hx + dx, hy - 1, hx + dx, hy + 1), fill=WHITE)
        elif obj.name == "broom":
            draw.polygon(
                [(hx - 2, hy - 5), (hx + 2, hy - 5), (hx + 5, hy + 1), (hx - 5, hy + 1)], fill=GOLD, outline=INK
            )
        else:
            draw.polygon([(hx - 6, hy), (hx - 3, hy - 4), (hx + 4, hy - 5), (hx + 2, hy - 2)], fill=WHITE, outline=INK)
    elif action == "drink":
        # Same vessel, decreasing liquid; coaster remains at home.
        draw.rectangle((x - 4, y - 8, x + 4, y - 1), fill="#a4755d" if obj.name == "cocoa" else "#5e7d89", outline=INK)
        liquid = round(5 * obj.amount)
        if liquid:
            draw.rectangle((x - 3, y - 1 - liquid, x + 3, y - 2), fill=GOLD)
        draw.arc((x + 2, y - 7, x + 8, y - 1), 270, 90, fill=WHITE)
        if active and 0.25 < p < 0.8:
            draw.line((x - 3, y - 8, gx - 2, gy - 2), fill=GOLD)
        if obj.name == "cocoa" and obj.amount > 0.1:
            for k in (0, 4):
                draw.line((x - 2 + k, y - 11 - beat // 3, x - 1 + k, y - 13 - beat // 3), fill="#8c9aa3")
    elif action in ("water", "fill_water", "plant"):
        if action == "plant" and p < 0.2:
            icon("acorn", x, y, layer=layer, limit=10)
        else:
            px, py = place(director.work_key if action == "fill_water" else home)
            d.ellipse((px - 7, py - 2, px + 7, py + 1), fill="#684832")
            if action != "plant" or p > 0.45:
                icon("seedling" if action in ("plant", "fill_water") else obj.name, px, py, limit=13)
                if obj.data.get("growth", 0) > 0.2:
                    d.line((px, py - 12, px + 4, py - 16), fill=GREEN, width=2)
            if active and action != "fill_water" or pouring or f.stage == "water_carry":
                fg.rectangle((gx - 3, gy - 5, gx + 3, gy + 1), fill="#638b9e", outline=INK)
                fg.line((gx + 3, gy - 1, px - 2, gy - 3), fill=BLUE, width=2)
                for k in range(3):
                    yy = gy + 2 + (beat + k * 3) % max(1, py - gy - 2)
                    fg.point((px - 2 + k % 2, yy), fill=BLUE)
            if action == "fill_water":
                px, py = place(home)
                d.arc((px - 8, py - 5, px + 8, py + 2), 0, 180, fill=WHITE, width=2)
                d.line((px - 6, py - 3, px + 6, py - 3), fill=BLUE)
                d.line((px, py - 3, px, py - 12), fill=BLUE)
                d.arc((px - 6, py - 15, px + 6, py - 8), 180, 360, fill=WHITE)
                if active:
                    fg.rectangle((gx - 3, gy - 3, gx + 3, gy + 3), outline=WHITE)
                    fg.line(
                        (gx - 2, gy + 2 - round(4 * director.water), gx + 2, gy + 2 - round(4 * director.water)),
                        fill=BLUE,
                    )
    elif action in ("chase", "roll_snow", "drive", "ride"):
        px, py = place(home)
        motion = round(obj.data.get("offset", 0))
        if action == "ride":
            px = round(g.anchor(home)[0] / scale + obj.data.get("offset", 0))
            py = round(g.anchor(home)[1] / scale)
            d.line((px - 14, py - 1, px + 13, py - 1, px + 16, py - 4), fill=WHITE, width=2)
            d.rectangle((px - 13, py - 6, px + 12, py - 4), fill=PINK, outline=INK)
        else:
            if action == "roll_snow":
                radius = round(obj.data.get("radius", 3))
                d.ellipse((px + motion - radius, py - radius * 2, px + motion + radius, py), fill=WHITE, outline=BLUE)
            else:
                icon(obj.name, px + motion, py, round(obj.data.get("angle", 0)) % 8, limit=18)
            if action == "drive":
                d.line((px - 12, py + 1, px + 13, py + 1), fill="#7a8b98")
            if active and (p < 0.2 or p > 0.7):
                fg.line((gx, gy, px + motion - 5, py - 4), fill=WHITE)
    elif action == "unwrap":
        d.rectangle((x - 7, y - 10, x + 7, y - 1), fill=obj.color, outline=INK)
        lift = round(8 * obj.data.get("lid", 0))
        d.polygon(
            [(x - 7, y - 10), (x - 7, y - 13), (x + 8, y - 13 - lift), (x + 8, y - 10 - lift)], fill=PINK, outline=INK
        )
        d.rectangle((x - 1, y - 10, x + 1, y - 1), fill=GOLD)
        if p > 0.6:
            icon("beachball", x, y - 4, limit=8)
        if not done:
            d.line((x + 7, y - 6, x + 10 + round(p * 3), y - 2), fill=GOLD)
    elif action in ("spin", "spin_globe", "blow", "switch_fan"):
        phase = int(obj.data.get("turn", 0)) % 8
        icon(obj.name, x, y, phase, limit=18)
        if action == "spin" and done:
            d.rectangle((x - 9, y - 23, x + 9, y), fill=(0, 0, 0, 0))
            d.polygon([(x - 5, y - 2), (x, y - 6), (x + 5, y - 2), (x, y)], fill=BLUE, outline=INK)
            d.line((x + 4, y - 2, x + 7, y - 2), fill=GOLD)
        if action == "spin_globe" and active:
            d.line((x - 4 + phase, y - 14, x - 4 + phase, y - 9), fill=GREEN, width=2)
        if active:
            fg.line((gx, gy, x - 4, y - 8), fill=WHITE)
            if action in ("blow", "switch_fan"):
                fg.line((x - 12, y - 13, x - 8, y - 13 - beat % 2), fill=BLUE)
    elif action in ("serve", "picnic", "candles", "unwrap_eat", "lick"):
        icon(obj.name, x, y, 0, layer=layer, limit=17)
        if p > 0.2:
            # Author a missing portion, not unrelated glitter.
            draw.rectangle((x + 1, y - 11, x + 7, y - 4), fill=(0, 0, 0, 0))
            if active:
                fg.rectangle((gx - 2, gy - 4, gx + 2, gy), fill=GOLD, outline=INK)
        if action == "candles" and p > 0.2:
            draw.rectangle((x - 8, y - 23, x + 8, y - 14), fill=(0, 0, 0, 0))
        if action == "unwrap_eat" and active:
            d.line((target_x - 4, target_y - 2, target_x + 5, target_y - 1), fill=PINK)
        if obj.data.get("cleared", 0) >= 0.95:
            draw.rectangle((x - 8, y - 23, x + 8, y), fill=(0, 0, 0, 0))
            d.rectangle((target_x - 5, target_y - 3, target_x + 5, target_y), fill=WOOD, outline=INK)
    elif action in ("tend_wick", "light_candles", "read_light", "tend_pumpkin", "hang"):
        icon(obj.name, x, y, beat if active else 0, layer=layer, limit=19)
        lit = obj.data.get("lit", False)
        if lit:
            if obj.name not in ("lamp", "menorah"):
                draw.line((x - 2, y - 10, x, y - 14, x + 1, y - 9), fill=GOLD, width=2)
            d.line((target_x - 8, target_y, target_x + 7, target_y), fill="#8e6a43")
        else:
            if obj.name == "lamp":
                draw.polygon(
                    [(x - 4, y - 23), (x + 4, y - 23), (x + 8, y - 14), (x - 8, y - 14)], fill="#657785", outline=INK
                )
            else:
                draw.rectangle((x - 2, y - 14, x + 2, y - 10), fill="#594f44")
        if action == "hang" and done:
            d.line((x, y - 21, x + 4, y - 22), fill=WOOD)
        if action == "read_light" and active and p > 0.4:
            fg.polygon(
                [(gx - 6, gy), (gx, gy + 2), (gx + 6, gy), (gx + 6, gy - 6), (gx, gy - 4), (gx - 6, gy - 6)],
                fill=WHITE,
                outline=INK,
            )
    elif action in ("aim", "moonwatch", "shelter", "lullaby", "catch_flake"):
        # Sky landmarks retain a distinct nonphysical role.
        if obj.name in ("cloud", "crescent"):
            icon(obj.name, target_x, target_y - 22, beat if active else 0, limit=14)
        elif obj.name == "snowflake":
            if p < 0.5:
                crystal_y = gy - round(obj.data.get("height", 12))
                icon("snowflake", gx, crystal_y, 0, limit=max(2, round(10 * obj.amount)), layer=front)
            elif obj.amount > 0.1:
                fg.point((gx, gy), fill=BLUE)
        elif obj.name == "music":
            d.rectangle((target_x - 7, target_y - 7, target_x + 7, target_y), fill=WOOD, outline=INK)
            lid = 5 if active and 0.15 < p < 0.85 else 0
            d.line((target_x - 7, target_y - 7, target_x + 7, target_y - 7 - lid), fill=GOLD, width=2)
            if active and 0.15 < p < 0.85:
                icon("music", gx + 6, gy - 7 - beat // 2, limit=10)
        else:
            tx, ty = target_x, target_y
            d.line((tx, ty - 10, tx - 7, ty), fill="#92a8b8")
            d.line((tx, ty - 10, tx + 7, ty), fill="#92a8b8")
            rise = round(4 * math.sin(p * math.pi))
            d.line((tx - 8, ty - 12, tx + 6, ty - 19 - rise), fill=BLUE, width=5)
            d.line((tx - 8, ty - 13, tx + 6, ty - 20 - rise), fill=WHITE)
            if active:
                d.point((tx + 5, ty - 27 - rise), fill=GOLD)
        if action in ("aim", "moonwatch"):
            if obj.name != "telescope":
                icon("telescope", target_x, target_y, limit=15)
            if active:
                fg.line((gx, gy - 3, target_x - 5, target_y - 9), fill=BLUE, width=2)
        elif action == "shelter":
            d.line((target_x - 16, target_y - 19, target_x + 4, target_y - 19), fill=WOOD, width=2)
            d.line((target_x + 4, target_y - 19, target_x + 4, target_y), fill=WOOD)
            if p > 0.3:
                d.ellipse((target_x - 8, target_y - 1, target_x + 8, target_y + 1), fill=BLUE)
        elif action == "catch_flake" and p > 0.5:
            fg.point((gx, gy - 1), fill=BLUE)
    elif action in ("build_sand", "build_snow", "snow_angel", "trim", "harvest", "finish_pattern", "pour_pattern"):
        if action in ("build_sand", "build_snow"):
            icon(obj.name, x, y, limit=20)
            tier = obj.data.get("tier", 0)
            if tier < 3:
                cutoff = y - 5 - tier * 5
                d.rectangle((x - 11, y - 25, x + 11, cutoff), fill=(0, 0, 0, 0))
                if tier == 0:
                    d.ellipse((x - 7, y - 5, x + 7, y), fill=WHITE if action == "build_snow" else GOLD)
            if active:
                fg.rectangle((gx, gy, gx + 3, gy + 3), fill=WHITE if action == "build_snow" else GOLD)
        elif action == "snow_angel":
            if p > 0.15:
                icon("snowangel", round(jelly.x / scale), y, limit=26)
        elif action == "trim":
            icon("grass", x, y, limit=19)
            if p > 0.3 and director.sky != "fireflies":
                d.rectangle((x - 10, y - 12, x + 10, y - 5), fill=(0, 0, 0, 0))
            if active and director.sky != "fireflies":
                fg.line((gx, gy, x + 3, y - 4), fill=WHITE, width=2)
            if done:
                d.rectangle((x + 3, y - 3, x + 7, y), fill=GREEN)
        else:
            d.arc((x - 10, y - 7, x - 3, y), 0, 180, fill=WHITE)
            d.line((x - 9, y - 4, x - 4, y - 4), fill=PINK)
            for i in range(8):
                if i / 8 <= p:
                    a = i * math.tau / 8
                    xx, yy = x + round(7 * math.cos(a)), y - 2 + round(2 * math.sin(a))
                    d.ellipse((xx - 2, yy - 1, xx + 2, yy + 1), fill=(PINK, BLUE, GOLD, GREEN)[i % 4])
            if active:
                fg.line((gx, gy, x, y - 2), fill=GOLD)
    elif action in ("retie", "fly"):
        airborne = (held or active or action == "retie") and not (action == "fly" and obj.data.get("folded", False))
        if airborne:
            height = obj.data.get("height", 15) if action == "fly" else 15
            sway = round(obj.data.get("wind", 0) * 3)
            icon(obj.name, x + side * 2 + sway, y - height, 0, layer=layer, limit=12)
            draw.line((x + side * 2 + sway, y - height - 2, x, y), fill=WHITE)
            if action == "fly":
                draw.rectangle((x - 2, y - 1, x + 2, y + 1), fill=WOOD)
        else:
            draw.polygon([(x - 6, y - 3), (x + 6, y - 3), (x, y - 8)], fill=obj.color, outline=INK)
    elif action in ("read_letter", "press_leaf", "hug", "wear", "decorate_egg"):
        icon(obj.name, x, y, 0, layer=layer, limit=12)
        if action == "read_letter" and p > 0.15:
            unfolding = min(1, (p - 0.15) / 0.2) * (1 - min(1, max(0, (p - 0.8) / 0.2)))
            height = 5 + round(7 * unfolding)
            draw.rectangle((x - 5, y - height, x + 5, y - 2), fill=WHITE, outline=INK)
            for yy in range(y - height + 3, y - 2, 3):
                draw.line((x - 3, yy, x + 3, yy), fill=WOOD)
        elif action == "press_leaf" and done:
            d.rectangle((x - 7, y - 3, x + 7, y), fill=WOOD, outline=INK)
            d.line((x - 5, y - 2, x + 5, y - 2), fill=GOLD)
        elif action == "hug" and active:
            fg.arc((gx - 7, gy - 6, gx + 4, gy + 2), 0, 180, fill=WHITE)
        elif action == "wear" and active:
            fg.rectangle((gx - 3, gy - 2, gx + 3, gy + 2), fill=PINK, outline=INK)
        elif action == "decorate_egg":
            for stripe in range(min(3, int(p * 4))):
                draw.line((x - 2, y - 4 - stripe * 3, x + 2, y - 4 - stripe * 3), fill=(PINK, BLUE, GOLD)[stripe])
            if active:
                fg.line((gx, gy, x - 2, y - 4 - min(2, int(p * 4)) * 3), fill=WOOD)
    elif action in (
        "wind_clock",
        "count_coins",
        "catch_drips",
        "close_window",
        "check_wind",
        "decorate_tree",
        "splash",
        "smoke_show",
        "launch",
    ):
        icon(obj.name, x, y, beat if active else 0, limit=20)
        if action == "wind_clock" and active:
            fg.line((gx, gy, x - 5, y - 10), fill=GOLD)
        elif action == "count_coins":
            for i in range(round(5 * p)):
                d.ellipse((x - 9 + i * 2, y - 2, x - 6 + i * 2, y), fill=GOLD, outline=WOOD)
        elif action == "catch_drips":
            melt = round(6 * p)
            if melt:
                d.rectangle((x - 8, y - 15, x + 8, y - 15 + melt), fill=(0, 0, 0, 0))
            d.arc((x - 6, y - 5, x + 6, y + 1), 0, 180, fill=WHITE, width=2)
            if active:
                d.point((x, y - 15 + beat), fill=BLUE)
            if p > 0.4:
                d.line((x - 4, y - 2, x + 4, y - 2), fill=BLUE)
        elif action == "close_window":
            opening = obj.data.get("opening", 1)
            d.rectangle((x - 7, y - 19, x + 7, y - 3), fill="#152938", outline=WOOD)
            edge = x - 7 + round(14 * (1 - opening))
            d.rectangle((x - 7, y - 19, edge, y - 3), fill="#365d72", outline=WOOD)
            d.point((edge - 1, y - 10), fill=GOLD)
        elif action == "check_wind" and active:
            fg.line((gx, gy, x - 3, y - 5), fill=GOLD)
        elif action == "decorate_tree":
            for i in range(round(4 * p)):
                d.point((x - 4 + i * 2, y - 6 - i * 3), fill=PINK if i % 2 else GOLD)
        elif action == "splash" and active:
            for i in range(4):
                d.point((x - 8 + i * 5, y - 2 - beat // 2), fill=BLUE)
        elif action == "smoke_show" and (not active or p > 0.8):
            d.rectangle((x - 10, y - 24, x + 10, y - 9), fill=(0, 0, 0, 0))
            d.line((x - 4, y - 9, x + 4, y - 9), fill=WHITE)
        elif action == "launch":
            d.rectangle((x - 10, y - 26, x + 10, y - 5), fill=(0, 0, 0, 0))
            lift = round(obj.data.get("height", 0))
            icon("rocket", x, y - lift, 0, limit=10)
            if not active or obj.data.get("landed", False):
                d.rectangle((x - 5, y - 5, x + 5, y - 1), fill=(0, 0, 0, 0))
                d.line((x - 5, y, x + 5, y), fill=WOOD)
    else:
        raise ValueError("Missing activity renderer: " + action)

    if f.stage == "cleanup":
        alpha = max(0, 1 - f.elapsed / 1.2)
        for canvas in (back, front):
            canvas.putalpha(canvas.getchannel("A").point([round(v * alpha) for v in range(256)]))

    def crops(canvas):
        occupied = canvas.getbbox()
        if occupied is None:
            return {}
        result = {}
        for key in available:
            if key not in range(g.count):
                continue
            left, top, right, bottom = g.bounds(key)
            logical = (left // scale, top // scale, math.ceil(right / scale), math.ceil(bottom / scale))
            if (
                logical[2] <= occupied[0]
                or logical[0] >= occupied[2]
                or logical[3] <= occupied[1]
                or logical[1] >= occupied[3]
            ):
                continue
            tile = canvas.crop(logical)
            if tile.getbbox() is None:
                continue
            tile = tile.resize((tile.width * scale, tile.height * scale), Image.Resampling.NEAREST)
            dx, dy = left % scale, top % scale
            result[key] = tile.crop((dx, dy, dx + g.width, dy + g.height))
        return result

    return crops(back), crops(front)
