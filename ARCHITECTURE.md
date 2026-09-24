# Runtime architecture

## Layers and ownership

| Module | Responsibility and lifetime |
| --- | --- |
| `md/ce_ownerless_hub.xml` | Persistent sector registry, reconciliation, lifecycle orchestration and captured native delivery listeners; stable forwarding entry points for extracted libraries. |
| `md/ce_demand.xml` | Frozen-profile initialization, validated rate preparation and identity-preserving rate commits. |
| `md/ce_trade.xml` | Delivery accounting, sector-owner sales tax, guarded native offers, pricing, account funding and manager setup. |
| `md/ce_diagnostics.xml` | Validated per-hub snapshots and blackboard publication. |
| `md/ce_reserves.xml` | Synchronous reserve consumption, replenishment targets and cumulative supplied-time growth. No persistent cue namespace. |
| `md/ce_population_profiles.xml` | Synchronous startup population-profile resolution from loaded race workforce resources. |
| `md/ce_placement.xml` | Current-plot-first layout retries, bounded safe enlargement and empty-shell relocation; internal cue state and retry diagnostics. |
| `md/ce_construction.xml` | Racial component selection, asynchronous native layout generation, validation, queue recovery and module readiness. |
| `ui/ce_population.lua` | Native accessible-population reader; no economic state. |
| `ui/ce_debug_tools.lua` | Optional testing menu, target-level shortcuts, guarded native force-completion and scoped ownerless interaction fallback. |
| `md/ce_debug_advance.xml` | Validated debug target requests, saved per-hub completion permissions and native-build completion dispatch. |
| `ui/ce_hub_status.lua` | Read-only cached hub snapshots, metric formatting and explanatory text for the map. |
| `ui/ce_map_status.lua` | Civilian-only map selection table, height-limited native scrolling and native reserve/growth bars. |
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
After consuming the completion guard, delivery accounting pays the player an
additional 15% of actual delivered quantity times deal unit price if the hub's
sector is currently player-owned. The seller's identity does not affect tax;
native seller payments and civilian spending totals exclude this extra payout.
Build-storage purchases are separate from civilian hub offers.
Positive native tax transfers emit a localized message-ticker notification and
a General logbook entry linked to the hub, using the amount actually transferred.
Live demand records own `$Active` membership and `$DisplayOrder`. Diagnostics
read those records through the captured hub context, independently of definitions.
Destruction affects only the matching record. Install into a save from before the mod
was installed (or a new game). There is no old-save detection or migration.
Subsequent saves made with this implementation retain their state normally.

Demand scales by accessible population / 8,524,100,000. Population changes accrue
at the previous rate before updating rates, retaining reserves and growth. Zero
population pauses an existing hub without deleting it. UI snapshots and commands
are selected by exact hub identity.

## Local demand profiles

`CE_PopulationProfiles.Build` is included synchronously by startup `CaptureSectorProfile`. Its explicit `$ProfileRace` input is a native race or null, also used by construction discovery. `$DiscoveredRace` is loop scratch. It returns candidate data without replacing `$R` or modifying the saved record. It enumerates `lookup.race.list` and `lookup.ware.list`, using
`race.workforce.resources.list` for local sustain. Pharmaceutical resources unlock
at level 3; other sustain resources at level 1. Common water and energy unlock at
levels 1 and 2. Industrial goods unlock at levels 4–7 and luxuries at level 9;
Terran profiles use microlattice, silicon carbide, computronic substrate and
stimulants. Distinct foreign staples unlock at level 8, excluding water and
medicine. First definition wins: local staples cannot be downgraded or duplicated
by common/imported demand. Default rows carry an optional fourth field, `'budget'`,
with their third field interpreted as average-market-value credits/hour. `Add`
validates the row and available ware before `NormalizeBudget` calculates
`max(10, 10 * floor(budget / average-price-in-credits / 10 + 0.5))`.
Average money prices are cast to `LF` before dividing by `(1Cr)LF`; division by
`1Cr` alone does not guarantee a numeric result in the engine.
Budgets per ware are 150,000 for local food, energy and medicine; 75,000 for
water and foreign food; 250,000 for industrial goods; 100,000 for luxuries.
Native water uses its water budget even when discovered as local sustain.
Multiple staples remain additive requirements. Unavailable/non-container wares
are skipped before price lookup; nonpositive/missing prices invalidate the
candidate. Deduplicated rows never reprice a previously accepted requirement.

