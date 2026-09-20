# Runtime architecture

## Layers and ownership

| Module | Responsibility and lifetime |
| --- | --- |
| `md/ce_ownerless_hub.xml` | Persistent sector registry, native construction, ten-level progression and per-ware delivery accounting. |
| `ui/ce_population.lua` | Native accessible-population reader; no economic state. |
| `ui/ce_debug_tools.lua` | Optional UI Extensions testing menu and scoped ownerless interaction fallback. |
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

`ui.xml` loads both Lua modules after vanilla detail monitor helpers,
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

Both modules have separate mocked Lua tests under `tools/`.

## Validation boundary

Automated tests mock native actions. Native construction, object marshalling
through blackboards, unloading and save/load still need disposable-save tests.
The MD controller covers several subsystems; a future refactor should separate
reconciliation, construction and demand libraries while preserving saved cue
namespaces and record references.
