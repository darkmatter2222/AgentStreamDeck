# AgentStreamDeck design and experience contract

This is the reusable UI, UX and implementation strategy for contributors, including AI coding agents. Read it before changing buttons, Jelly, input routing or device rendering. It describes the shipped design, not a replacement theme.

## Product promise

A glance answers which coding agent needs attention. A press takes the user to that session. Jelly makes unused space feel alive. Decorations must never interfere with those first two promises.

Support Mini (2 × 3), Original/MK.2 (3 × 5) and XL (4 × 8). Obtain physical key sizes and layout from the device. Mock capacities are 6, 15 and 32. Do not advertise unsupported device families merely because a new geometry renders in a preview.

## Visual language

Buttons use dark backgrounds, crisp borders, short high-contrast labels and recognizable harness artwork. Status is communicated with words and badges as well as color. Keep primary status legible at physical key size. Put setup instructions in documentation and a deliberate help interaction, not continuous technical captions.

| Token | Existing value | Meaning |
| --- | --- | --- |
| Running | `#20eb75` | Work in progress |
| Idle | `#ffb32e` | Session available |
| Input | `#ff374b` | User attention requested |
| Ready | `#32ccff` | Broker ready |
| Jelly outline | `#193849` | Crisp silhouette |
| Jelly shadow | `#267c91` | Volume beneath body |
| Jelly body | `#40bec0` | Default teal personality |
| Jelly light | `#83e6d4` | Soft upper highlight |
| Jelly shine | `#dbfff1` | Small specular accents |
| Jelly ink | `#122b3e` | Facial details |
| Jelly cheek | `#f1a5c0` | Friendly warmth |
| World background | `#09111b` | Quiet scene framing |

The `classic`, `high-contrast`, `aurora`, `ocean`, `accessible` and `mono` themes remain authoritative in [appearance.py](../../ocdeck/appearance.py). Never recolor occupied agent buttons for a holiday. Honor per-button overrides, readable/focus presets and global animation settings. See [appearance reference](../reference/APPEARANCE.md).

## Character art and inspiration

Jelly is original procedural pixel art inspired by the readable, squash-and-stretch language of small game companions. Preserve its rounded mass, bright curious eyes, tiny cheeks, asymmetric highlights and friendly expression. Do not copy Terraria sprites or import unrelated pet art. Use the shipped geometry as the reference, not a new generated mascot.

- Draw on a 40 × 40 logical grid. The floor-contact anchor is `(20, 34)`.
- Author polygons and lines on integer pixels. Scale with nearest-neighbor sampling. Never blur, smooth or rotate by arbitrary angles.
- Keep apparent mass coherent through compression, stretch, flight and landing. The existing pose catalog is the source of truth.
- Facial expression and gaze carry emotion. Costumes must leave the face readable, except a deliberate sheet-ghost face with clear eye cutouts.
- Keep decoration silhouettes simple enough to recognize at 72, 80 and 96 native pixels.
- The ghost floats, Santa wears a hat, an elf retains Jelly's face, and a skeleton is playful rather than graphic.
- Cached artwork is immutable. Copy before compositing or drawing.

## Animation and layout

Maintain elapsed-time positioning independently from discrete pose holds. Existing local art uses approximately 12 pose holds per second; the broker defaults to 24 FPS and caps at 30. Natural particles sample elapsed seconds on every frame, with independent lifetimes, stable per-key seeds and local ground contact. Stars and supported decorative motifs retain an 8 Hz pose clock; held props use 4 Hz poses and bounded caches. Do not increase USB writes for unchanged images.

Jelly travels only between orthogonally adjacent free keys. Shared deck coordinates include virtual gaps, so effects line up across keys. A scene can occupy disconnected empty viewports, but Jelly cannot cross an occupied key. Recalculate availability every frame; never retain an ownership claim to a key.

Physical props require an active intention. Choose initial placement randomly from Jelly's reachable free component, keep object identity and location stable during approach, and route to the actual cell with orthogonal hops. Draw background supports, Jelly, then held-object contact layers. One free cell uses local manipulation; zero free cells draws nothing. The same floor anchor applies to every size. Never reintroduce a standalone-prop fallback. Reduced motion disables activities and their physical objects; natural background presentation may remain frozen. Global `animations=false` disables Jelly.


## Interaction priorities

| Situation | Required behavior |
| --- | --- |
| Agent owns a key | Agent rendering and focus retain ownership |
| Launcher/permission menu open | Existing controls menu overlays the scene |
| Update interlude | World yields to the updater |
| Coffee interlude | World yields to the coffee pair |
| Jelly visible | Tap remains a pet interaction |
| World help enabled | Hold Jelly for setup; hold again for documentation |
| Help visible | Tap closes help; help expires automatically |
| Scene-only decoration | No synthetic pet or session action |
| Key reassigned during press | Drop stale action using generation and identity |

Do not use decorative keys to accept permissions, launch processes, or open arbitrary URLs. Browser help uses a constant repository documentation URL, dispatched through the existing physical press queue. Synthetic focus requests cannot invoke it. World help is independent of the launcher controls setting.

## Scene selection strategy

