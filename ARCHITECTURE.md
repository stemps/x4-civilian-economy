# Runtime architecture

## Layers and ownership

| Module | Responsibility and lifetime |
| --- | --- |
| `md/ce_ownerless_hub.xml` | Persistent sector registry, native construction, ten-level construction lifecycle and captured native delivery listeners. |
| `md/ce_reserves.xml` | Synchronous reserve migration, consumption, replenishment targets and cumulative supplied-time growth. No persistent cue namespace. |
| `md/ce_population_profiles.xml` | Synchronous population-profile configuration and resolution from live race workforce resources; no persistent cue state. |
| `ui/ce_population.lua` | Native accessible-population reader; no economic state. |
| `ui/ce_debug_tools.lua` | Optional UI Extensions testing menu and scoped ownerless interaction fallback. |
| `ui/ce_hub_status.lua` | Read-only cached hub snapshots, metric formatting and explanatory text for the map. |
| `ui/ce_map_status.lua` | Civilian-only map selection table, five-ware pagination and native reserve/growth bars. |
| `libraries/`, `assets/`, `index/` | Cumulative construction plans and hub definition using vanilla modules/artwork. |
| `aiscripts/build.buildstorage.xml` | Excludes registered hubs from vanilla builder recruitment; MD assigns their builders. |
| `t/` | Localized names and diagnostics. |
| `tests/`, `tools/` | MD action tests, Lua mocks, plan generation and schema/toolkit validation. |

## State and events

`Init.$Registry` is keyed by sector. Each record owns its hub, completed level,
pending expansion, population, rates, reserve balances, cumulative growth seconds, trade
guards and testing settings. Construction sites count as hubs immediately.
Five-minute reconciliation requests population through blackboard arrays and
Lua events. Request tokens reject duplicate/stale replies; failed reads preserve
existing state. Minute ticks process each registry entry.

Creating or replacing a hub requires at least 100,000,000 accessible population.
Existing hubs below this threshold are retained, with demand still proportional
to their actual population.

Each hub's instantiated delivery watcher has its own namespace and captured
record reference, preventing later loop iterations from redirecting deliveries.
Live demand records own `$Active` membership and `$DisplayOrder`. Diagnostics
read those records through the captured hub context, independently of definitions.
Destruction affects only the matching record. Existing leveling saves retain
their registry; energy-only prototype saves remain blocked.

Demand scales by accessible population / 8,524,100,000. Population changes accrue
at the previous rate before updating rates, retaining reserves and growth. Zero
population pauses an existing hub without deleting it. UI snapshots and commands
are selected by exact hub identity.

## Local demand profiles

`CE_PopulationProfiles.Build` is included synchronously by reconciliation/save-load
`RefreshProfile`. It returns candidate data without modifying the saved record. It enumerates `lookup.race.list` and `lookup.ware.list`, using
`race.workforce.resources.list` for local sustain. Pharmaceutical resources unlock
at level 3; other sustain resources at level 1. Common water and energy unlock at
levels 1 and 2. Industrial goods unlock at levels 4–7 and luxuries at level 9;
Terran profiles use microlattice, silicon carbide, computronic substrate and
stimulants. Distinct foreign staples unlock at level 8, excluding water and
medicine. First definition wins: local staples cannot be downgraded or duplicated
by common/imported demand. Each native staple gets the existing 2,000 units/hour
baseline; each foreign staple gets 500. Multiple staples are additive requirements.

The initial sector owner's primary race is a population proxy, not a measurement
of planetary ethnicity. `$ProfileRace` is retained across conquest and hub loss.
An unknown owner receives common demand without invented local food; explicit
sector overrides can resolve this. This is a single-culture profile, not a weighted
racial demographic simulation. Existing saves capture their current owner on migration.

Conversion adapters patch `md/ce_population_profiles.xml` through the usual nested
extension path and append `set_value` actions to library `Configure`:

- `$ProfileStaples.{'$raceid'}`: replacement list of staple ware-ID strings.
- `$ProfileMedicines.{'$raceid'}`: replacement list of medicine ware-ID strings.
- `$ProfileRaceDemands.{'$raceid'}`: replacement list of `[ware-ID, unlock-level,
  baseline-units/hour]` for common/industrial/luxury demand.
- `$ProfileSectorRaces.{'$sector_macro_id'}`: race-ID string for a sector.
- `$ProfileCommon`: default common/industrial/luxury rows for other races.

