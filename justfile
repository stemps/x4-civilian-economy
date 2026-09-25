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

check: validate lua

# Exercise the optional installed VTL source without redistributing it.
vtl moddir:
    uv run --offline --with lxml --with lupa python tools/test_transaction_log.py "{{moddir}}"
