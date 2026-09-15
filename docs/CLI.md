# AgentStreamDeck CLI command and option reference

[Project overview](../README.md) · [Documentation index](README.md)

The installed console command is `ocdeck`; `python -m ocdeck` runs the same parser and avoids Scripts/PATH issues. This reference covers every subcommand and argument in [the CLI source](../ocdeck/__main__.py).

```text
python -m ocdeck --version
python -m ocdeck --help
python -m ocdeck appearance --help
```

## Command index

| Command | Purpose |
|---|---|
| [`controls`](#controls) | Configure launcher profiles, gestures and native permission review; validate or launch a saved profile. |
| [`broker`](#broker) | Run the foreground device broker. |
| [`install`](#install) | Register per-user startup and start the broker. |
| [`status`](#status) | Print the broker status JSON, including slots, overflow, device input, focus and update state. |
| [`stop`](#stop) | Request graceful shutdown of the running broker. |
| [`devices`](#devices) | Enumerate supported USB devices, model, key count and serial information without starting a renderer.. |
| [`hardware-check`](#hardware-check) | Run an interactive physical image/key diagnostic. |
| [`doctor`](#doctor) | Run diagnostic checks for the selected project. |
| [`report`](#report) | Write a scrubbed diagnostic ZIP. |
| [`uninstall`](#uninstall) | Remove owned startup/integrations and back up local configuration. |
| [`launch`](#launch) | Legacy OpenCode managed Windows launcher. |
| [`route`](#route) | Internal compatibility entry point for older OpenCode shims. |
| [`worker`](#worker) | Internal OpenCode supervisor. |
| [`identity`](#identity) | Print the exact PID and process creation timestamp for a local process. |
| [`install-plugin`](#install-plugin) | Install the global OpenCode adapter after `install` creates runtime metadata. |
| [`harness-install`](#harness-install) | Merge, preview or remove one project’s native hooks. |
| [`harness-launch`](#harness-launch) | Optional managed hook supervisor. |
| [`harness-worker`](#harness-worker) | Internal hook-harness supervisor taking a generated JSON specification. |
| [`start`](#start) | Optional compatibility wrapper selecting OpenCode or a native-hook profile. |
| [`preview`](#preview) | Render a six-key GIF with sample running/idle/input/unknown/ready states. |
| [`appearance`](#appearance) | Display or save visual preferences. |
| [`focus`](#focus) | Request focus for a one-based assigned slot. |

## Argument rules

Put AgentStreamDeck options before the literal `--` separator when forwarding arguments to a harness. Arguments after it belong to that harness. JSON settings use underscores where CLI flags use hyphens. Every subcommand also accepts `-h` / `--help`. Argparse rejects invalid syntax/choices with exit status 2; caught runtime errors return 1. Some compatibility launch paths return their child status.

## controls

Every setting for the new launcher/review controls is available through this command. [Hands-on tutorials](TUTORIALS.md#launch-a-new-agent-without-leaving-the-deck) · [Defaults, INI format and harness coverage](features/DECK-CONTROLS.md).

```text
python -m ocdeck controls configure [--enabled | --no-enabled]
    [--permissions | --no-permissions] [--hold-ms N] [--menu-timeout N] [--request-timeout N]
python -m ocdeck controls show
python -m ocdeck controls validate
python -m ocdeck controls repo set NAME [--directory PATH]
    [--harness PROFILE ...] [--arg VALUE ...] [--clear-args]
    [--executable PATH] [--clear-executable]
python -m ocdeck controls repo remove NAME
python -m ocdeck controls launch NAME --harness PROFILE
```

`configure` preserves omitted fields and requires a broker restart. `--hold-ms` accepts 300–2000 (default 650), `--menu-timeout` 10–300 seconds (45), and `--request-timeout` 10–110 seconds (110). Controls and permission decisions default off. Enabling permissions also requires enabled controls.

`repo set` creates or updates one named profile in `launcher.ini`; a new profile requires `--directory`. Repeat `--harness` for each choice: `opencode`, `claude`, `codex`, `copilot-cli`, `copilot-vscode`, `gemini`, `cursor`. Repeated choices or unknown INI fields are rejected. Default harness choices are OpenCode and Claude. Omitted fields are retained; supplied harness/argument lists replace old lists. Use `--arg=--option` when an argument begins with a dash. Arguments are stored as a JSON array and never evaluated as a shell command. `--clear-args` and `--clear-executable` reset those optional fields. Use distinct profiles for harness-specific launch arguments.

`show` returns JSON settings and profiles. `validate` returns JSON checks and exit 1 when any check fails; it inspects directories, PATH executables, adapter manifests and Windows Terminal, without launching agents. `launch` uses the same saved-folder launch path as the deck, but does not require a physical key press. Permission decisions themselves are physical/native-UI actions, not a CLI automation endpoint.

## broker

Run the foreground device broker. `--mock` uses simulated keys and does not open USB. Use a separate OCDECK_HOME for a test broker.

```text
python -m ocdeck broker [-h] [--mock]
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `--mock` | `False` | toggle |

## install

Register per-user startup and start the broker. Windows uses the AgentStreamDeck Broker task; Linux uses agentstreamdeck.service. `--no-start` registers without starting; `--no-opencode-plugin` skips optional OpenCode installation.

```text
python -m ocdeck install [-h] [--no-start] [--no-opencode-plugin]
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `--no-start` | `False` | toggle |
| `--no-opencode-plugin` | `False` | toggle |

## status

Print the broker status JSON, including slots, overflow, device input, focus and update state. `--json` is accepted for compatibility; output is JSON with or without it.

```text
python -m ocdeck status [-h] [--json]
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `--json` | `False` | toggle |

## stop

Request graceful shutdown of the running broker. A service supervisor can restart it; use the platform service controls when you need hardware to remain released.

```text
python -m ocdeck stop [-h]
```

| Argument | Default | Accepted values / type |
|---|---|---|

## devices

Enumerate supported USB devices, model, key count and serial information without starting a renderer.

```text
python -m ocdeck devices [-h]
```

| Argument | Default | Accepted values / type |
|---|---|---|

## hardware-check

Run an interactive physical image/key diagnostic. Release USB from the broker and Elgato first. This is not a headless CI check.

```text
python -m ocdeck hardware-check [-h]
```

| Argument | Default | Accepted values / type |
|---|---|---|

## doctor

Run diagnostic checks for the selected project. `--no-device` avoids HID enumeration/opening. PASS is verified, FAIL is a detected problem, MANUAL still needs interactive verification. Any FAIL produces exit code 1.

```text
python -m ocdeck doctor [-h] [--project PROJECT] [--no-device] [--json]
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `--project` | `'.'` | string |
| `--no-device` | `False` | toggle |
| `--json` | `False` | toggle |

## report

Write a scrubbed diagnostic ZIP. Default filename is agentdeck-report.zip, default log tail is 100 lines, and the cap is 2,000 lines. Existing output files are refused.

```text
python -m ocdeck report [-h] [--output OUTPUT] [--lines LINES]
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `--output` | `'agentdeck-report.zip'` | string |
| `--lines` | `100` | int |

## uninstall

Remove owned startup/integrations and back up local configuration. `--all` is required. Repeat `--scan` for project roots; without it the current directory is scanned in addition to recorded projects. Preview with `--dry-run`. This does not uninstall the pip distribution.

```text
python -m ocdeck uninstall [-h] --all [--scan SCAN] [--dry-run]
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `--all` | `required` | toggle |
| `--scan` | `[]` | string |
| `--dry-run` | `False` | toggle |

## launch

Legacy OpenCode managed Windows launcher. Needs Windows Terminal and legacy install metadata containing the real OpenCode executable. Prefer launching opencode normally after plugin installation.

```text
python -m ocdeck launch [-h] ...
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `args` | `none` | remaining harness arguments |

## route

Internal compatibility entry point for older OpenCode shims. Routes interactive calls through a managed window and utility/headless commands to the recorded executable. Fresh plugin-first installation does not create these shims.

```text
python -m ocdeck route [-h] ...
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `args` | `none` | remaining harness arguments |

## worker

Internal OpenCode supervisor. Takes a generated launch-specification JSON file; do not hand-author or invoke for ordinary use.

```text
python -m ocdeck worker [-h] spec
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `spec` | `required` | string |

## identity

Print the exact PID and process creation timestamp for a local process. Used by adapters to prevent PID reuse from stealing an assignment.

```text
python -m ocdeck identity [-h] pid
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `pid` | `required` | int |

## install-plugin

Install the global OpenCode adapter after `install` creates runtime metadata. Server mode is the default. `--config-dir` overrides OpenCode configuration discovery. TUI mode is an advanced compatibility path; see the OpenCode guide.

```text
python -m ocdeck install-plugin [-h] [--mode {server,tui}]
                             [--config-dir CONFIG_DIR]
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `--mode` | `'server'` | server, tui |
| `--config-dir` | `none` | string |

## harness-install

Merge, preview or remove one project’s native hooks. Profile choices are codex, claude, copilot-cli, copilot-vscode, gemini and cursor. OpenCode uses install-plugin instead. Preserve the project receipt and review native trust requirements.

```text
python -m ocdeck harness-install [-h] [--project PROJECT] [--remove] [--dry-run]
                              {codex,claude,copilot-cli,copilot-vscode,gemini,cursor}
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `profile` | `required` | codex, claude, copilot-cli, copilot-vscode, gemini, cursor |
| `--project` | `'.'` | string |
| `--remove` | `False` | toggle |
| `--dry-run` | `False` | toggle |

## harness-launch

Optional managed hook supervisor. `--executable` selects a CLI or existing launcher. On Windows the default creates a dedicated Terminal window; `--current-window` uses the current window. On other systems it runs in the current process context without Windows focus.

```text
python -m ocdeck harness-launch [-h] --profile
                             {codex,claude,copilot-cli,copilot-vscode,gemini,cursor}
                             [--executable EXECUTABLE] [--current-window]
                             ...
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `--profile` | `required` | codex, claude, copilot-cli, copilot-vscode, gemini, cursor |
| `--executable` | `none` | string |
| `--current-window` | `False` | toggle |
| `args` | `none` | remaining harness arguments |

## harness-worker

Internal hook-harness supervisor taking a generated JSON specification. Owns the legacy relay and child lifetime; not a normal end-user entry point.

```text
python -m ocdeck harness-worker [-h] spec
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `spec` | `required` | string |

## start

Optional compatibility wrapper selecting OpenCode or a native-hook profile. `--launcher` accepts an existing synchronous BAT/CMD/EXE launcher. Fresh OpenCode installs lack legacy executable metadata; use normal opencode startup instead.

```text
python -m ocdeck start [-h] --profile
                    {opencode,codex,claude,copilot-cli,copilot-vscode,gemini,cursor}
                    [--launcher LAUNCHER]
                    ...
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `--profile` | `required` | opencode, codex, claude, copilot-cli, copilot-vscode, gemini, cursor |
| `--launcher` | `none` | string |
| `args` | `none` | remaining harness arguments |

## preview

Render a six-key GIF with sample running/idle/input/unknown/ready states. Explicit visual flags temporarily override saved settings, including per-slot preferences. This previews agent key appearance, not Jelly, and does not save configuration.

```text
python -m ocdeck preview [-h] [--output OUTPUT]
                      [--preset {studio,neon,focus,readable,marquee}]
                      [--alias ALIAS] [--text-effect {none,scroll,shimmer}]
                      [--text-size {small,normal,large}]
                      [--text-align {left,center,right}]
                      [--badge {dot,ring,pill}]
                      [--border {solid,double,corners,none}]
                      [--background {solid,gradient,grid}]
                      [--logo-size {small,normal,large}]
                      [--layout {classic,harness,minimal}]
                      [--theme {high-contrast,classic,aurora,ocean,accessible,mono}]
                      [--effect {breathe,glow,steady}]
                      [--primary {status,project,harness,detail,custom,alias,none}]
                      [--secondary {status,project,harness,detail,custom,alias,none}]
                      [--custom-text CUSTOM_TEXT]
                      [--show-slot | --no-show-slot] [--speed SPEED]
                      [--intensity INTENSITY] [--brightness BRIGHTNESS]
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `--output` | `'animation-preview.gif'` | string |
| `--preset` | `none` | studio, neon, focus, readable, marquee |
| `--alias` | `none` | string |
| `--text-effect` | `none` | none, scroll, shimmer |
| `--text-size` | `none` | small, normal, large |
| `--text-align` | `none` | left, center, right |
| `--badge` | `none` | dot, ring, pill |
| `--border` | `none` | solid, double, corners, none |
| `--background` | `none` | solid, gradient, grid |
| `--logo-size` | `none` | small, normal, large |
| `--layout` | `none` | classic, harness, minimal |
| `--theme` | `none` | high-contrast, classic, aurora, ocean, accessible, mono |
| `--effect` | `none` | breathe, glow, steady |
| `--primary` | `none` | status, project, harness, detail, custom, alias, none |
| `--secondary` | `none` | status, project, harness, detail, custom, alias, none |
| `--custom-text` | `none` | string |
| `--show-slot / --no-show-slot` | `none` | toggle |
| `--speed` | `none` | float |
| `--intensity` | `none` | float |
| `--brightness` | `none` | float |

## appearance

Display or save visual preferences. Without visual flags, displays config. `--slot` uses one-based slots 1–32; omission changes global defaults. `--preset` resets visual fields at that scope while preserving labels, then explicit flags apply. `--dry-run` prints a diff and PNG data URI without writing config, export or preview files. Import replaces visual fields only; restart the broker after saving.

```text
python -m ocdeck appearance [-h]
                         [--slot {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32}]
                         [--preset {studio,neon,focus,readable,marquee}]
                         [--alias ALIAS] [--text-effect {none,scroll,shimmer}]
                         [--text-size {small,normal,large}]
                         [--text-align {left,center,right}]
                         [--badge {dot,ring,pill}]
                         [--border {solid,double,corners,none}]
                         [--background {solid,gradient,grid}]
                         [--logo-size {small,normal,large}]
                         [--layout {classic,harness,minimal}]
                         [--theme {high-contrast,classic,aurora,ocean,accessible,mono}]
                         [--effect {breathe,glow,steady}]
                         [--primary {status,project,harness,detail,custom,alias,none}]
                         [--secondary {status,project,harness,detail,custom,alias,none}]
                         [--custom-text CUSTOM_TEXT]
                         [--show-slot | --no-show-slot] [--speed SPEED]
                         [--intensity INTENSITY] [--brightness BRIGHTNESS]
                         [--dry-run] [--export EXPORT_FILE]
                         [--import IMPORT_FILE]
                         [--fps {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30}]
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `--slot` | `none` | 1–32 |
| `--preset` | `none` | studio, neon, focus, readable, marquee |
| `--alias` | `none` | string |
| `--text-effect` | `none` | none, scroll, shimmer |
| `--text-size` | `none` | small, normal, large |
| `--text-align` | `none` | left, center, right |
| `--badge` | `none` | dot, ring, pill |
| `--border` | `none` | solid, double, corners, none |
| `--background` | `none` | solid, gradient, grid |
| `--logo-size` | `none` | small, normal, large |
| `--layout` | `none` | classic, harness, minimal |
| `--theme` | `none` | high-contrast, classic, aurora, ocean, accessible, mono |
| `--effect` | `none` | breathe, glow, steady |
| `--primary` | `none` | status, project, harness, detail, custom, alias, none |
| `--secondary` | `none` | status, project, harness, detail, custom, alias, none |
| `--custom-text` | `none` | string |
| `--show-slot / --no-show-slot` | `none` | toggle |
| `--speed` | `none` | float |
| `--intensity` | `none` | float |
| `--brightness` | `none` | float |
| `--dry-run` | `False` | toggle |
| `--export` | `none` | string |
| `--import` | `none` | string |
| `--fps` | `none` | 1–30 |

## focus

Request focus for a one-based assigned slot. This is a synthetic focus check, not proof that a physical USB key works and not a way to trigger Jelly actions.

```text
python -m ocdeck focus [-h] slot
```

| Argument | Default | Accepted values / type |
|---|---|---|
| `slot` | `required` | int |

## Related guides

[Install](FIRST-RUN.md) · [Appearance fields](reference/APPEARANCE.md) · [Configuration fields](reference/CONFIG.md) · [Diagnostics](features/DIAGNOSTICS.md) · [Launchers](LAUNCHERS.md)

## world

`ocdeck world reset` schedules a world-memory reset for the next broker restart. Jelly needs are preserved; a generation marker prevents old background saves from undoing the reset.

Configure holiday, weather and seasonal scenes in `jelly.ini`. Restart the broker to apply.

- `world configure`: save any combination of the flags below.
- `world show`: print effective settings.
- `world catalog`: list every recipe and stable ID.
- `world validate`: validate without network requests.
- `world preview scene --keys 6 --output scene.gif`: offline GIF; `--keys` accepts 6, 15 or 32.

[Setup, ranges, defaults and examples](jelly/world.md) · [All scene IDs](jelly/world-catalog.md)

| INI field | Default | CLI flag |
| --- | --- | --- |
| `enabled` | `true` | `--enabled` / `--no-enabled` |
| `holidays` | `true` | `--holidays` / `--no-holidays` |
| `weather` | `true` | `--weather` / `--no-weather` |
| `seasons` | `true` | `--seasons` / `--no-seasons` |
| `costumes` | `true` | `--costumes` / `--no-costumes` |
| `particles` | `true` | `--particles` / `--no-particles` |
| `props` | `true` | `--props` / `--no-props` |
| `living_world` | `false` | `--living-world` / `--no-living-world` (unfinished development director; restart required) |
| `interactions` | `true` | `--interactions` / `--no-interactions` |
| `interaction_seconds` | `24` | `--interaction-seconds` (12–300) |
| `captions` | `true` | `--captions` / `--no-captions` |
| `help` | `true` | `--hold-help` / `--no-hold-help` |
| `auto_location` | `true` | `--auto-location` / `--no-auto-location` |
| `reduced_motion` | `false` | `--reduced-motion` / `--no-reduced-motion` |
| `country` | `auto` | `--country` |
| `timezone` | `auto` | `--timezone` |
| `latitude` | `empty` | `--latitude` |
| `longitude` | `empty` | `--longitude` |
| `hemisphere` | `auto` | `--hemisphere` |
| `units` | `auto` | `--units` |
| `poll_seconds` | `900` | `--poll-seconds` |
| `stale_seconds` | `3600` | `--stale-seconds` |
| `scene_seconds` | `24` | `--scene-seconds` |
| `caption_seconds` | `90` | `--caption-seconds` |
| `hint_seconds` | `1800` | `--hint-seconds` |
| `hold_ms` | `900` | `--hold-ms` |
| `before_days` | `1` | `--before-days` |
| `after_days` | `1` | `--after-days` |
| `halloween_days` | `7` | `--halloween-days` |
| `christmas_days` | `12` | `--christmas-days` |
| `birthday` | `empty` | `--birthday` |
| `quiet_start` | `-1` | `--quiet-start` |
| `quiet_end` | `-1` | `--quiet-end` |
| `max_keys` | `32` | `--max-keys` |
| `holiday_ids` | `july4,thanksgiving,christmas,holi,easter,halloween,newyear,valentine,lunar,diwali,eid,hanukkah,patrick,earth,birthday` | `--holiday-ids` |
| `disabled_scenes` | `empty` | `--disabled-scenes` |
| `scene_override` | `empty` | `--scene-override` |
| `weather_override` | `empty` | `--weather-override` |
| `date_override` | `empty` | `--date-override` |
