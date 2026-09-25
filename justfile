set windows-shell := ["powershell", "-NoProfile", "-Command"]
python := env_var_or_default("CE_PYTHON", "")

default:
    @just --list

# Controller tests, XML parsing and x4validate (uses the configured Python).
validate:
    if ('{{python}}') { & '{{python}}' tools/check.py; exit $LASTEXITCODE } else { uv run --offline --with lxml --with rich --with click python tools/check.py; exit $LASTEXITCODE }

# Full native schemas, including the merged AI patch.
schema:
    if ('{{python}}') { & '{{python}}' tools/check.py --schema; exit $LASTEXITCODE } else { uv run --offline --with lxml --with rich --with click python tools/check.py --schema; exit $LASTEXITCODE }

lua:
    if ('{{python}}') { & '{{python}}' tools/test_debug_menu.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_debug_menu.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' tools/test_population_bridge.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_population_bridge.py; exit $LASTEXITCODE }
    if ('{{python}}') { & '{{python}}' tools/test_map_status.py; exit $LASTEXITCODE } else { uv run --offline --with lupa python tools/test_map_status.py; exit $LASTEXITCODE }

check: validate lua test-release

# Validate, record, push, package and publish a release from clean main.
release:
    if ('{{python}}') { & '{{python}}' scripts/release.py; exit $LASTEXITCODE } else { uv run --with markdown-it-py==4.0.0 python scripts/release.py; exit $LASTEXITCODE }

# Package the current working tree, including uncommitted runtime files.
build-zip:
    if ('{{python}}') { & '{{python}}' scripts/release.py build-zip; exit $LASTEXITCODE } else { uv run python scripts/release.py build-zip; exit $LASTEXITCODE }

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
