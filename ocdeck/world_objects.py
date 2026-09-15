"""Small world contracts. Definitions are immutable; instances belong to the director."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Definition:
    action: str
    support: str
    motive: str
    result: str
    carry: bool = False
    grip: tuple[int, int] = (20, 28)
    ground: tuple[int, int] = (20, 34)


# Explicit semantics, including assets not selected by today's scene catalog.
DEFINITIONS = {
    "acorn": Definition("plant", "soil", "curiosity", "sprout", True),
    "balloon": Definition("retie", "post", "play", "tied", True),
    "beachball": Definition("chase", "floor", "play", "parked"),
    "broom": Definition("sweep", "rack", "tidy", "clean", True),
    "cake": Definition("candles", "plate", "nourishment", "served"),
    "candy": Definition("unwrap_eat", "tray", "nourishment", "wrapper_stored", True),
    "canister": Definition("smoke_show", "floor", "celebrate", "closed"),
    "clock": Definition("wind_clock", "stand", "rest", "wound"),
    "cloud": Definition("shelter", "sky", "weather", "puddle"),
    "clover": Definition("water", "soil", "curiosity", "grown"),
    "cocoa": Definition("drink", "coaster", "nourishment", "empty", True),
    "crescent": Definition("moonwatch", "sky", "rest", "observed"),
    "diya": Definition("tend_wick", "tray", "celebrate", "lit"),
    "dreidel": Definition("spin", "floor", "play", "tipped"),
    "eggs": Definition("decorate_egg", "basket", "curiosity", "decorated"),
    "fan": Definition("switch_fan", "stand", "weather", "cooled"),
    "feast": Definition("picnic", "plate", "nourishment", "packed"),
    "flower": Definition("water", "soil", "curiosity", "grown"),
    "fountain": Definition("fill_water", "basin", "curiosity", "watered"),
    "gift": Definition("unwrap", "floor", "curiosity", "opened"),
    "globe": Definition("spin_globe", "stand", "curiosity", "located"),
    "grass": Definition("trim", "soil", "tidy", "trimmed"),
    "heart": Definition("hug", "tray", "sociability", "kept", True),
    "icicles": Definition("catch_drips", "ledge", "weather", "collected"),
    "kite": Definition("fly", "rack", "play", "folded", True),
    "lamp": Definition("read_light", "stand", "rest", "off"),
    "lantern": Definition("hang", "hook", "celebrate", "hung", True),
    "leaf": Definition("press_leaf", "floor", "curiosity", "pressed", True),
    "lemonade": Definition("drink", "coaster", "nourishment", "empty", True),
    "letter": Definition("read_letter", "mat", "sociability", "folded", True),
    "menorah": Definition("light_candles", "stand", "celebrate", "lit"),
    "mittens": Definition("wear", "rack", "weather", "returned", True),
    "music": Definition("lullaby", "effect", "rest", "quiet"),
    "pie": Definition("serve", "plate", "nourishment", "served"),
    "pinwheel": Definition("blow", "stand", "play", "stopped"),
    "popsicle": Definition("lick", "tray", "nourishment", "stick_stored", True),
    "pot": Definition("count_coins", "floor", "curiosity", "counted"),
    "powder": Definition("pour_pattern", "tray", "celebrate", "pattern"),
    "puddle": Definition("splash", "water", "play", "settled"),
    "pumpkin": Definition("tend_pumpkin", "floor", "celebrate", "lit"),
    "rake": Definition("rake", "rack", "tidy", "pile", True, (20, 19)),
    "rangoli": Definition("finish_pattern", "floor", "celebrate", "complete"),
    "rocket": Definition("launch", "stand", "celebrate", "spent"),
    "sandcastle": Definition("build_sand", "soil", "curiosity", "built"),
    "scythe": Definition("harvest", "rack", "tidy", "harvested", True),
    "seedling": Definition("water", "soil", "curiosity", "grown"),
    "sled": Definition("ride", "floor", "play", "parked"),
    "snowangel": Definition("snow_angel", "snow", "play", "imprint"),
    "snowball": Definition("roll_snow", "snow", "play", "rolled"),
    "snowflake": Definition("catch_flake", "sky", "curiosity", "melted"),
    "snowman": Definition("build_snow", "snow", "curiosity", "built"),
    "sweets": Definition("serve", "plate", "nourishment", "served"),
    "telescope": Definition("aim", "tripod", "rest", "observed"),
    "train": Definition("drive", "track", "play", "parked"),
    "tree": Definition("decorate_tree", "soil", "celebrate", "decorated"),
    "window": Definition("close_window", "wall", "weather", "closed"),
    "windsock": Definition("check_wind", "post", "weather", "secured"),
}

ATMOSPHERES = {
    "balloons": "balloon",
    "butterflies": "flower",
    "clouds": "cloud",
    "confetti": "broom",
    "fireflies": "grass",
    "fireworks": "rocket",
    "fog": "lamp",
    "fountain": "fountain",
    "hearts": "heart",
    "hurricane": "window",
    "icicles": "icicles",
    "lanterns": "lantern",
    "leaves": "rake",
    "lights": "tree",
    "meteor": "telescope",
    "petals": "leaf",
    "rain": "window",
    "rainbow": "puddle",
    "smoke": "canister",
    "snow": "snowman",
    "stars": "telescope",
    "sun": "lemonade",
    "sunrise": "window",
    "tornado": "window",
    "wind": "kite",
}


@dataclass
class Object:
    id: int
    name: str
    cell: int | None
    home: int | None
    state: str = "available"
    progress: float = 0.0
    amount: float = 1.0
    result: str = ""
    applied: bool = False
    color: str = "#83e6d4"
    data: dict = field(default_factory=dict)