An absent override inherits the native/default list; an explicit empty list disables
that category. To extend a native basket automatically, change its native workforce
resources. To extend a CE override, include all desired IDs in its replacement
list. No hardcoded race enumeration or DLC dependencies are needed. Unknown ware
IDs and non-container cargo are skipped; adapters should verify their IDs. Wares
use native localized names, so profiles introduce no new translation keys.
For example, an adapter can append:

```xml
<set_value name="$ProfileStaples.{'$customrace'}" exact="['customgrain','customrations']"/>
<set_value name="$ProfileMedicines.{'$customrace'}" exact="['custommedicine']"/>
<set_value name="$ProfileSectorRaces.{'$custom_sector_macro'}" exact="'customrace'"/>
```

Save loads rebuild definitions and compare ware/unlock/rate membership independent
of ordering. Changed profiles and ordinary reloads retain reserves and growth. Retired ware records keep reserves, paid/delivered totals and unloading
references, but have zero rates/caps, no new reservations and no growth/UI
requirement. Existing unloading finishes through the original watcher. Leveling
and population scaling still run through `ApplyLevel`. Resolver tests mock native
lookups, including conversion-only wares and races; live engine validation remains
necessary, especially save migration with reserved trades.

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
The panel uses label/value summary rows and native reserve bars behind remaining-time labels and one cumulative growth bar, following vanilla storage-bar cell placement.
Population is formatted in millions, billions or trillions. Ware tooltips show reserve units, hourly rate, target, buying and incoming units. Map hover on a known registered hub shows just level and
compact population on two lines. The override is cleared before native update
and on cleanup, preserving special-mode tooltips. Native station popovers are
untouched. Registration is idempotent, with the same
load/population-request retry convention as testing UI.

`ce_hub_status.lua` caches player blackboard membership/snapshots for one real
second; object validity and player knowledge are checked at use. Snapshot version 3
is required by all UI consumers; incompatible versions show details unavailable.
The shared validator rejects incomplete/duplicate rows. Malformed version-3 input
can retain a copied last-valid snapshot with an explicit stale warning.

Header positions: 1 hub, 2 completed level, 3 pending target, 4 operational,
5 growth seconds, 6 required seconds, 7 paused offers, 8 plot ready, 9 ware rows,
10 testing bypass, 11 population, 12 pause reason, 13 schema version (3),
14 profile-refresh error, 15 stale, 16 next-level localized unlock names.
Ware rows: 1 name, 2 reserves, 3 replenishment target, 4 native advertised buying,
5 native reservations, 6 lifetime deliveries, 7 lifetime payment credits,
8 remaining simulation seconds, 9 hourly rate, 10 stable ware ID.

Initial ordering is empty, low (<900 seconds), then supplied, by remaining time.
Stable IDs freeze ordering while selected; new requirements append and removed
requirements disappear. Pagination retains five wares. Level, target, membership,
availability and warning-state changes trigger a native frame rebuild without
resorting. Status-bar colors cannot be function-valued in native Helper; set
colors on rebuild and update numeric fill/text with function-valued properties.
The shared adapter loads before the testing and map consumers.

Population, debug-menu and map integration have mocked Lua tests under `tools/`,
run by `just lua`. Native rendering and UI Extensions interaction still require
in-game acceptance.

## Validation boundary

Automated tests mock native actions. Native construction, object marshalling
through blackboards, unloading and save/load still need disposable-save tests.
The MD controller covers several subsystems; a future refactor should separate
reconciliation, construction and demand libraries while preserving saved cue
namespaces and record references.

String keys in MD profile tables require a literal `$` prefix. Raw ware/race IDs
remain unprefixed values; dynamic lookups use `{'$' + id}`. The profile test
runner preserves string sigils and rejects unprefixed profile-table writes.

## Refresh failure boundaries

Profile preparation writes only caller-local candidate definitions, race, status
and rate arrays. Completion flags are reset before each build/rate-preparation
call, so interrupted execution cannot reuse previous scratch output. Native
lookup writes are checked, definitions/rates are validated, and the saved profile
is replaced only after both stages complete. Missing discovery is an error;
explicitly empty resolved configuration is valid. Optional unavailable wares can
still be skipped when a useful profile resolves.

`RefreshProfile` compares validated definitions with the saved set. A changed
profile accrues old consumption before committing prepared rates; both paths
preserve reserves and growth. `ApplyLevel` uses committed definitions without rebuilding
profiles. `CommitRates` keeps ware/offer/deal identities and lifetime counters,
updates active membership/order and rebases the simulation clock.
Failures retain existing state, log only transitions/stage changes, and retry on
five-minute reconciliation. New hubs without a valid profile wait without offers.