`Init.$SectorProfiles` captures every discovered sector before requesting population,
including sectors below the hub threshold. `Init.$RaceProfiles` caches one immutable
demand/component snapshot per race. The sector owner's primary race is a population
proxy, not a measurement of ethnicity. Conquest, reload, replacement and later
eligibility reuse that snapshot. Newly introduced sectors capture on first discovery.
Unknown owners cannot construct a hub without valid components. No sector overrides
or migration of earlier construction schemas are supported.

Conversion adapters patch `md/ce_population_profiles.xml` through the usual nested
extension path and append `set_value` actions to library `Configure`:

- `$ProfileStaples.{'$raceid'}`: replacement list of staple ware-ID strings.
- `$ProfileMedicines.{'$raceid'}`: replacement list of medicine ware-ID strings.
- `$ProfileRaceDemands.{'$raceid'}`: replacement list of `[ware-ID, unlock-level,
  baseline-units/hour]` for common/industrial/luxury demand. Three-field rows
  remain literal quantity overrides and do not read average prices. Optional
  `[ware-ID, unlock-level, credits/hour, 'budget']` rows opt into normalization.
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
```

Save loads reuse saved definitions. `RefreshProfile` initializes a hub record from
its sector snapshot only if definitions are absent. `ApplyLevel` changes rates and
unlocks against that saved basket; population changes scale rates without rebuilding
preferences. Adapters must be installed before the mod first initializes.
Resolved/saved definitions use three-field rows; reload does not reprice the basket.

## Racial construction

`CE_Construction.Resolve` queries native `get_module_definition` categories for the
captured race, without filtering by the ownerless hub faction. It chooses the
smallest positive container storage, S/M dock (by combined docking capacity), and
capital pier (`numpierdocks`). Ties use native enumeration order; saved choices never
reroll. All racial connection modules become the allowed connector pool.

Adapters can append to `CE_Construction.Configure` a race-keyed table such as:

```xml
<set_value name="$ConstructionOverrides.{'$customrace'}"
  exact="table[$Dock=macro.custom_dock_macro,$Storage=macro.custom_storage_macro,$Pier=macro.custom_pier_macro,$Connectors=[macro.custom_connector_macro]]"/>
