# Develop, test and document AgentStreamDeck

[Read the UI, UX and implementation contract](DESIGN_SYSTEM.md) before changing visuals or interaction. Rebuild world previews with `python scripts/preview_world.py`.

[Project overview](../../README.md) · [Documentation index](../README.md)

## Development setup

```bash
git clone https://github.com/darkmatter2222/AgentStreamDeck.git
cd AgentStreamDeck
python -m pip install -e ".[dev]"
pre-commit install
```

Use Node.js 20+ for plugins/tests. Edit original modules in ocdeck/, plugins/ and scripts/; setup.py copies runtime assets when building wheels. Never edit a generated build/runtime copy as your source change.

[Living-world architecture and verification](../jelly/living-world-development.md). The intention director is the default; disabling it suppresses objects rather than selecting the legacy renderer.

## Automated checks

```bash
python -m unittest discover -s tests -v
node --test tests/facts.test.mjs tests/harnesses.test.mjs tests/next.test.mjs
ruff check ocdeck tests
ruff format --check ocdeck tests
pyright
python scripts/check-docs.py
```

The Python suite includes subprocess and broker integration; Node suites validate native mappings and shared facts. scripts/Test.ps1 is a Windows convenience runner. CI uses Windows and Ubuntu with Python 3.11/3.13. Tests without real USB, native logins or a Windows desktop cannot establish those acceptance gates.

## Isolated mock broker

```bash
export OCDECK_HOME="$(mktemp -d)"
python -m ocdeck broker --mock
```

Keep that terminal open, and use the same temporary OCDECK_HOME from a second terminal for status/stop. Do not reuse your production config for an isolated test. Mock capacity can be 6, 15 or 32. The ordinary GIF preview always draws six sample agent keys.

## Regenerate media

Run from the source checkout. These scripts write generated assets; review the resulting diffs and images before committing.

```bash
python scripts/readme_hero.py
python scripts/render-gallery.py
python scripts/preview_jelly.py --benchmark
python scripts/preview_jelly_life.py
python scripts/preview_jelly_v3.py
python scripts/preview_jelly_update.py
python scripts/preview_coffee.py
python scripts/preview_world.py
python scripts/preview_world_art.py
python scripts/preview_world_interactions.py
```

The v3 showcase generator also requires ffmpeg with H.264 encoding support. Some preview helpers save a QA still under /tmp and assume that directory exists; they were authored on Linux. The hero and galleries are renderer demonstrations. Keep the original YouTube hardware link in the README and media index; regenerating a GIF is not a replacement for that walkthrough. Preserve valid media filenames so incoming links continue working.

## Add or change an integration

For native hooks, start with profiles.mjs and install.mjs, then direct_hooks.py for broker-side state. The old per-launch relay uses its own HookFacts path, so check both when changing normalization. For OpenCode-style complete snapshots, use Bridge/Facts and the documented API identity/sequence contract.

Document native config location, exact event names, stable request-ID availability and missing-event behavior. Preserve unrelated user hooks and ownership receipts. Add meaningful fixtures for state changes, concurrency/reconnect, unknown counts and removal as appropriate. Update the integration guide, matrix, source map and CLI/config references if their contracts change.

## Documentation maintenance

Give every new feature a clear user benefit, setup steps, defaults, limitations, example and source link. Link it from the main README, docs hub and related guides. Use descriptive headings and link labels; substantive explanations make the material discoverable without repeated keyword lists or duplicate pages. Keep release history in historical records rather than mixing old installation instructions into current guides.

The [documentation checker](../../scripts/check-docs.py) validates local Markdown/HTML destinations and headings, media decoding, and reference coverage for commands/settings. The [audit record](DOCUMENTATION-AUDIT.md) records the reviewed base and verification limits. Recalculate SHA256SUMS.txt after final changes, excluding the manifest itself.

## Build and release

```bash
python -m build
```

Verify an installed wheel from outside the source checkout, especially bundled JavaScript and PowerShell assets. The automatic main release workflow builds/publishes after a main push; a documentation-only main commit can trigger it. See the current release guide before merging.

## Related guides

[Contributing](../../CONTRIBUTING.md) · [Source map](SOURCE-MAP.md) · [Architecture](../ARCHITECTURE.md) · [API](../API.md) · [Releases](../PYPI.md)
