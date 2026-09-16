# Launch agents and review permissions from your Stream Deck

[Project overview](../../README.md) · [Tutorials](../TUTORIALS.md) · [CLI reference](../CLI.md#controls)

Save your project folders once, choose an agent on the deck, and open a dedicated terminal in that folder. When a supported native permission request arrives, select that specific request and press **ACCEPT** or **REJECT** once. Controls are opt-in; ordinary session taps still focus their windows.

![Actual control renderer on a simulated six-key deck: project picker, launch confirmation and permission review](../controls/preview.gif)

This is a source-rendered UI preview, not a recording of physical hardware.

## Enable the controls

```powershell
python -m ocdeck controls configure --enabled --permissions
python -m ocdeck controls repo set "My App" --directory "C:\Projects\MyApp" --harness opencode --harness claude
python -m ocdeck harness-install claude --project "C:\Projects\MyApp"
python -m ocdeck controls validate
```

Restart the broker after changing controls settings. On a standard Windows installation:

```powershell
Stop-ScheduledTask -TaskName 'AgentStreamDeck Broker'
Start-ScheduledTask -TaskName 'AgentStreamDeck Broker'
```

Repository edits take effect when you next open the picker. CLI commands create and edit `launcher.ini` under `%USERPROFILE%\.opencode-deck`, or `OCDECK_HOME` when overridden. You can also edit that file directly. All new configuration has CLI equivalents; no manual file editing is required.

## How the keys work

| Gesture / screen | Behavior |
|---|---|
| Tap a session | Focus its existing window. With controls enabled, taps fire on release. |
| Hold and release an unused key | Open the project picker. Works even when Jelly occupies that key. |
| Hold and release a session | Open its session menu: review requests, focus, or start a new agent. |
| Hold progress | A progress bar appears after 200 ms; RELEASE appears when the configured threshold is reached. |
| Project picker | Four projects per page; NEXT cycles pages. Pick a project, then a harness. |
| Confirmation | Shows project, folder and harness. LAUNCH requests a new dedicated window. |
| Request picker | Four pending requests per page. Select the tool/request preview you want to review. |
| Permission review | Tool and project, paged detail preview, TERMINAL, ACCEPT, REJECT, BACK. |
| DETAIL | Advance through the bounded request preview. Page count is shown. |
| TERMINAL | Return this request to native handling and focus its window. |
| ACCEPT / REJECT | Submit one decision for the displayed ticket. Never grants “always allow.” |
| BACK | Return to live sessions. A pending request keeps waiting until handled or expired. |
| Timeout | Menus close after inactivity. Request expiry returns control to the native harness. |

The menu occupies the first six keys on Mini, Original/MK.2 and XL. Extra keys retain their live-session behavior. The normal dashboard continues updating while menus are open. Text, color and labels distinguish acceptance, rejection and navigation. Small keys show previews; use TERMINAL for full commands, arguments or ambiguous requests.

## Harness coverage

| Harness | Launch from saved folder | Native deck decision | Requirements / limits |
|---|---|---|---|
| OpenCode | Yes | Yes, server plugin | Live `permission.asked` event with session/request IDs and a supported SDK reply method. TUI-only plugin and missed historical requests use native UI. |
| Claude Code | Yes | Yes | Reinstall the current project hooks. `PermissionRequest` waits for a physical decision; other hook events remain observers. |
| Codex | Yes | Focus native prompt | Existing adapter observes permission state; this feature does not supply Codex decisions. |
| Copilot CLI | Yes | Focus native prompt | Its current permission hook runs before rule evaluation, not just at a pending user prompt. This feature does not intercept every tool call. |
| Copilot VS Code | Yes, preview | Focus editor | Managed launch uses a separate editor profile, as in the existing integration. |
| Gemini CLI | Yes | Focus native prompt | Notification coverage is not a request-specific approval transport. |
| Cursor CLI | Yes | Focus native prompt | Existing activity hooks are retained; no guessed keystrokes or desktop Cursor control. |

Windows and Windows Terminal are required for deck launches. CLI executables must be installed and discoverable by the broker's environment. Install the relevant project hooks before launching. Neither launch nor configuration silently installs or trusts a harness, edits its permission rules, authenticates an account, or creates a Git worktree. For parallel work in one repository, configure separate existing worktree directories as separate profiles.

## Configuration reference

| CLI option on `controls configure` | Stored field | Default | Range / behavior |
|---|---|---|---|
| `--enabled` / `--no-enabled` | `controls.enabled` | false | Enable/disable the hold menus. |
| `--permissions` / `--no-permissions` | `controls.permissions` | false | Enable native request handoff; also requires controls enabled. |
| `--hold-ms` | `controls.hold_ms` | 650 | Integer 300–2000 ms. |
| `--menu-timeout` | `controls.menu_timeout` | 45 | Integer 10–300 seconds. |
| `--request-timeout` | `controls.request_timeout` | 110 | Integer 10–110 seconds. |

`controls show` prints effective settings and profiles. `controls validate` checks configuration, folders, executables, project adapter manifests and Windows Terminal; it does not prove hook trust or live native API compatibility. Global animation enablement is respected. Settings require a broker restart; the INI catalog is reread whenever the picker opens.

| Profile option on `controls repo set NAME` | INI key | Meaning |
|---|---|---|
| `--directory` | `directory` | Explicit working directory. CLI resolves relative input to an absolute path; hand-written INI paths must be absolute. |
| Repeated `--harness` | `harnesses` | Ordered picker choices; defaults to OpenCode and Claude for new profiles. |
| Repeated `--arg` | `args` | Exact argv elements, stored as a JSON array. `--clear-args` removes them. |
| `--executable` | `executable` | Optional CLI path or existing BAT/CMD launcher; `--clear-executable` restores automatic selection. |

Omitted fields retain their previous values. Supplied harness/argument lists replace the previous list. Arguments and executable apply to every harness in that profile, so use a separate named profile for harness-specific flags or launch scripts. Names control picker order through INI section order. Missing folders and full decks produce an on-device error; no launch occurs. Launch I/O runs outside the render/HID threads, and a three-second cooldown suppresses rapid repeat launches.

```ini
[repo:My App]
directory = C:\Projects\MyApp
harnesses = opencode,claude,codex,copilot-cli,gemini,cursor
args = []

[repo:Local OpenCode]
directory = C:\Projects\MyApp
harnesses = opencode
executable = C:\HomeAI\opencode-local.bat
args = []
```

## Request identity, privacy and failure behavior

Native requests receive random, single-use tickets bound to a live process and slot generation. New sessions cannot inherit old approvals. Clients refresh a short lease only while the request is live; expiry, process exit, native cancellation, broker restart and a lost bridge invalidate pending tickets. Up to 64 requests may be outstanding. A decision is delivered at most once; uncertain delivery is never retried as a new approval.

The decision screen distinguishes queued, delivered and confirmed handoff. “Decision sent to harness” means the adapter returned its native response, not that the tool executed successfully. If confirmation is missing, inspect the native session. Native policies and other installed hooks still apply. Ordinary focus, question prompts and synthetic `/v1/focus` calls cannot approve requests.

By default, lifecycle transport remains metadata-only. Explicitly enabling permission controls allows bounded tool-input previews for Claude and permission-pattern previews for OpenCode to pass through the authenticated loopback broker. These previews are scrubbed for recognized credential patterns and held in memory, not written to logs or public status. Scrubbing cannot recognize every secret. Preview text is limited to 2,000 characters; use the native prompt for complete context. Restarting the broker clears all tickets.

## Troubleshooting

| Symptom | Check |
|---|---|
| Holding only focuses | Enable controls, restart broker, hold until RELEASE appears, then release. |
| Empty picker | Add a profile with `controls repo set`; run `controls show`. |
| Missing executable | Run `controls validate`, install the CLI, and restart the broker so it inherits the updated PATH. |
| Window opens without status | Install the project's adapter, restart the harness, inspect `ocdeck doctor --project ...`. |
| Claude requests do not appear | Reinstall Claude hooks from this branch; old hook entries have a five-second timeout. Trust/enable hooks in the native harness. |
| REVIEW says use terminal | No live supported ticket exists. Activity/notifications alone do not imply native-decision support. |
| Decision not confirmed | Focus the terminal; never assume an API timeout means the tool was denied. |
| Multiple agents edit the same files | Use separate existing worktrees and separate named profiles. |

See the [hands-on tutorials](../TUTORIALS.md#launch-a-new-agent-without-leaving-the-deck), [design research](../development/DECK-CONTROLS-RESEARCH.md), and [API contract](../API.md#permission-controls).
