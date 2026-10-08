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

# Require every English entry in all game locales, including format contracts.
translations:
    uv run python tests/translations/test_translations.py
    uv run python tests/translations/check_translations.py

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
    & ./scripts/game_link.ps1 link -Source samples/client-mod -Name ce_sample_client

# Remove the sample's extensions junction; never deletes a regular folder or the dev files.
sample-unlink:
    & ./scripts/game_link.ps1 unlink -Source samples/client-mod -Name ce_sample_client

# Show whether the sample's extensions folder holds a junction, a copied folder or nothing.
sample-link-status:
    & ./scripts/game_link.ps1 status -Source samples/client-mod -Name ce_sample_client

# Toolkit x4validate on the sample (god.xml selectors, plan and macro references).
sample-validate *args:
    uv run --project "{{toolkit}}/tools/x4validate" x4validate samples/client-mod --reference "{{reference}}" {{args}}

# ---------------------------------------------------------------------------
# Shared tasks: keep this block identical in every mod repository.
# ---------------------------------------------------------------------------

# Release gate: the mod checks plus the release tooling tests.
check-release: check test-release

# Exercise releases using temporary repositories and local remotes only.
test-release:
    uv run --with markdown-it-py==4.0.0 python tests/release/test_release.py
    uv run --with markdown-it-py==4.0.0 python tests/release/test_manual_bbcode.py
    uv run python tests/release/test_nexus.py
    uv run --with markdown-it-py==4.0.0 python tests/release/test_archive.py
    uv run --with markdown-it-py==4.0.0 python tests/release/test_release_support.py
    uv run python tests/release/test_workshop.py
    uv run python tests/release/test_discord.py

# Validate, record, push, package and publish a release from clean main.
release:
    uv run --with markdown-it-py==4.0.0 python scripts/release.py

# Package src/ from the working tree, including uncommitted files.
build-zip:
    uv run python scripts/release.py build-zip

# Stage src/ as a Workshop folder (ws_ manifest, packed catalog) in dist/workshop/local.
build-workshop:
    uv run python scripts/release.py build-workshop

# Minimal folder for the one-time WorkshopTool publish that creates the Workshop item.
workshop-placeholder:
    uv run python scripts/release.py workshop-placeholder

# Publish or resume an existing tagged release on Nexus Mods.
publish-nexus tag *args:
    uv run --with markdown-it-py==4.0.0 python scripts/release.py publish-nexus "{{tag}}" {{args}}

# Publish or resume a tagged release on the Steam Workshop (WorkshopTool; Steam must be running).
publish-steam tag *args:
    uv run --with markdown-it-py==4.0.0 python scripts/release.py publish-steam "{{tag}}" {{args}}

# Announce a published release in the Discord channel named in discord.json.
publish-discord tag *args:
    uv run python scripts/release.py publish-discord "{{tag}}" {{args}}

# Render and open the manual at a release tag, branch or commit without publishing anything.
nexus-description ref:
    uv run --with markdown-it-py==4.0.0 python scripts/manual_bbcode.py "{{ref}}"

# Render and open the manual as Steam BBCode at a release tag, branch or commit without publishing anything.
steam-description ref:
    uv run --with markdown-it-py==4.0.0 python scripts/manual_bbcode.py "{{ref}}" --target steam

# Junction src/ into the game's extensions folder for in-game testing.
link:
    & ./scripts/game_link.ps1 link

# Remove the extensions junction; never deletes a regular folder or the dev files.
unlink:
    & ./scripts/game_link.ps1 unlink

# Show whether the extensions folder holds a junction, a copied folder or nothing.
link-status:
    & ./scripts/game_link.ps1 status

# Follow the game's debug log; press Ctrl+C to stop.
log:
    & ./scripts/game_log.ps1
