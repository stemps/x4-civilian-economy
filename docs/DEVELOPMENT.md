# Development of the Mod

See [Runtime architecture](../ARCHITECTURE.md) for module responsibilities, state
lifetimes, compatibility contracts and the native acceptance checklist.

## Dependencies

- [uv](https://docs.astral.sh/uv/) Python package manager
- [Just](https://github.com/casey/just) for running convenience tasks
- [X4 Claude Toolkit](https://github.com/WingedGuardian/x4-claude-toolkit)
  (optional but recommended)
- For Steam Workshop releases: Egosoft's "X Tools" (free, in the Steam library
  under Tools), which provides `WorkshopTool.exe` and `XRCatTool.exe`

## Repository layout

- `src/` is the mod: exactly the files the game loads and every release ships.
- `tests/mod/` holds the MD controller tests, `tests/lua/` the Lua UI harnesses,
  `tests/release/` the release tooling tests and `tests/translations/` the
  translation checks.
- `tools/` holds the check runner, the MD test runtime and the generators for
  files in `src/`; `scripts/` holds release, publishing and the `just link`
  junction. `docs/` and `images/` hold documentation and promotional material.

## Local development setup

The repository assumes that it's located in a `dev` subfolder of a working
checkout of the X4 Claude Toolkit. Make sure to run through the full toolkit
setup first and then check out this repo into a `dev` subfolder.

Without the X4 Claude Toolkit some of the checks won't work due to missing game
files. Set `X4_TOOLKIT` and/or `X4_REFERENCE` to absolute paths for a different
layout.

`just link` creates a junction from the game's `extensions/civilian_economy` to
`src/`, so the game loads your working copy directly. `just unlink` removes only
the junction and `just link-status` shows its target. The extensions folder comes
from `X4_EXTENSIONS`, then the toolkit's `.claude/x4-paths.env`, then
`X4_GAME\extensions`.

## Running checks

Install `just` and `uv`, then run commands from the repository root (or any
subdirectory):

```text
just                 # list tasks
just check           # everyday gate: translations, plans, controller tests, x4validate, Lua
just check-release   # check plus the release tooling tests
just check-full      # check-release plus full native schema validation
just validate        # controller tests, XML parsing and x4validate on src/
just lua             # Lua UI harnesses
just translations    # all game languages contain every English entry
just test-release    # release workflow against temporary local Git remotes
just build-zip       # package the current src/ for local testing
```

The recipes are written for PowerShell (Windows).

## Building a local test ZIP

Run `just build-zip` to create `dist/Civilian-Economy-local.zip`. It contains
every file in `src/` under `civilian_economy/`, including uncommitted edits and
untracked files (unless ignored), from any branch. Nothing outside `src/` is
packaged. Both manifests (`content.xml`, `ui.xml`) are required and runtime
symlinks are rejected. The old local ZIP is replaced only after the new archive
passes integrity/content checks.

This task packages only: run `just check` separately before in-game testing.
It does not update version metadata, create commits or tags, or contact Nexus or
Steam.

## Releasing

`just release` runs from a clean, pushed `main`. It asks for the version and
release notes, runs `just check-release`, commits the version metadata, tags and
pushes, then publishes to Nexus and afterwards to the Steam Workshop.

- Nexus needs `X4_NEXUS_KEY` (your personal API key); `nexus.json` names the mod.
- Steam needs the Steam client running and online; `steam.json` names the
  Workshop item. The Workshop copy gets its own `content.xml` with the
  Workshop id `ws_<item id>`, so Nexus and Workshop saves are not
  interchangeable.
- `XRCATTOOL` must point to `XRCatTool.exe` (or be set in the toolkit's
  `x4-paths.env`) to pack the Workshop catalog.

If a platform fails, the Git release stays. Resume it with
`just publish-nexus vX.Y.Z` or `just publish-steam vX.Y.Z`; both keep receipts
in `dist/` so a resumed upload never runs twice. `just build-workshop` stages the
Workshop folder from the working copy for inspection.

## Nexus description after release

Maintain the main Nexus page description in `docs/MANUAL.md`. `just release`
validates its conversion before changing release metadata. After a successful
Nexus publication, both `just release` and `just publish-nexus <tag>` generate
`dist/nexus/<tag>/description.bbcode.txt` from the released commit's manual and
open it in Windows Notepad. Copy the text into Nexus's description editor and
preview it before saving; the main page description is not published by the API.

The converter uses `markdown-it-py==4.0.0`, supplied automatically by `uv` in the
relevant Just recipes. It supports paragraphs, headings (H1 size 5, H2 size 4,
H3 size 3, H4-H6 size 2), bold, italic, absolute HTTP/HTTPS/mailto links, and
nested bullet or numbered lists starting at 1. Markdown source line wraps become
spaces; explicit line breaks are preserved. Explicit BBCode colour tags pass
through unchanged. Tables, images, code, HTML, blockquotes, horizontal rules,
strikethrough and task lists are rejected with an actionable error.

Generated descriptions are ignored by Git and excluded from mod ZIPs. A failed
Notepad launch does not undo publication or trigger another upload. Reopen or
regenerate the file without publishing anything using:

```text
just nexus-description v0.1.0
```

This requires the requested tag to contain `docs/MANUAL.md` in supported syntax.
On systems without Windows Notepad, the generated file remains available at the
printed path even though opening the editor fails. `just build-zip` does not
convert or open the manual.
