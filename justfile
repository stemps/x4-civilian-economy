set windows-shell := ["powershell", "-NoProfile", "-Command"]

default:
    @just --list

# Controller tests, XML parsing and x4validate (uses the configured Python).
validate:
    uv run --offline --with lxml --with rich --with click python tools/check.py

# Full native schemas, including the merged AI patch.
schema:
    uv run --offline --with lxml --with rich --with click python tools/check.py --schema

lua:
    uv run --offline --with lupa python tools/test_debug_menu.py
    uv run --offline --with lupa python tools/test_population_bridge.py

check: validate lua
