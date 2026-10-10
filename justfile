# Requires just and uv on PATH. Commands run from this file's directory.
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

toolkit := env('X4_TOOLKIT', '../..')
reference := env('X4_REFERENCE', toolkit + '/reference')

# List available tasks.
default:
    @just --list

# ---------------------------------------------------------------------------
# Mod checks
# ---------------------------------------------------------------------------

# Everyday gate: translations, generated plans, controller tests, x4validate, Lua UI and the sample.
check: translations plans-verify validate lua sample-validate

# Comprehensive gate; controller tests execute once, schemas in a fresh process.
check-full: check-release schema-only

# Controller tests, XML parsing and x4validate on src/.
validate *args:
    uv run --with lxml --with rich --with click python tools/check.py {{args}}

# Full native schemas, including the merged AI patch.
schema *args:
    uv run --with lxml --with rich --with click python tools/check.py --schema {{args}}

# Full static/native schema validation without repeating controller tests.
schema-only *args:
    uv run --with lxml --with rich --with click python tools/check.py --schema --skip-tests {{args}}

# Lua UI harnesses with a fake engine.
lua:
    uv run --with lupa python tests/lua/test_initial_construction.py
    uv run --with lupa python tests/lua/test_debug_menu.py
    uv run --with lupa python tests/lua/test_population_bridge.py
    uv run --with lupa python tests/lua/test_workforce_bridge.py
    uv run --with lupa python tests/lua/test_map_status.py

# Exercise the optional installed VTL source without redistributing it.
vtl moddir:
    uv run --with lxml --with lupa python tests/lua/test_transaction_log.py "{{moddir}}"

# Focused test-tooling contracts, independent of game execution.
test-tooling:
    uv run --with lxml python -m unittest discover -s tests/mod -p 'test_tooling*.py'

# Read-only production plan reproducibility, snap geometry and construction contracts.
plans-check: plans-verify plans-tests construction-tests

# Artifact verification only; validate already discovers the focused plan tests.
plans-verify:
    uv run --with lxml python tools/generate_plans.py

# Focused geometry, native-stage and recovery contracts against generated artifacts.
plans-tests:
    uv run --with lxml python -m unittest discover -s tests/mod -p 'test_spine*.py'

# Focused production staging and profile checks.
construction-tests:
    uv run --with lxml python -m unittest discover -s tests/mod -p '*construction*.py'

# ---------------------------------------------------------------------------
# Mod assets
# ---------------------------------------------------------------------------

# Explicitly regenerate only the isolated production plan artifacts.
plans-generate:
    uv run --with lxml python tools/generate_plans.py --write

# Encode the raider skull source as a mipmapped game texture.
raider-logo:
    uv run --with pillow python tools/build_raider_logo.py

# Render and fully decode the approved runtime broadcast videos.
news-videos:
    uv run --with imageio-ffmpeg python tools/build_news_videos.py

# ---------------------------------------------------------------------------
# Samples (development only, never shipped)
# ---------------------------------------------------------------------------

# Junction the external hub API sample (samples/client-mod) into the game's extensions folder.
sample-link:
    {{x4mod}} link --source samples/client-mod --name ce_sample_client

# Remove the sample's extensions junction; never deletes a regular folder or the dev files.
sample-unlink:
    {{x4mod}} unlink --source samples/client-mod --name ce_sample_client

# Show whether the sample's extensions folder holds a junction, a copied folder or nothing.
sample-link-status:
    {{x4mod}} link-status --source samples/client-mod --name ce_sample_client

# Toolkit x4validate on the sample (god.xml selectors, plan and macro references).
sample-validate *args:
    uv run --project "{{toolkit}}/tools/x4validate" x4validate samples/client-mod --reference "{{reference}}" {{args}}

# ---------------------------------------------------------------------------
# Shared tasks from x4-modkit. Keep this block identical to `x4mod justfile`;
# `x4mod doctor` (part of test-release) fails when it drifts.
# ---------------------------------------------------------------------------

x4mod := env('X4MOD', 'x4mod')

# Every translation matches the English source src/t/0001.xml: coverage, escapes and formatting.
translations:
    {{x4mod}} translations

# Release gate: the mod checks plus the release tooling tests.
check-release: check test-release

# Release tooling tests, including live checks of this repository's manifests, manual and configs.
test-release:
    {{x4mod}} doctor
    {{x4mod}} test

# Validate, record, push, package and publish a release from clean main.
release:
    {{x4mod}} release

# Package src/ from the working tree, including uncommitted files.
build-zip:
    {{x4mod}} build-zip

# Stage src/ as a Workshop folder (ws_ manifest, packed catalog) in dist/workshop/local.
build-workshop:
    {{x4mod}} build-workshop

# Minimal folder for the one-time WorkshopTool publish that creates the Workshop item.
workshop-placeholder:
    {{x4mod}} workshop-placeholder

# Publish or resume an existing tagged release on Nexus Mods.
publish-nexus tag *args:
    {{x4mod}} publish-nexus "{{tag}}" {{args}}

# Publish or resume a tagged release on the Steam Workshop (WorkshopTool; Steam must be running).
publish-steam tag *args:
    {{x4mod}} publish-steam "{{tag}}" {{args}}

# Announce a published release in the Discord channel named in discord.json.
publish-discord tag *args:
    {{x4mod}} publish-discord "{{tag}}" {{args}}

# Render and open the manual at a release tag, branch or commit without publishing anything.
nexus-description ref:
    {{x4mod}} description "{{ref}}"

# Render and open the manual as Steam BBCode at a release tag, branch or commit without publishing anything.
steam-description ref:
    {{x4mod}} description "{{ref}}" --target steam

# Junction src/ into the game's extensions folder for in-game testing.
link:
    {{x4mod}} link

# Remove the extensions junction; never deletes a regular folder or the dev files.
unlink:
    {{x4mod}} unlink

# Show whether the extensions folder holds a junction, a copied folder or nothing.
link-status:
    {{x4mod}} link-status

# Follow the game's debug log; press Ctrl+C to stop.
log:
    {{x4mod}} log
