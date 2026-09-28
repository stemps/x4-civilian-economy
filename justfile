set windows-shell := ["powershell", "-NoProfile", "-Command"]
python := env_var_or_default("CE_PYTHON", "")

default:
    @just --list

# Read-only production plan reproducibility, snap geometry and construction contracts.
plans-check:
    if ('{{python}}') { & '{{python}}' tools/generate_plans.py; exit $LASTEXITCODE } else { uv run --offline --with lxml python tools/generate_plans.py; exit $LASTEXITCODE }
    @just plans-tests
    @just construction-tests

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
validate:
    if ('{{python}}') { & '{{python}}' tools/check.py; exit $LASTEXITCODE } else { uv run --offline --with lxml --with rich --with click python tools/check.py; exit $LASTEXITCODE }

# Full native schemas, including the merged AI patch.
schema:
    if ('{{python}}') { & '{{python}}' tools/check.py --schema; exit $LASTEXITCODE } else { uv run --offline --with lxml --with rich --with click python tools/check.py --schema; exit $LASTEXITCODE }

lua:
    if ('{{python}}') { & '{{python}}' tools/test_initial_construction.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_initial_construction.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' tools/test_debug_menu.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_debug_menu.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' tools/test_population_bridge.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_population_bridge.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' tools/test_map_status.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_map_status.py; exit $LASTEXITCODE }

check: translations plans-check validate lua test-release

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

# Regenerate and open a released manual without publishing anything.
nexus-description tag:
    if ('{{python}}') { & '{{python}}' scripts/manual_bbcode.py "{{tag}}"; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python scripts/manual_bbcode.py "{{tag}}"; exit $LASTEXITCODE }

# Exercise releases using temporary repositories and local remotes only.
test-release:
    if ('{{python}}') { & '{{python}}' test/test_release.py; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python test/test_release.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' test/test_manual_bbcode.py; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python test/test_manual_bbcode.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' test/test_nexus.py; exit $LASTEXITCODE } else { uv run python test/test_nexus.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' test/test_archive.py; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python test/test_archive.py; exit $LASTEXITCODE }

# Exercise the optional installed VTL source without redistributing it.
vtl moddir:
    uv run --offline --with lxml --with lupa python tools/test_transaction_log.py "{{moddir}}"
