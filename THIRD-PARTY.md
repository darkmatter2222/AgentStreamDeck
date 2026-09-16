# Dependencies and references

This source bundle installs dependencies through pip; it does not bundle Python, OpenCode, Windows Terminal, Elgato software, or their binaries. Their respective licenses apply. Consult the installed distribution metadata for exact dependency versions and license text.

- python-elgato-streamdeck / `streamdeck` 0.10.0: MIT; https://github.com/abcminiuser/python-elgato-streamdeck
- `hidapi` 0.15.0: Python wrapper and included native HID library; see https://github.com/trezor/cython-hidapi and https://github.com/libusb/hidapi for component licenses.
- Pillow: HPND; https://github.com/python-pillow/Pillow
- psutil 7.2.2: BSD-3-Clause; https://github.com/giampaolo/psutil

Animation frames are composed by Pillow using procedural status artwork and the bundled harness icons listed below. No Elgato artwork or API credentials are included.

Research citations and architecture evidence are in docs/RESEARCH.md. That report predates the final implementation choices: this bundle uses READY by default (configurable), the direct HID design, a per-user logon task, and a dynamic loopback port. Any implementation proposal in the research report should be read alongside the final source and ARCHITECTURE.md.


## Harness icons

Icons identify third-party integrations; their trademarks remain with their owners.
Bundling an icon does not imply endorsement or relicense it under AgentStreamDeck's
Apache license. Official app-icon pixels are preserved apart from resizing and
user-selected whole-button brightness. The Copilot SVG is rendered in white for
the dark button background; its geometry is unchanged.

| Icon | Official source / provenance |
|---|---|
| OpenCode | [Official site app icon](https://opencode.ai/favicon-96x96-v3.png), [brand page](https://opencode.ai/brand) |
| Claude | [Official Claude website app icon](https://cdn.prod.website-files.com/6889473510b50328dbb70ae6/68c33859cc6cd903686c66a2_apple-touch-icon.png), linked by Anthropic's Claude page |
| Cursor | [Official app icon](https://cursor.com/marketing-static/icon-192x192-light.png), [brand guidelines](https://cursor.com/brand) |
| Gemini | [Official Google app icon](https://www.gstatic.com/lamda/images/gemini_sparkle_4g_512_lt_f94943af3be039176192d.png), linked by gemini.google.com |
| Copilot CLI / VS Code | [GitHub Primer Octicons Copilot UI icon](https://github.com/primer/octicons/blob/main/icons/copilot-24.svg), MIT; [included license](ocdeck/assets/logos/OCTICONS-LICENSE.txt) |

GitHub's [brand toolkit](https://brand.github.com/brand-identity/copilot) distinguishes
its current standalone product logo from the Copilot UI icon. AgentStreamDeck uses the
small UI icon for integration identification, not the deprecated standalone lockup.

Fetched 2026-09-12. Exact source URLs, source SHA-256 hashes, and bundled PNG hashes
are recorded in [sources.json](ocdeck/assets/logos/sources.json). Runtime assets are
local PNGs included in wheel/sdist packages; rendering needs no network access or
SVG library. The original Copilot SVG is retained alongside its PNG for provenance.


## 2.1 dependencies and diagnostic policy

`packaging` (Apache-2.0 / BSD-2-Clause) compares release versions. Development tools
are Ruff, Pyright, pre-commit and build. Release SBOM generation uses cyclonedx-bom.
The wheel bundles the project's own Node/PowerShell source as runtime data.
Codex uses a text identifier and procedural status symbol; no new trademark image
is bundled. Never collect prompts, transcripts, tool input/output or provider
configuration in reports. Redact credential fields and bearer tokens at the log
and report output boundaries. See [NEXT.md](docs/NEXT.md) for coverage limits.

## Living-world data and original art

World props and costumes are original procedural pixel drawings in `ocdeck/world_art.py`. Calendar calculations use the MIT-licensed `holidays` and `pyluach` packages, plus timezone data from `tzdata`. Weather data: [Open-Meteo](https://open-meteo.com/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Approximate IP location: [IPWhois](https://ipwhois.io/). See [provider behavior and usage limits](docs/jelly/world.md#weather-and-location).

## Stream Deck product photographs

The documentation hardware composites use Elgato product photographs sourced from MaxGaming, JB Hi-Fi and GearTechs. Photographs and hardware marks remain the property of their respective owners and are excluded from the Apache software license. See [photo sources and reproduction](docs/hardware/README.md#image-sources-and-reproduction).
