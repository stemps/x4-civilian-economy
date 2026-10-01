set windows-shell := ["powershell", "-NoProfile", "-Command"]
python := env_var_or_default("CE_PYTHON", "")

default:
    @just --list

# Read-only production plan reproducibility, snap geometry and construction contracts.
plans-check: plans-verify plans-tests construction-tests

# Artifact verification only; validate already discovers the focused plan tests.
plans-verify:
    if ('{{python}}') { & '{{python}}' tools/generate_plans.py; exit $LASTEXITCODE } else { uv run --offline --with lxml python tools/generate_plans.py; exit $LASTEXITCODE }

# Focused geometry, native-stage and recovery contracts against generated artifacts.
plans-tests:
    if ('{{python}}') { & '{{python}}' -m unittest discover -s tests -p 'test_spine*.py'; exit $LASTEXITCODE } else { uv run --offline --with lxml python -m unittest discover -s tests -p 'test_spine*.py'; exit $LASTEXITCODE }

# Focused production staging and profile checks.
construction-tests:
    if ('{{python}}') { & '{{python}}' -m unittest discover -s tests -p '*construction*.py'; exit $LASTEXITCODE } else { uv run --offline --with lxml python -m unittest discover -s tests -p '*construction*.py'; exit $LASTEXITCODE }

# Explicitly regenerate only the isolated production plan artifacts.
plans-generate:
    if ('{{python}}') { & '{{python}}' tools/generate_plans.py --write; exit $LASTEXITCODE } else { uv run --offline --with lxml python tools/generate_plans.py --write; exit $LASTEXITCODE }

# Controller tests, XML parsing and x4validate (uses the configured Python).
validate *args:
    if ('{{python}}') { & '{{python}}' tools/check.py {{args}}; exit $LASTEXITCODE } else { uv run --offline --with lxml --with rich --with click python tools/check.py {{args}}; exit $LASTEXITCODE }

# Full native schemas, including the merged AI patch.
schema *args:
    if ('{{python}}') { & '{{python}}' tools/check.py --schema {{args}}; exit $LASTEXITCODE } else { uv run --offline --with lxml --with rich --with click python tools/check.py --schema {{args}}; exit $LASTEXITCODE }

# Full static/native schema validation without repeating controller tests.
schema-only *args:
    if ('{{python}}') { & '{{python}}' tools/check.py --schema --skip-tests {{args}}; exit $LASTEXITCODE } else { uv run --offline --with lxml --with rich --with click python tools/check.py --schema --skip-tests {{args}}; exit $LASTEXITCODE }

lua:
    if ('{{python}}') { & '{{python}}' tools/test_initial_construction.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_initial_construction.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' tools/test_debug_menu.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_debug_menu.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' tools/test_population_bridge.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_population_bridge.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' tools/test_workforce_bridge.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_workforce_bridge.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' tools/test_map_status.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_map_status.py; exit $LASTEXITCODE }

# Everyday gate: all controller tests, generated plans, static checks and UI.
check: translations plans-verify validate lua

# Preserve the release gate's integration coverage.
check-release: check test-release

# Comprehensive gate; controller tests execute once, schemas in a fresh process.
check-full: check-release schema-only

# Focused test-tooling contracts, independent of game execution.
test-tooling:
    if ('{{python}}') { & '{{python}}' -m unittest discover -s tests -p 'test_tooling*.py'; exit $LASTEXITCODE } else { uv run --offline --with lxml python -m unittest discover -s tests -p 'test_tooling*.py'; exit $LASTEXITCODE }

# Require every English entry in all game locales, including format contracts.
translations:
    if ('{{python}}') { & '{{python}}' test/test_translations.py; exit $LASTEXITCODE } else { uv run python test/test_translations.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' test/check_translations.py; exit $LASTEXITCODE } else { uv run python test/check_translations.py; exit $LASTEXITCODE }

# Validate, record, push, package and publish a release from clean main.
release:
    if ('{{python}}') { & '{{python}}' scripts/release.py; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python scripts/release.py; exit $LASTEXITCODE }

# Package the current working tree, including uncommitted runtime files.
build-zip:
    if ('{{python}}') { & '{{python}}' scripts/release.py build-zip; exit $LASTEXITCODE } else { uv run python scripts/release.py build-zip; exit $LASTEXITCODE }

# Encode the raider skull source as a mipmapped game texture.
raider-logo:
    if ('{{python}}') { & '{{python}}' tools/build_raider_logo.py; exit $LASTEXITCODE } else { uv run --with pillow python tools/build_raider_logo.py; exit $LASTEXITCODE }

# Render and fully decode the approved runtime broadcast videos.
news-videos:
    if ('{{python}}') { & '{{python}}' tools/build_news_videos.py; exit $LASTEXITCODE } else { uv run --with imageio-ffmpeg python tools/build_news_videos.py; exit $LASTEXITCODE }

# Publish or resume an existing tagged release on Nexus Mods.
publish-nexus tag *args:
    if ('{{python}}') { & '{{python}}' scripts/release.py publish-nexus "{{tag}}" {{args}}; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python scripts/release.py publish-nexus "{{tag}}" {{args}}; exit $LASTEXITCODE }

# Render and open the manual at a release tag, branch or commit without publishing anything.
nexus-description ref:
    if ('{{python}}') { & '{{python}}' scripts/manual_bbcode.py "{{ref}}"; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python scripts/manual_bbcode.py "{{ref}}"; exit $LASTEXITCODE }

# Exercise releases using temporary repositories and local remotes only.
test-release:
    if ('{{python}}') { & '{{python}}' test/test_release.py; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python test/test_release.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' test/test_manual_bbcode.py; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python test/test_manual_bbcode.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' test/test_nexus.py; exit $LASTEXITCODE } else { uv run python test/test_nexus.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' test/test_archive.py; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python test/test_archive.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' test/test_release_support.py; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python test/test_release_support.py; exit $LASTEXITCODE }

# Junction this dev directory into the game's extensions folder for in-game testing.
link:
    & ./scripts/game_link.ps1 link

# Remove the extensions junction; never deletes a regular folder or the dev files.
unlink:
    & ./scripts/game_link.ps1 unlink

# Show whether the extensions folder holds a junction, a copied folder or nothing.
link-status:
    & ./scripts/game_link.ps1 status

# Exercise the optional installed VTL source without redistributing it.
vtl moddir:
    uv run --offline --with lxml --with lupa python tools/test_transaction_log.py "{{moddir}}"