1. Apply master enable, global animation, quiet hours and update/coffee precedence.
2. Resolve local civil date with explicit timezone, discovered timezone, then system time.
3. Apply enabled holiday windows. Exact celebration days outrank neighboring windows; priority breaks remaining collisions. Birthday is highest, then Christmas, New Year, major festivals and smaller events.
4. With no holiday, choose current weather context. Then an observed rain-to-clear transition, night/morning or the local season.
5. Rotate through enabled recipes for that context. A scene override is explicit preview/demo behavior and is labeled accordingly.
6. Combine holiday scenery with current rain/snow when available; never invent temperature or an emergency from a decorative scene.

Every recipe has a stable ID, context, title, sky motif, prop, costume, action and color. Add each ID to the catalog documentation. All 50 additional experiences are individually selectable and disableable, not a list of future work. They reuse tested drawing primitives rather than introducing separate render loops.

## Configuration and privacy

[World reference](../jelly/world.md) defines the INI/CLI schema. Defaults must be validated in one place. Unknown names, invalid booleans, nonfinite coordinates, unpaired coordinates and bad dates fail clearly. CLI writes are atomic and preserve the last valid file. Runtime startup merges `config.json` world values, then `jelly.ini` overrides. Restart applies changes.

Automatic location is approximate IP geolocation, not GPS. A manual coordinate pair bypasses it. Explain the provider requests and the offline switch in setup documentation. Never attach agent labels, prompts, code, repository paths or broker tokens to weather requests. Diagnostics expose weather condition and location source, not precise coordinates.

## Implementation boundaries

| Module | Responsibility |
| --- | --- |
| [jelly.py](../../ocdeck/jelly.py) | Character motion, state, cropped sprite |
| [jelly_art.py](../../ocdeck/jelly_art.py) | Original body, expressions and palette |
| [world_catalog.py](../../ocdeck/world_catalog.py) | Immutable scene recipes |
| [world_art.py](../../ocdeck/world_art.py) | Costume overlays and sparse atmosphere |
| [world_particles.py](../../ocdeck/world_particles.py) | Deterministic particle lifetimes, local floors, impacts and fading |
| [world_props.py](../../ocdeck/world_props.py) | Sized object silhouettes, materials and held animation poses |
| [world_interactions.py](../../ocdeck/world_interactions.py) | Interruptible object-use timeline, grip overlays and persistent outcomes |
| [world_calendar.py](../../ocdeck/world_calendar.py) | Cached calendar dates and priority |
| [world_weather.py](../../ocdeck/world_weather.py) | Bounded background provider requests and snapshots |
| [world.py](../../ocdeck/world.py) | Render-thread director, captions and compositing |
| [world_settings.py](../../ocdeck/world_settings.py) | Schema and INI read validation |
| [world_cli.py](../../ocdeck/world_cli.py) | Supported configuration and offline preview CLI |
| [device.py](../../ocdeck/device.py) | Physical dimensions, input ownership and native image writes |

Never perform network access, filesystem reads or browser launches in frame rendering or HID callbacks. Weather snapshots are immutable and protected by a lock. One daemon worker waits between requests, uses finite response sizes and timeouts, and retires on disconnect. Festival calculations are cached. A missing provider leaves the scene usable offline.

## Reusable feature brief

Copy this checklist into the implementation plan for a new feature:

- **User value:** What can the user see or do on a physical key?
- **Context and priority:** What starts/stops it, and what takes precedence?
- **Geometry:** Show behavior with zero, one, several and all keys free.
- **Art contract:** Palette, logical pixel motifs, anchor and face visibility.
- **Motion:** Pose timing, elapsed-time movement, reduced-motion behavior.
- **Input contract:** Tap/hold behavior, generation validation, timeout and cancellation.
- **Configuration:** Default, valid range, CLI flag, INI field and offline behavior.
- **Failure behavior:** Unavailable network, stale data, reconnect and shutdown.
- **Verification:** Deterministic previews, meaningful behavioral tests, required CI.
- **Documentation:** README value statement, linked guide, reference and release notes.

Before merge, run the repository's Python and Node suites, Ruff checks, Pyright, documentation validation and package build. Inspect real renderer GIFs at native and enlarged sizes. Clearly distinguish simulated geometry checks from physical USB/device validation. Do not claim real-hardware testing without it.

See the [artwork inventory and verification guide](../jelly/artwork.md) before adding a new motif. A new prop needs an identifiable silhouette, material palette, declared floor or airborne placement, and intentional motion. A static glint is appropriate for a solid object; do not make every object bounce.

## Prop interaction contract

`world_objects.py` declares all 57 objects and 25 environmental opportunities. `world_interactions.py` owns placement, routes, reservations, material state and disposal. `world_actions.py` advances contact-driven local motion; `world_object_art.py` only renders it. `world_environment.py` couples effects to sources. Keep cached art immutable.

Activities progress through notice, approach, position, reach, carry/use, return, put-down, admiration, rest and cleanup. A target is reached before pickup. Rakes contact a work patch and return to a rack; vessels lose contents; gifts create a single follow-up toy. Balls stay on one ground plane, sled riders board and dismount, and kites reel back in. Persist only bounded state, outside rendering. Reconcile coordinates on restore and preserve the reset generation marker.

All priorities in the table above remain authoritative. Cancelled held objects enter storage immediately. Changing scene themes does not cancel an active task. `living_world=false`, `interactions=false`, `props=false` and reduced motion suppress activities without leaving abandoned props.

Regenerate `scripts/review_living_assets.py` and `scripts/preview_living_world.py` after art changes. The coverage manifest and per-asset review must describe real behavior, with native 72/80/96 evidence. Run semantic tests and the complete repository checks before merging. Offline previews do not establish physical-device verification.