```

Each field is optional and replaces that role. Modules must support the required
class/capacity. Defaults follow loaded module definitions, including conversion
replacements. No fallback to Argon components is allowed.

A new hub is an empty station shell. Its first layout uses its existing plot;
build storage is created only after layout acceptance. There is no up-front
reservation for level ten. `CE_Placement` applies a five-minute cooldown after a
failed attempt; the next five-minute reconciliation performs the retry (so the
actual delay can be nearly ten minutes).
Only a native generation failure permits safe incremental plot enlargement (up to
2 km per side per attempt, capped at 16 km half-size on each axis). The center is
preserved and existing larger plots never shrink. Invalid module baskets and build
task failures retry without enlargement.

If enlargement is unsafe, capped or has no effect, placement can retry up to three
times using native safe-position warping of the same empty station. Relocation
requires no native modules, storage, accepted/completed sequence, build task,
initialization, pending callback or operational state. Established hubs stay put,
retain their earned level and continue operating while expansion retries. After
limits are reached, layout attempts continue through reconciliation in the current
plot; no overlap is forced and no free module is supplied.

The dormant `CE_Placement.State` cue owns a lazily initialized table keyed by hub
identity (attempts, failures, next allowed time, enlargement flag and placement
attempt count). This is internal saved cue state; public hub records, adapter
contracts and snapshot version remain unchanged. Hub loss removes its entry.
Reload cancellation retains the retry delay and counters. `PlotReady` means the
current plot is available for a layout attempt or accepted construction, rather
than a guaranteed level-ten envelope; it does not gate expansion qualification.
Logs identify the hub, sector ID/name, level/token/attempt, failure reason, next
retry time, bounds and each plot/placement outcome. Native save/load and relocation
behavior still require in-game acceptance.

`Generate` has an instantiated namespace holding the record, station, token, level,
and completed base sequence. `create_construction_sequence` runs asynchronously
without `immediate`, with a ten-second timeout and `failsafe=false`. Completion
checks identity/token, exact functional module multiplicities, allowed connectors,
and preservation of every base entry ID/macro before queuing normal construction.
Level 1 requires dock/storage/pier; every later level adds storage, 4/7/10 add docks,
and 6/10 add piers. Generated connector counts are deliberately unconstrained.

Saved `CompletedSequence` and `TargetSequence` define readiness by native plan entry
IDs, including connectors. Expansion retains completed-level demand. On reload an
unfinished generation watcher is cancelled and its request retried; queued builds
retain their sequence. A lost build task is requeued from the saved target sequence.
Hub destruction clears sequences but retains the sector preferences and earned level.
Native construction-plan entries are property-path intermediates, not values that
can be stored in MD variables. Validation and readiness read `.macro`, `.id` and
`.exists` through the sequence, retaining only the resulting native values.

`StartBuild` is shared by accepted layouts and recovered build tasks. It binds the
hub and sector from the captured record, processes the build, initializes/funds
build storage, then applies the existing builder policy immediately. An unavailable
builder is retried by five-minute reconciliation. Failed generation clears pending
state without queueing a build; identity/token guards discard stale completions.
Startup diagnostics name the hub and the layout/build/funding/builder stage.
Invalid components/layouts log a diagnostic and block without substitution.
The packaged static Argon plans and generator remain reference fixtures; racial
runtime construction does not select them.

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

`ce_hub_status.lua` owns membership normalization and the shared positional-to-named
snapshot decoder. Map `get` caches player blackboard membership/snapshots for one real
second; object validity and player knowledge are checked at use. Snapshot version 3
is required by all UI consumers; incompatible versions show details unavailable.
The shared validator rejects incomplete/duplicate rows. Testing UI uses `getFresh`
for display and action eligibility, and `isHub` for construction completion. These
read current blackboards without consuming or updating the display cache; map-only
knowledge filtering and retained stale snapshots are not command authority. Malformed version-3 input
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

`wareCode` classifies validated ware rows by policy (paused, needed, low,
supplied, full); a shared descriptor maps the code to text, sort rank and color.
Rebuild signatures use these codes rather than translated labels. `classify`
provides shared hub facts for state, progress, action and level-label formatting.
Each formatter preserves its existing message precedence; these facts do not
decide economic state or authorize commands.

Population, debug-menu and map integration have mocked Lua tests under `tools/`,
run by `just lua`. Native rendering and UI Extensions interaction still require
in-game acceptance.

## Validation boundary

Automated tests mock native actions. Native construction, object marshalling
through blackboards, unloading and save/load still need disposable-save tests.
The controller retains persistent cue namespaces and captured record references.
Demand, trade and diagnostics implementations are synchronous libraries behind
the existing controller entry points. Their calls use explicit cross-script refs;
no new persistent cue namespace or saved state is introduced.

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

`RefreshProfile` commits validated saved-snapshot definitions only to records without
an existing basket. `ApplyLevel` uses committed definitions without rediscovery.
`CommitRates` retains ware/offer/deal identities and lifetime counters. Failed startup
snapshots remain invalid rather than changing preferences later; correct the adapter
and start a fresh game. Failed rate preparation preserves the last committed state.

`CommitRates` creates display order and active membership with each rate commit;
there is no metadata backfill for older saves.
`PublishDiagnostics` reads live active records, validates row completeness and
retains the previous snapshot on failure without relabeling old data as version 3.
Removed hubs evict cached snapshots. Rendering never creates supplies.

`tests/test_refresh_safety.py` exercises failures and isolated delivery scopes,
including X4-style continued execution after invalid profile-key writes. These
checks and full XML schemas complement, but cannot replace, native save/load and
concurrent-trade acceptance tests.

## Reserve accounting

`CE_Reserves` libraries run synchronously in the controller/listener namespace
with explicit `$R`. `RebaseAccrual`, `AccrueAll` and `EvaluateQualification` delegate
to reserve rebasing, accrual and qualification respectively. `ResetHistory` remains
a compatibility alias for rebasing; neither name clears earned growth.

`ReconcileSector` initializes growth to zero and last accrual to the current
simulation age when creating each record. `CommitRates` initializes new wares
with empty reserves. `SyncAll` only refreshes derived targets and shortfalls;
it never converts or initializes saved data. Normal saves keep `$Last` across
reload; wall-clock offline time never enters calculations.

`CE_Reserves.SyncWare` is the sole target/shortfall calculator. Prepared rate rows
contain `[ware, rate, price]`; commit rebases and synchronizes after applying them.
Accrual/rebasing, profile/rate application, offers and diagnostics keep their
synchronization boundaries. `ForgetHub` delegates its initial synchronization to
`AccrueAll` directly; `UpdateHub` first checks module readiness (no reserve reads),
then synchronizes via accrual or rebasing on both branches before funding. These
two controller-level duplicate calls are omitted; delivery-before-credit ordering
and old-rate accrual before population changes are unchanged.
For each active positive-rate ware, target = ceil(2 * hourly rate). `$Cap` remains
an internal target alias and `$Demand=max(0,target-reserve)` a derived shortfall.
Offers use floor(shortfall) minus native reservations, retaining unloading guards.
Diagnostics report actual native availability/reservations during deferred writes.
Each `UpdateOffers` call prunes expired transfers and builds a temporary ware-keyed
`UnloadingWares` set in the same pass. Offer updates use that set for their unloading
guard; multiple live deals for one ware remain guarded until all finish. The set
is rebuilt per call and is not part of a saved hub record or an incremental cache.
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
The summary and ware-heading rows (1-6) are fixed; all ware rows scroll.
`maxVisibleHeight` caps the single table at 40% of the screen height and
`getVisibleHeight()` determines its bottom-aligned position. Short lists use only
the height they need. `reserveScrollBar=true` leaves room in the variable-width
last column. There are no page controls or five-ware limit.

Before native updates rebuild the frame, CE records `GetTopRow` for the same hub
and restores it through `setTopRow`, clamped when the basket shrinks. Switching
hubs, native selection modes or cleanup resets the position. The Lua fixture
checks header/ware row modes, large and empty lists, viewport bounds at several
screen heights, scroll restoration and the one-table contract.

The renderer separates selection/order retention, panel geometry and row access,
summary widgets and ware headings/rows into local helpers. They all populate the
single table created by `createPanel`; no helper adds another table.
Live callback closures still resolve the current snapshot by hub and ware identity.

Reserve bars use native start/current segments: delivered stock is blue and
reserved incoming stock is green, clamped to the target. Remaining time excludes
reservations. Plain text ware cells share a baseline; the growth label uses a
transparent icon. Native cargo backgrounds and explicit anchor widths preserve
the combined ware-name/time column. Buying uses native `ConvertIntegerString`.

## Test support and configured paths

`tests/support.py` owns fixture data, reference resolution and the reusable
profile fixture. Test suites do not import helpers from other test suites.
`tools/check.py --reference` passes its resolved path through `CE_REFERENCE` to
all fixtures; `X4_REFERENCE` and `X4_TOOLKIT` set defaults for isolated worktrees.
`tools/md_test_runtime.py` dispatches fully qualified library calls by the shipped
MD script name. Controller forwarding calls preserve existing test interception.

## Debug advance to a chosen level

The interaction testing section offers levels 2-10; only targets above an active
hub's current level are enabled, with no pending expansion. Lua rechecks fresh
state on click. MD resolves a bounded command list, checks native readiness,
identity, ownerless ownership and absence of a pending plan/task, then queues the
chosen cumulative target through CE_Construction. Existing base entry IDs and
normal layout validation/retries remain in effect; Level is never assigned early.

CE_DebugAdvance.State stores requested targets keyed by hub, outside the public
record/snapshot. StartBuild and minute ticks emit CEAdvanceBuildReady only for an
explicit debug request with a native task. Lua revalidates identity, snapshot test
flag and native progress, calls ForceBuildCompletion and requests an UpdateHub.
Normal readiness then commits the target, demand and name. If generation/completion
is delayed, the request survives save/load and retries. Requests end when the level
is reached, ownership changes or the target changes; hub loss removes them. Ordinary
queue-upgrade actions never acquire automatic-completion permission. The automatic
callback requires the Lua addon; a missed UI event is retried on a minute tick.