`EnsureDisplayMetadata` migrates saved records without resetting progress or rates.
`PublishDiagnostics` reads live active records, validates row completeness and
retains the previous snapshot on failure without relabeling old data as version 3.
Removed hubs evict cached snapshots. Rendering never creates supplies.

`tests/test_refresh_safety.py` exercises failures and isolated delivery scopes,
including X4-style continued execution after invalid profile-key writes. These
checks and full XML schemas complement, but cannot replace, native save/load and
concurrent-trade acceptance tests.

## Reserve accounting and migration

`CE_Reserves` libraries run synchronously in the existing controller/listener
namespace with explicit `$R`. Saved cue identities remain unchanged. Legacy
`ResetHistory`, `AccrueAll` and `EvaluateQualification` library entry points are
thin delegates, not rolling-history implementations.

`ReserveVersion=1` migrates each leveling record once: clear old buckets, initialize
reserves/growth to zero, set last accrual to simulation age, preserve native offers,
trade references, accounts, levels, pending builds and lifetime counters. New ware
records explicitly start empty. Existing reserve saves keep `$Last` across reload;
wall-clock offline time never enters calculations.

For each active positive-rate ware, target = ceil(2 * hourly rate). `$Cap` remains
an internal target alias and `$Demand=max(0,target-reserve)` a derived shortfall.
Offers use floor(shortfall) minus native reservations, retaining unloading guards.
Diagnostics report actual native availability/reservations during deferred writes.
Reservations do not supply civilians. Delivery callbacks accrue elapsed consumption
before adding actually transferred units; surplus is never discarded.

While operational, drain each reserve independently to zero. Growth adds the lesser
of elapsed time and the earliest pre-drain reserve exhaustion across all required
wares, only with at least one requirement and no pending expansion at levels 1-9.
It caps at (level+1)*3600 supplied seconds. Shortages, damage and zero population
pause growth without subtracting it. Readiness changes are detected on minute ticks.
Expansion consumes the completed-level basket; completion keeps reserves, starts
new wares empty and resets growth. Destruction loses reserves, preserves growth and
earned level, and discards the pending expansion before reconstruction.

Native restart/save-load, unloading, construction and rendering remain runtime
acceptance gates; the action interpreter and Lua mocks do not emulate X4.

## Two-pane selection layout

The civilian map panel retains one native selection table (eight columns) with a
shared title and a gutter. The left pane contains population, a level/status label over the growth bar,
and next-level unlocks. Timing and guidance are in the level tooltip; errors and
test overrides remain visible. The right pane contains four ware columns and pagination. Native cargo `cellBGColor` styling uses
`rowgroup_background_default` for data and `row_title_background` for headings.
One-pixel anchors place reserve/growth bars behind explicitly full-width transparent
icon/text cells. Reserve bars use native start/current segments: delivered stock
is blue and reserved incoming stock is green (clamped to the target); remaining
time excludes reservations. Background spans bridge column gutters. Buying uses
native ConvertIntegerString(value, true, 2, true), matching cargo quantity formatting.
Local opaque dark fills have zero glow, preserving white-text contrast without
modifying global game colors. Warning text retains
native red/yellow colors. Changes are presentation-only; snapshots and economics
are unchanged.

The ware pane now has three visual columns: Civilian good, Status, Buying.
The first column spans an anchor plus separate left/right text cells, allowing
ware name and remaining time to share one continuous delivered/incoming bar
without text overlap. Both text areas have explicit icon widths; the bar width
includes both cells and their native inter-cell border. The separate internal
cells are layout details, not separate player-visible column headings.

Ware name/time are plain text cells, matching status and buying alignment.
Only the growth label retains a transparent icon over its bar. A wrapped left-pane
summary can enlarge a shared row; using one text widget type across the ware row
keeps its labels on the same baseline. The reserve bar remains behind both name
and time using the preceding anchor column.


## Current layout: one table, summary above wares

`MapMenu.viewCreated` binds widget IDs positionally and expects exactly one table
from `createSelectedShips`. Adding extra tables shifts `menu.topLevel`/`menu.map`
and passes a table ID to render-target functions. Multiple tables are valid in
other native contexts only when their viewCreated callbacks bind them accordingly.

CE therefore adds exactly one five-column table (tabOrder 21). The shared title,
population, level/progress, unlock summary and optional warnings occupy complete
rows above the ware heading. Ware rows cannot inherit the summary's wrapped height.
The three visual ware columns still use a bar anchor plus name/time text cells.
Do not add tables here without updating and testing the native callback contract.
The Lua mock asserts the one-table invariant; native lifecycle remains a runtime gate.
