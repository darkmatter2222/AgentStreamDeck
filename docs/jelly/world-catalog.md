# Living-world scene catalog

[Setup and configuration](world.md) · [Design contract](../development/DESIGN_SYSTEM.md)

Every entry is implemented in the production renderer. Use `ocdeck world preview ID --output scene.gif` to inspect it, or add IDs to `disabled_scenes` to switch them off. A context is an automatic selection condition, not a claim about live weather. Demo contexts require an explicit override.

![All 75 recipes at native key size](world-catalog.png)

[Animated object inventory and atmosphere gallery](artwork.md) show the shared artwork behind all 75 recipes. Each prop has a material animation or subtle light detail; stationary objects stay grounded. Cloud watching is intentionally scenery-only.

[Jelly–prop interaction gallery and individual prop assessments](prop-review.md) explain which objects are used and which remain scenery. The `prop` column below selects the interaction recipe automatically when object use is enabled.

Weather and particle motifs in all recipes use independent elapsed-time motion. Rain splashes on each free key; snow, leaves, petals and confetti settle and fade. The scene IDs and controls below are unchanged. [Native particle previews](world.md#natural-weather-particles).

## Requested holiday and weather scenes

| ID | Experience | Context | Sky / prop / costume |
| --- | --- | --- | --- |
| `sky_fireworks` | Sky fireworks | july4 | fireworks / rocket / none |
| `ground_fountain` | Ground fountain | july4 | fountain / fountain / none |
| `smoke_bombs` | Color smoke | july4 | smoke / canister / none |
| `thanksgiving_table` | A feast to share | thanksgiving | none / feast / none |
| `thanksgiving_bite` | One more bite | thanksgiving | none / pie / none |
| `christmas_lights` | String the lights | christmas | lights / tree / elf |
| `christmas_santa` | Santa Jelly | christmas | snow / gift / santa |
| `christmas_elf` | Workshop elf | christmas | lights / gift / elf |
| `christmas_snow` | Snowy Christmas | christmas | snow / snowman / scarf |
| `holi_colors` | Holi colors | holi | confetti / powder / none |
| `easter_hunt` | Egg hunt | easter | none / eggs / bunny |
| `ghost_hover` | Little ghost | halloween | stars / pumpkin / ghost |
| `skeleton_dance` | Skeleton dance | halloween | none / pumpkin / skeleton |
| `reaper_stroll` | Tiny reaper | halloween | fog / scythe / reaper |
| `masked_jelly` | Masquerade | halloween | none / candy / mask |
| `rain` | Rainy day | rain | rain / puddle / umbrella |
| `snow` | Snow day | snow | snow / snowman / scarf |
| `hot` | Feeling the heat | hot | sun / fan / sweat |
| `cloudy` | Cloud watching | cloudy | clouds / none / none |
| `wind` | Windy day | wind | wind / windsock / none |
| `storm` | Thunderstorm | storm | rain / cloud / umbrella |
| `fog` | Foggy morning | fog | fog / lamp / none |
| `tornado` | Toy tornado | demo | tornado / windsock / none |
| `hurricane` | Toy hurricane | demo | hurricane / cloud / none |
| `straight_line_wind` | Strong wind | wind | wind / leaf / none |

## Fifty additional experiences

| # | ID | Experience | Context | Visible motif and action |
| --- | --- | --- | --- | --- |
| 1 | `new_year_countdown` | New year stars | newyear | clock; stars; party; cheer |
| 2 | `new_year_confetti` | Confetti parade | newyear | balloon; confetti; party; dance |
| 3 | `valentine_hearts` | Floating hearts | valentine | heart; hearts; Jelly; wave |
| 4 | `valentine_letter` | A little kindness | valentine | letter; hearts; bow; nod |
| 5 | `lunar_lanterns` | Lantern evening | lunar | lantern; lanterns; Jelly; look_up |
| 6 | `lunar_envelope` | Lucky envelope | lunar | letter; stars; party; cheer |
| 7 | `diwali_diyas` | Diwali lamps | diwali | diya; stars; Jelly; wave |
| 8 | `diwali_rangoli` | Rangoli colors | diwali | rangoli; confetti; Jelly; applaud |
| 9 | `eid_crescent` | Crescent evening | eid | crescent; stars; Jelly; look_up |
| 10 | `eid_sweets` | Share sweets | eid | sweets; lanterns; Jelly; nod |
| 11 | `hanukkah_lights` | Festival candles | hanukkah | menorah; stars; Jelly; wave |
| 12 | `hanukkah_dreidel` | Dreidel spin | hanukkah | dreidel; quiet background; Jelly; spin |
| 13 | `st_patrick_clover` | Lucky clover | patrick | clover; quiet background; bow; cheer |
| 14 | `st_patrick_rainbow` | Rainbow end | patrick | pot; rainbow; Jelly; edge_peek |
| 15 | `earth_day_seed` | Plant a seed | earth | seedling; quiet background; gardener; nod |
| 16 | `earth_day_globe` | Our little planet | earth | globe; stars; Jelly; wave |
| 17 | `birthday_cake` | Birthday candles | birthday | cake; confetti; party; cheer |
| 18 | `birthday_balloons` | Birthday balloons | birthday | gift; balloons; party; dance |
| 19 | `spring_blossoms` | Blossom breeze | spring | flower; petals; Jelly; look_up |
| 20 | `spring_butterfly` | Butterfly visitor | spring | flower; butterflies; Jelly; wave |
| 21 | `spring_seedling` | Garden morning | spring | seedling; quiet background; gardener; nod |
| 22 | `spring_kite` | Kite afternoon | spring | kite; clouds; Jelly; look_up |
| 23 | `summer_lemonade` | Lemonade break | summer | lemonade; sun; sunhat; nod |
| 24 | `summer_sandcastle` | Sandcastle builder | summer | sandcastle; sun; sunhat; applaud |
| 25 | `summer_beachball` | Beach ball | summer | beachball; clouds; shades; cheer |
| 26 | `summer_fireflies` | Firefly evening | night | grass; fireflies; Jelly; look_up |
| 27 | `autumn_leaves` | Leaf drift | autumn | leaf; leaves; scarf; wave |
| 28 | `autumn_rake` | Leaf pile | autumn | rake; leaves; Jelly; scoot |
| 29 | `autumn_acorn` | Acorn treasure | autumn | acorn; quiet background; Jelly; edge_peek |
| 30 | `autumn_cocoa` | Cozy cocoa | autumn | cocoa; smoke; scarf; rest |
| 31 | `winter_snowangel` | Snow angel | winter | snowangel; snow; scarf; dance |
| 32 | `winter_snowball` | Snowball play | winter | snowball; snow; beanie; cheer |
| 33 | `winter_icicles` | Icicle sparkle | winter | snowman; icicles; beanie; look_up |
| 34 | `winter_mittens` | Mitten weather | winter | mittens; snow; scarf; wave |
| 35 | `rain_puddle_jump` | Puddle hop | rain | puddle; rain; boots; cheer |
| 36 | `rain_umbrella` | Under my umbrella | rain | flower; rain; umbrella; wave |
| 37 | `rain_window` | Rain on the window | rain | window; rain; Jelly; rest |
| 38 | `rain_rainbow` | After-rain rainbow | after_rain | puddle; rainbow; Jelly; cheer |
| 39 | `snow_catch` | Catch a snowflake | snow | snowflake; snow; beanie; look_up |
| 40 | `snow_sled` | Tiny sled | snow | sled; snow; scarf; scoot |
| 41 | `hot_popsicle` | Popsicle pause | hot | popsicle; sun; sweat; nod |
| 42 | `hot_fan` | Personal fan | hot | fan; wind; shades; rest |
| 43 | `wind_pinwheel` | Pinwheel spin | wind | pinwheel; wind; Jelly; spin |
| 44 | `wind_scarf` | Scarf in the breeze | wind | windsock; leaves; scarf; lean_back |
| 45 | `night_stargazing` | Stargazing | night | telescope; stars; Jelly; look_up |
| 46 | `night_meteor` | A shooting star | night | crescent; meteor; Jelly; cheer |
| 47 | `night_lullaby` | Moonlight rest | night | music; stars; nightcap; rest |
| 48 | `morning_sunrise` | Good morning | morning | flower; sunrise; Jelly; reform |
| 49 | `halloween_witch` | Friendly witch | halloween | broom; stars; witch; wave |
| 50 | `christmas_train` | Gift train | christmas | train; lights; elf; cheer |
