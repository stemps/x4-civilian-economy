# Runtime architecture

## Layers and ownership

| Module | Responsibility and lifetime |
| --- | --- |
| `md/ce_ownerless_hub.xml` | Persistent sector registry, native construction, ten-level progression and per-ware delivery accounting. |
| `ui/ce_population.lua` | Native accessible-population reader; no economic state. |
| `ui/ce_debug_tools.lua` | Optional UI Extensions testing menu and scoped ownerless interaction fallback. |
| `ui/ce_hub_status.lua` | Read-only cached hub snapshots, metric formatting and explanatory text for the map. |
| `ui/ce_map_status.lua` | Civilian-only map selection table, five-ware pagination and native percentage bars. |
| `libraries/`, `assets/`, `index/` | Cumulative construction plans and hub definition using vanilla modules/artwork. |
| `aiscripts/build.buildstorage.xml` | Excludes registered hubs from vanilla builder recruitment; MD assigns their builders. |
| `t/` | Localized names and diagnostics. |
| `tests/`, `tools/` | MD action tests, Lua mocks, plan generation and schema/toolkit validation. |

## State and events

`Init.$Registry` is keyed by sector. Each record owns its hub, completed level,
pending expansion, population, rates, backlogs, qualification history, trade
guards and testing settings. Construction sites count as hubs immediately.
Five-minute reconciliation requests population through blackboard arrays and
Lua events. Request tokens reject duplicate/stale replies; failed reads preserve
existing state. Minute ticks process each registry entry.

Each hub's instantiated delivery watcher has its own namespace and captured
record reference, preventing later loop iterations from redirecting deliveries.
Destruction affects only the matching record. Existing leveling saves retain
their registry; energy-only prototype saves remain blocked.

Demand scales by accessible population / 8,524,100,000. Population changes accrue
at the previous rate before updating rates and resetting qualification. Zero
population pauses an existing hub without deleting it. UI snapshots and commands
are selected by exact hub identity.

## UI and population bridge

`ui.xml` loads the Lua modules after vanilla detail monitor helpers,
independently of UI Extensions.

`ce_population.lua` handles `CEPopulationRequest`, reads
`$ce_population_request = [token, sectors]`, calls native `GetSectorPopulation`
(the map's Accessible population source), and writes
`$ce_population_response = [token, [[sector, population], ...]]` before sending
`CEPopulation/ready`. Invalid reads are omitted; real zeroes are included.
MD owns discovery, retries and persistent economic state.

`ce_debug_tools.lua` optionally registers a UI Extensions action section. It
locates the clicked hub in `$ce_hubs`, selects its `$ce_hub_statuses` snapshot,
and sends target-specific commands. Registration retries on population requests
if UI Extensions loads later. Its scoped `prepareActions` fallback keeps the
menu open only for a registered hub with prepared custom entries.

The map adapter wraps `MapMenu.createSelectedShips`, `onUpdate` and `cleanup`,
preserving the previous functions. A single known registered hub gets one
bottom-positioned table in the native selection-table slot, including during
construction. Other selections and special map modes retain the previous UI.
The panel uses label/value summary rows and native status bars behind numeric
fulfillment/reliability labels, following vanilla storage-bar cell placement.
Population is formatted in millions, billions or trillions. Each cell's tooltip
covers only that field. Map hover on a known registered hub shows just level and
compact population on two lines. The override is cleared before native update
and on cleanup, preserving special-mode tooltips. Native station popovers are
untouched. Registration is idempotent, with the same
load/population-request retry convention as testing UI.

`ce_hub_status.lua` caches player blackboard membership/snapshots for one real
second; object validity and player knowledge are checked at use. Array positions
match the existing MD snapshot: history minutes 5/6, ware rows 9, population 11;
ware demand/cap 2/3, fulfillment/reliability 8/9, shortage/rate 10/11. No new
economy calculation is introduced. Snapshot field 12 appends the MD-derived
pause reason, recomputed by `UpdateHub`; older snapshots retain the generic
paused label. Missing/wrecked hubs and changed ownership are reported first;
for an owned-by-ownerless hub, wrecked required modules take precedence over
construction, then zero population, then other unavailable required modules.
Only completed-level modules participate, so pending expansions stay active.
Dynamic cells reread
cached values; selection, snapshot availability, ware membership and pagination
drive structural refreshes through native `refreshMainFrame`. Missing history
uses printable `N/A` over an empty bar, never synthetic zero percentages.

Population, debug-menu and map integration have mocked Lua tests under `tools/`,
run by `just lua`. Native rendering and UI Extensions interaction still require
in-game acceptance.

## Validation boundary

Automated tests mock native actions. Native construction, object marshalling
through blackboards, unloading and save/load still need disposable-save tests.
The MD controller covers several subsystems; a future refactor should separate
reconciliation, construction and demand libraries while preserving saved cue
namespaces and record references.
