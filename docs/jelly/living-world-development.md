# Living-world architecture and verification

[Controls](world.md) · [Every object and preview](prop-review.md) · [Coverage manifest](world-coverage.json) · [Scene catalog](world-catalog.md)

Physical objects appear as part of an achievable activity. The default director replaces the old standalone-prop path. Disabling living-world activities removes their objects; it does not switch back to ambient props.

## Lifecycle and ownership

The director owns one activity, one held object, up to eight remembered objects, 24 recent activities and 12 recent destinations. It ranks feasible scene/environment opportunities using existing needs and repetition penalties. Initial placement samples the reachable free component. Tools get a separate work cell when available. `route_to` reaches the actual target using the existing orthogonal hop animation.

Notice, approach, local position and reach precede material updates. Carrying uses a pose-aware mirrored grip. Timelines then perform use, return/put-down, admiration, a short rest and cleanup. Tools rest against visible supports. Object-specific contact timelines handle consumption, watering, gathering, ball pursuit, sled boarding and kite reeling. Gifts create one follow-up ball, fountains carry water to a plant, and windsocks lead to kite play.

Material progress advances only during valid visible use, with elapsed-time deltas capped after stalls. Outcomes are guarded against duplicate application. Scene changes preserve the current activity; occupied keys, input, menus, help, coffee, updates and agent attention cancel it immediately. Cancellation stores a carried object and releases actor control. Resuming validates geometry and routes again.

Plants and projects can reuse completed identities on later visits. Snapshots preserve bounded growth, progress and history, and reconcile all restored coordinates. Existing Jelly persistence writes immutable snapshots outside rendering with at most one worker. `ocdeck world reset` writes a generation marker, applied at the next broker restart, so an old background save cannot undo the reset. There is no offline neglect simulation.

## Environmental behavior

Natural rain, snow, leaves and wind retain the particle engine introduced in 3.0.13. Sourced displays such as balloons, lanterns, confetti, lights and smoke no longer appear as unrelated global objects. Their activity provides the source. Butterfly/firefly movement, telescope targets, fireworks responses, lamp illumination and snowfall opportunities use activity state. Environmental reactions are scheduled around completed work rather than interrupting every particle.

[All atmosphere-to-activity mappings](world-coverage.json) include the existing 25 effects. Celestial landmarks are observed from a reachable activity location, not picked up. All 75 scenes retain compatible object or environment opportunities.

## Reproduce the review

```console
python scripts/review_living_assets.py
python scripts/preview_living_world.py
python -m unittest discover -s tests -p test_world_lifecycle.py
python -m unittest discover -s tests -p test_living_world.py
python scripts/benchmark_living_world.py --baseline-checkout ../baseline-3.0.13
```

[Activity timelines](living-previews/activity-timelines.json) record complete generated sequences. [Rake travel, Mini](living-previews/autumn_rake-72.gif), [Original](living-previews/autumn_rake-80.gif), [XL](living-previews/autumn_rake-96.gif), and [session takeover](living-previews/autumn_rake-72-takeover.gif) exercise whole-deck navigation. Individual native captures and stage sheets are linked from the per-object review. These are procedural-renderer recordings, not hand-authored mockups.

The native review corrected unsupported gift-lid motion, static snowflake contact, lamp shading, telescope adjustment, incremental egg decoration, letter folding and construction stages. Mini stance placement accounts for its 1x logical artwork; Original and XL use the existing 2x art scale. Jelly's original body artwork remains unchanged.

## Performance and practical limits

[Comparison measurements](living-previews/comparison.json) use separate interpreter processes per checkout/layout, the same scene, seed, free-key layout and simulated duration. They include first-object-frame and warm composition timings. The candidate executes longer routes and different poses than the baseline, so this is an end-to-end workload comparison, not an isolated primitive benchmark. No USB writes or physical screen latency are measured.

Single-key play uses a short local ground path. This is authored pixel animation with bounded material state, not a physics engine. The expanded home/economy/crafting concepts remain outside this implementation. Repository CI and semantic tests cover source behavior; actual Stream Deck hardware still requires user observation.

## Validation record

The local full Python suite exercises navigation, persistence, button precedence, weather and object lifecycles; the Node suite exercises the harness and permission paths. Ruff, Pyright, documentation/media checks, package build and an installed-wheel import check are required alongside hosted CI. The process-restart test has a known local skip because this container exposes host PIDs through `/proc`; hosted CI remains authoritative for that platform behavior.

The generated evidence includes 246 complete object/environment recordings (57 objects plus 25 atmospheres at three native sizes) and [225 completed scene/layout checks](living-previews/scene-review.json). The scene review reclaims a middle key and verifies that rendering stays within free keys. The semantic tests separately check takeover during activity stages, gift identity, fountain travel, frame-rate equivalence, capped time jumps, cleanup, reset markers and disabled-mode absence of orphan props.
