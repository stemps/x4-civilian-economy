# Runtime architecture

## Production connector-spine construction

Normal hubs now use the six approved racial connector-spine layouts. The debug
experiment menus, worker, probes, review gates and legacy cleanup tombstone have
been removed. Existing pre-integration hubs require the normal full hub reset;
there is no old-plan migration or fallback random construction path.

Native evidence for the geometry: six-race smoke and physical construction,
600 bulk sites / 6,000 placement checks, and user approval of all six finished
level-10 stations. Docks/piers were visually accessible. Actual docking remains
untested by user choice. The production controller integration requires a fresh
in-game reset/upgrade check after a full restart.

## Hub ownership and reconstruction

Hubs and their managers belong to `faction.civilian`. The controller is
`CE_CivilianHub` in `md/ce_civilian_hub.xml`. Construction-plan IDs use the
production ce_hub_<race> catalogue. Older mod saves are unsupported; start with
a save that has never loaded the mod. There are no ownership or old-state
migrations. Saves made with the current implementation retain normal continuity.

`ReconcileSector` gates creation, including replacement and debug creation, on the
sector owner's enemy relation toward civilians. Unowned and non-hostile sectors
qualify; nearby enemies do not affect eligibility. Existing hubs keep operating
after hostile conquest. Destruction retains earned progress under the existing
loss policy; reconstruction resumes when the sector qualifies again. Funding
continues to use the ownerless faction account. Unrest fleets still switch to
`ce_unrest`, explicitly neutral toward both civilians and ownerless objects.

These MD changes require a full restart and save load. Continuity of active
construction needs in-game verification.

## Localization

`t/0001-l044.xml` is the canonical English source for page 974201. The other
15 `0001-lNNN.xml` files carry the same page/text IDs for all locales shipped
in the game reference, matching Supply Chain View's coverage. This includes
Bulgarian, Turkish and Ukrainian even where the game's language selector does
not enable them. Entries cover UI labels, tooltips, MD messages and debug actions.

`test/check_translations.py` mirrors SCV's translation coverage gate, adapted
to CE's existing English filename instead of adding a second English source.
It checks every page, required locale files, missing/extra/duplicate/empty entries,
language IDs and X4 text escapes. CE additionally checks ordered Lua format
specifiers, numbered MD arguments, text references and literal newline counts.
`test/test_translations.py` exercises failure fixtures and the shipped files.
`just translations` runs both; `just check` runs it before the other checks.
These checks validate coverage and formatting, not linguistic quality or UI fit.
Translation files require a full game restart; `/reloadui` is insufficient.

## Sector demand events

`CE_DemandEvents` owns eleven stable event IDs, applicable ware baskets, selection
and lifecycle. `CE_EventNotifications` owns start/end tickers and General logbook
entries. `CE_DebugEvents` accepts token-guarded hub requests from the Events group
in the existing debug interaction menu. Event mechanics never change faction laws,
police behaviour or native production.

Each registry record lazily gains version-2 `DemandEvents`, containing an `Active`
table keyed by event ID, sector identity and a command token. Each active entry
holds its ID, signed percentage, expiry, frozen affected ware list and ware names.
Initialization creates the current collection only; obsolete single-event state
is unsupported.

Candidates use active positive-rate wares and racial categories. Water, medicine
and energy are excluded from staples; festivals use imported foods and drugs.
Industrial events use refined metals, silicon wafers, advanced composites,
metallic microlattice and silicon carbide. Tech Boom uses microchips, advanced
electronics and computronic substrate. Locked goods stay out, and new level
unlocks do not join an already active event's frozen basket. Start rejects any
ware intersection with another event, including partial overlaps and duplicates.

The minute controller rolls independently for each unoccupied applicable group:
staples, water, medicine, energy, technology, industrial materials, exotic
foods/drugs. With K applicable groups, including occupied ones, a group's chance
is `1 / (120 * (K - 1) + 1)` per game minute; it then chooses uniformly among that
group's compatible events. The renewal calculation includes 120 active minute
intervals and geometric idle failures, targeting one active event per sector.
There are no initial delays, post-event cooldowns or missed-roll catch-up. K=1
runs consecutive events; K=0 starts none. Natural starts require an operational
civilian-faction hub. Positive effects roll +25-100%; reductions roll -25-50%,
once per event. Debug interventions and changing eligibility are outside the
long-run average. Timers continue while the hub is unavailable.

`CE_Demand.PrepareRates` combines the applicable event with baseline definition,
level, population and settings scaling. `CE_Reserves.Accrue` finds successive
expiry deadlines, accrues reserves and unrest to each boundary, removes all
simultaneous expiries, and recomputes rates once per batch. It restores `Last`
after rate commit rebases the clock, then consumes the remaining interval.
Non-operational rebases cannot move accrual backward. Offers, deals and inventory
retain their identities. End notifications identify only the restored goods;
other events may still be active. Tickers can wait for the next minute tick.

Snapshot v3 optional slot 21 is `[2, eventRows, eligibleIDs, commandToken]`, with
rows `[eventID, signedPercent, remainingSeconds, wareNames]` ordered by ID. The
UI accepts only this collection format for display and debug commands.
Stale snapshots retain event display
and cannot authorize commands. With active events, the map fixes only its five
hub summary rows; events, ware heading and wares scroll in the same table. With
no events the ware heading remains the sixth fixed row. Changing the event list
returns the viewport to its first scrollable row.

Debug commands use `CEEventTesting`, `start:ID:token` or `end:ID:token` and hub
identity; `end:0:token` ends all events. Triggers add compatible events and never
replace an existing one. MD rechecks debug mode, snapshot health, ownership,
identity and ware conflicts. End actions work even when the hub is temporarily
non-operational, and create no cooldown. Separate notifications use the removed
event's preserved entry while all remaining modifiers continue.

Regression coverage executes shipped MD actions and Lua menu/panel code, plus a
seeded renewal simulation using the shipped group denominator and event duration.
Native rendering, ticker timing and save serialization still require in-game
acceptance. Installing these MD/text changes requires a full game restart.

## Release tooling

The release workflow mirrors Supply Chain View. `just release` requires clean
`main` tracking and matching `origin/main`. It suggests the next minor version
(with an editable override), opens commit subjects in Git's configured editor,
updates `VERSION`, `CHANGELOG.md` and the manifest version/date, runs `just check`,
commits only that metadata, creates an annotated tag and atomically pushes both.
Before the first tag, CE derives the suggestion from the existing manifest
(version 300 suggests 0.4.0); later releases derive it from the latest tag.
`VERSION` and `CHANGELOG.md` are created by the first release, not pre-seeded.

- `scripts/release.py`: preflight, version/notes, metadata, validation and Git
  orchestration; preserves concurrent edits and rolls back pre-commit failures.
- `scripts/release_archive.py`: deterministic ZIPs under `civilian_economy/`,
  local working-tree builds and reconstruction from verified remote tags.
  Runtime selection includes the two manifests, UI Lua and XML in `md`, `t`,
  `aiscripts`, `assets`, `index`, `libraries` and nested `extensions` patches.
  Promotional images, docs, tools and tests are excluded.
- `scripts/nexus_publish.py`: Nexus upload/version/changelog publication with
  resumable receipts in ignored `dist/nexus/`. `nexus.json` targets mod 2405;
  `X4_NEXUS_KEY` supplies credentials. With `file_id: null`, exactly one main
  file must exist. For an empty page, set `create_new_file: true`; the successful
  file binding is retained locally for subsequent releases.
- `scripts/manual_bbcode.py`: converts the released `docs/MANUAL.md` to
  `dist/nexus/<tag>/description.bbcode.txt` and opens Notepad for copy/paste.
  Unsupported Markdown fails before releasing or publishing. The source manual
  is never modified, and description editing on Nexus remains manual.
  Continued numbered lists use explicit numbers because Nexus BBCode has no
  list-start attribute; this preserves CE's dependency-section numbering.
- `test/`: isolated release repositories/local remotes and fake HTTP responses;
  run via `just test-release`, also included in `just check`. This directory is
  separate from the MD controller tests in `tests/`.

`just build-zip` packages dirty and untracked runtime files without changing Git
or versions. `just publish-nexus vX.Y.Z` resumes an existing release;
`just nexus-description vX.Y.Z` regenerates only its manual handoff. Release
tasks use `uv` with pinned `markdown-it-py==4.0.0`, or the existing `CE_PYTHON`
override (which must have the dependencies installed). Retain `dist/nexus`
receipts to resume uncertain uploads safely.

## Civil unrest

`CE_Unrest` owns per-record shortage contributions, eligibility/grace deadlines,
stage hysteresis and the continuous critical timer. `CE_Reserves.Accrue` calls it
before consuming reserves, so shortage starts at depletion within the elapsed
game-time interval. Supplied time first recovers existing points; recovery cannot
prepay future deprivation. Frozen racial profiles include ware categories; older
saves classify existing definitions lazily. The minute controller schedules hubs
in rotating order.

`CE_Sabotage` selects a player station before choosing an applicable effect. Its
saved station table holds cooldowns and pending destruction; its pause table owns
temporary production pauses. `ui/ce_unrest.lua` wraps the native station overview
pause control and relinquishes CE ownership when the player intervenes. Hacks
use the native returned affected-component list; cargo uses actual dropped
amounts. Destruction waits for a missing/wrecked module before committing its
popup and destructive cooldown. No last-module or last-dock exclusion exists.

`CE_Raids` owns saved group IDs, composition, berth preflight and docked creation.
New ships explicitly receive Black Steel (`paintmod_0017`) at creation. Existing
ships are not repainted. `libraries/factions.xml` assigns the CE skull icon to
the unrest faction for menus and hull decals; `libraries/icons.xml` resolves its
extension-qualified texture. The faction uses the vanilla active/inactive-only
icon declaration, without a separate image override. The user confirmed this
corrected the solid-square hull decal in game. `images/ce_unrest_skull.png` is the source artwork,
inspired by the pirate broadcast still. `just raider-logo` encodes it as a 256px
RGBA DDS with nine mip levels, gzip-wrapped in `assets/textures/ui/factions/`.
The release archive explicitly includes that texture. A full game restart is
required; Black Steel contrast remains an in-game acceptance check.
Up to five groups may be active per hub, including departing and withdrawing
ones; there are no global or capital-group caps. Ordinary launch cooldowns remain
one hour (four hours for capital launches); explicit debug launches bypass them.
Capital commanders are L destroyers with five verified cargo drones; other tiers
use their first M. All remaining ships use native `assignment.attack`.
Capital equipment generation excludes the `units` flag so optional combat/repair
drones cannot consume the shared drone bay before the five cargo drones are added.
Failed partial launches never activate pirate ownership or fleet orders; their
neutral, ungrouped, weapons-held departure is withdrawal cleanup, not a raid.

`CE_RaidBehaviour` controls version-2 groups through saved `departing`, `raiding`
and `withdrawing` phases. It holds weapons and issues individual MoveWait orders
to a safe sector rally point beyond the hub. Every surviving member must undock
and finish its rally order before the commander receives native Plunder. The
10-minute departure deadline produces safe withdrawal on failure. Pending launches
reserve cooldowns; failed departures restore them only if no newer reservation
replaced them. A single news broadcast commits when departure is accepted;
the 45-minute lifetime starts only when piracy begins. Separate saved `Announced`
and `CombatStarted` guards prevent repeat warnings/lifetime resets on regrouping.
Groups start in `launching` phase; successful preparation changes the phase to
`departing`. Failed partial launches remain in `launching` and use the dedicated
`CleanupFailedLaunch` library, preserving boarding, capture and safe-despawn
checks. Prepared groups use the current raid behavior; no historical group
versions or announcement flags are migrated.

CE AI hooks require true ownership plus versioned pilot blackboard markers.
`move.seekenemies` preserves the cargo-carrying player-flown ship exception and
3:1 player ownership weighting; `order.plunder` allows all container goods while
retaining native demands, responses, collection and refusal attacks. It suppresses
cover and offload trips. `interrupt.restock` blocks autonomous resupply; full
holds or loss of the capital commander's cargo drones cause withdrawal.
`move.generic` rejects remote destinations before native gate travel and signals
the MD controller to replan locally, with a five-second return delay and a
30-second controller retry limit. No `move.gate` abort remains.

Raids use native combat and retaliation, including against stations. Plunder mode
0 selects ship robbery, but CE no longer filters weapon targets or disengages
when stations attack. Five AI patches retain cargo/target selection, no disguise
or resupply/offload trips, sector validation and departure/withdrawal guards.
Added blocking waits carry sinceversion markers with script versions 24
(move.generic), 28 (Attack) and 7 (Plunder), preserving native resume positions
in pre-CE saves. Route rejection can still request a local regroup.
Transition/stall logs record group, commander, ship order, dock and
drones; demand logs identify the selected target. Capture releases CE markers;
boarding suspends reordering/disposal. Clearing unrest requests withdrawal for
all groups from that hub, including debug groups. Ship components cannot store
script variables, so all AI identity/control markers live on pilots.

`CE_UnrestNotifications` owns penalty tickers, interactive target-monitor alerts,
General logbook entries and map fallback. Saved penalty state suppresses repeat
tickers; committed incidents own their alert, including delayed destruction.
Raids and successful sabotage call `Broadcast` with an explicit cutscene key and
short localized caption. `ce_news_raid`, `ce_news_sabotage` and `ce_news_hacking` play 12-second still
clips in the native target monitor, with a warning sound and map interaction.
The broadcast interaction stops its own cutscene before opening the affected
object or surviving sector; critical-unrest text alerts keep their original event.
Full incident details appear in the left message ticker for 12 seconds at submission
and are written once to the General logbook. Sabotage names its attack type and
affected equipment/module; destruction captures names before removal. A null cutscene
result falls back to the original interactive text alert. Native monitor queuing
is retained. The cutscene API exposes no priority parameter.
The hacking surveillance image covers production disruption, turret/shield hacks
and cargo release. The sabotage explosion image is reserved for confirmed module
destruction. Captions and logs describe the actual outcome.

`images/broadcast/` contains the approved art sources. `tools/build_news_videos.py`
encodes H.264/yuv420p clips using imageio-ffmpeg and an installed TrueType font,
fitting the full images above a solid red lower third without cropping. Bold white
headlines scroll left at 110 pixels/sec, prefixed with BREAKING. Strings come from
English text IDs 291-292 and 296. These baked-in video headlines remain English;
localizing them would require separate strip renders and language-based clip selection.
Runtime captions use the localized native text entries. These are packaged videos, not a runtime
image-generation or encoder dependency. Only the three production broadcast MKVs are
included in release archives, along with cutscene XML.
`just news-videos` rebuilds and fully decodes the runtime MKVs.

`CE_Trade` reduces only the additional player-sector reward, leaving recorded
seller payments intact. Routine payment-message settings do not gate unrest
tickers. Snapshot v3 has optional slot 20 containing score, stage, direction,
critical time remaining, causes and a one-use debug token; older snapshots remain
readable but cannot authorize unrest actions.

`CE_DebugUnrest` consumes command-specific tokens after checking debug mode,
hub identity and ownership. Explicit incidents share production handlers and
notifications, bypass timing/score gates and retain applicability and raid caps.
Exact requested effects never fall back. Stage changes use real scoring and
transition handling. Resetting cooldowns preserves pending and active effects.

Validation executes shipped actions with native-effect mocks, Lua UI contracts,
native schemas and merged AI diffs. These checks do not replace in-game wreck,
cargo, docking, combat, boarding and save/load acceptance. MD, faction and AI
changes require a full game restart; `/reloadui` alone is insufficient.

## Layers and ownership

| Module | Responsibility and lifetime |
| --- | --- |
| `md/ce_settings.xml` | Per-save settings, defaults, validation, live economic transitions and shared growth-time calculation. Publishes the debug-menu visibility flag. |
| `md/ce_options.xml` | Civilian Economy page in Mod Support APIs Extension Options; checkbox and stepped-slider callbacks. |
| `md/ce_civilian_hub.xml` | Persistent sector registry, reconciliation, lifecycle orchestration and captured native delivery listeners; stable forwarding entry points for extracted libraries. |
| `md/ce_demand.xml` | Frozen-profile initialization, validated rate preparation and identity-preserving rate commits. |
| `md/ce_trade.xml` | Delivery accounting, sector-owner sales tax, guarded native offers and pricing. Retains payment watcher cues; provisioning belongs to CE_Accounts. |
| `md/ce_accounts.xml` | Synchronous station/build-storage funding and manager provisioning, behind the existing trade/controller entry points. |
| `md/ce_transaction_log.xml` | Synchronous optional payment-label integration: capture requests, tax labels and receipt publication. Owns no persistent cue state. |
| `md/ce_notifications.xml` | Upgrade-start and completion ticker/logbook messages, with saved per-target start deduplication. |
| `md/ce_diagnostics.xml` | Validated per-hub snapshots and blackboard publication. |
| `md/ce_reserves.xml` | Synchronous reserve consumption, replenishment targets and cumulative supplied-time growth. No persistent cue namespace. |
| `md/ce_population_profiles.xml` | Synchronous startup population-profile resolution from loaded race workforce resources. |
| md/ce_placement.xml | Fixed-plot construction retry counters and bounded backoff. |
| md/ce_construction.xml | Production staged-plan admission, readiness, funding/builder handoff and initial completion authorization. |
| `md/ce_construction_data.xml` | Generated exact macro baskets and geometry for six racial plans and ten levels. |
| `md/ce_construction_stages.xml` | Load/reuse native master sequences and validate stage boundaries, macro order and preserved IDs. |
| `ui/ce_initial_construction.lua` | Complete only fresh MD-authorized level-1 seed/reset builds. |
| `md/ce_debug_reset.xml` | Confirmed global CE reset, protected removal and fresh initialization. |
| `ui/ce_population.lua` | Native accessible-population reader; no economic state. |
| `ui/ce_debug_tools.lua` | Optional testing menu with top-level diagnostics and station/construction, ware and unrest subgroups; guarded native force-completion and scoped civilian interaction fallback. |
| `md/ce_debug_wares.xml` | Token-guarded virtual reserve randomization/emptying for active positive-rate wares; settles consumption and refreshes offers and snapshots. |
| `md/ce_debug_advance.xml` | Validated debug target requests, saved per-hub completion permissions, native-build completion dispatch and token-guarded one-hour growth progress increments. |
| `md/ce_debug_create.xml` | Sector-targeted debug creation, fixed population/profile selection, and identity-scoped initial-build completion permission. |
| `ui/ce_hub_status.lua` | Read-only cached hub snapshots, metric formatting and explanatory text for the map. |
| `ui/ce_map_status.lua` | Civilian-only map selection table, height-limited native scrolling and native reserve/growth bars. |
| `libraries/`, `assets/`, `index/` | Cumulative construction plans and hub definition using vanilla modules/artwork. |
| `images/` | Promotional images for posting with the mod; separate from runtime game assets. |
| `aiscripts/build.buildstorage.xml` | Excludes registered hubs from vanilla builder recruitment; MD assigns their builders. Skips duplicate native initialization when a registered CE hub already has a trade NPC. |
| `t/` | Localized names and diagnostics. |
| `tests/`, `tools/` | MD action tests, Lua mocks, plan generation and schema/toolkit validation. |

## State and events

`Init.$Registry` is keyed by sector. Each record owns its hub, completed level,
pending expansion, population, rates, reserve balances, cumulative growth seconds, trade
guards and testing settings. Construction sites count as hubs immediately.
Five-minute reconciliation requests population through blackboard arrays and
Lua events. Request tokens reject duplicate/stale replies; failed reads preserve
existing state. Minute ticks process each registry entry.

Creating or replacing a hub requires at least 100,000,000 effective population
(native accessible population, or the explicit fixed debug override described below).
Existing hubs below this threshold are retained, with demand still proportional
to their actual population.

Each hub's instantiated delivery watcher has its own namespace and captured
record reference, preventing later loop iterations from redirecting deliveries.
After consuming the completion guard, delivery accounting pays the player an
additional configurable percentage (default 15%) of actual delivered quantity times deal unit price if the hub's
sector is currently player-owned. The seller's identity does not affect tax;
native seller payments and civilian spending totals exclude this extra payout.
Build-storage purchases are separate from civilian hub offers.
Tax income uses vanilla's `reward_player` action. The synchronous difference in
`player.money` before/after the reward determines the amount actually credited. Native financial
history classifies this as a generic mission reward (user-verified). Positive
income also emits VTL 1.14's description-only `transfer_money` Lua event with
actual cents and a localized sector label. Verbose Transaction Log optionally
consumes it; without that listener the native label remains. No external cue or
manifest dependency is required, and CE never invokes VTL's additional payment.
Description events are independent of the ticker/logbook toggle. VTL owns tax matching
and persistence; its time/amount matcher can confuse identical simultaneous payments.
Completed paid deliveries from player-owned sellers capture their current order,
ship, sale value and sector name in `CE_Trade.WatchDeliveryPayment`. Its private
namespace survives changes to controller scratch variables. `DeliveryAccountPaid`
queues a receipt request when that ship's account changes from exactly the sale
amount to zero, then cancels the watcher. Trade completion is too early (about one
second before receipt); AI order completion is too late (the latest save still
has the captured TradePerform order waiting for drones after receipt).
The account event also arrives a frame late: slot 4 measured a 17ms gap. Therefore
`ui/ce_transaction_log.lua` reads native player transaction entries and finds a
unique `orderqueue_remove` receipt by seller, exact cents and the captured
completion-to-account-event window. Windows longer than 30 seconds and ambiguous
or missing receipts retain native text. The adapter drains a shared blackboard
request list so simultaneous requests cannot overwrite each other.
Requests retain the MD money type: blackboard serialization converts it to Lua
credits. The native ledger uses cents, so only the Lua comparison multiplies by 100.
With VTL enabled and its v1.14 saved-data structure present, the adapter stores
text 156 against the native entry ID in VTL's lookup table, preserving existing
descriptions. It synchronously dispatches VTL's `mvtl.onGameLoad` event to reload
that private cache. VTL then renders and persists the name normally. This is an
adapter to the installed VTL implementation, not a documented public write API;
future VTL changes may require maintenance. Missing/disabled VTL is a no-op.
No external mod file is edited. Receipt naming is verified in-game.
Each new receipt also stores its ware ID as `ceWare` alongside VTL's description.
The optional UIX callback fills an empty Detail cell with the ware's localized
name; it leaves the native ware ID empty so the receipt does not gain an invalid
expandable trade breakdown. A lazily loaded cache refreshes on VTL boot. Existing
entries without ware metadata keep their current appearance. Detail rendering
still needs an in-game test. Temporary receipt/tax diagnostics have been removed.
Ship destruction or immediate order cancellation cancels the watcher without
guessing a refund/payment timestamp. Missing or infinite orders are not watched;
the latter are outside the tested manual-order payment path.
This label does not require player sector ownership or enabled tax. NPC sales,
free sales and zero deliveries do not emit it; seller payment remains entirely native.
When sales-tax notifications are enabled (the
default), positive credited income emits a localized message-ticker notification
and a General logbook entry linked to the hub.
Upgrade construction is announced after processing a valid build task; a saved
`UpgradeNotifiedTarget` prevents repeats on task recovery/reload and is cleared
on hub loss. Completion is announced only on level commit, after offer refresh.
Messages distinguish newly unlocked goods, quantity-only increases, and paused
offers. Initial construction and module repairs are not level-up events.
Live demand records own `$Active` membership and `$DisplayOrder`. Diagnostics
read those records through the captured hub context, independently of definitions.
Destruction affects only the matching record. Install into a save from before the mod
was installed (or a new game). There is no old-save detection or migration.
Subsequent saves made with this implementation retain their state normally.

Demand scales by accessible population / 8,524,100,000. Population changes accrue
at the previous rate before updating rates, retaining reserves and growth. Zero
population pauses an existing hub without deleting it. UI snapshots and commands
are selected by exact hub identity.

## Player settings

`CE_Settings.State` stores six values per save: Debug=false, NewsVideos=true,
DemandMultiplier=1.0, TimeMultiplier=1.0, TaxNotifications=true and TaxPercent=15.
Ensure fills only absent fields; Read provides defaults even before initialization.
No UI userdata is written and loading another save restores that save's settings.
`CE_Options` registers its three-section page whenever `Simple_Menu_API.Reloaded`
signals. It uses the installed Mod Support APIs manifest ID `ws_2042901274`.
Checkboxes use equal width and height from Helper.standardTextHeight and update
on click. Sliders update on confirmation, with multipliers ranging from 0.1 to
10.0 in 0.1 steps and tax in 1 percentage-point steps. MD validates and rounds
typed values too.

Demand changes first accrue every record at its old rate, then rebuild rates from
frozen definitions with the new multiplier, synchronize targets, and refresh live
offers/snapshots. Definition, reserve and deal identities are retained. Time changes
scale the required supplied seconds, preserving absolute earned growth. The normal
minute tick still owns qualification-triggered construction. These MD calculations
have no player-sector/attention branch; native delivery behavior is unchanged.

Debug visibility is published as `player.entity.$ce_debug_enabled`; Lua checks it
using a converted Lua component ID, not the raw FFI value from C.GetPlayerID(),
when building the right-click menu, invoking a retained action and applying the
empty-placeholder fallback. Hiding the menu does not revoke already-authorized
asynchronous debug construction. It leaves the read-only map panel visible.
TaxNotifications suppresses both the ticker and logbook entry, without changing
payouts. TaxPercent=0 skips the native tax transfer entirely.
NewsVideos controls the shared raid, sabotage and hacking broadcast playback.
Broadcast reads the setting each time; disabling it retains the ticker and one
logbook entry without a replacement popup. Enabled playback still falls back to
the interactive popup if the engine returns no cutscene handle. Critical warnings
are independent. The Display checkbox affects future broadcasts only.
Sections are ordered Debug, Gameplay, Display, with an unselectable 8-pixel
text spacer before Gameplay and Display; native UI scaling applies.

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
Unknown owners cannot construct a normal hub without valid components. Debug
creation can save a separate Argon fallback on its record; it does not rewrite the
sector snapshot. Migration of earlier construction schemas is not supported.

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

tools/spine_catalog.py selects native Argon, Boron, Paranid, Split, Terran and
Teladi modules. Container storage ranks by capacity, S/M docks by combined capacity
while requiring both classes, and piers by capital berths. Distinct minimum/middle/
maximum tiers apply to additions at levels 1-3/4-6/7-10; macro-name ordering resolves
ties. Storage is added every level, docks at 1/4/7/10, and piers at 1/6/10.

tools/spine_geometry.py builds the snap-connected multi-elevation layouts.
tools/spine_bounds.py fits measured native boxes and frozen candidate constraints.
tools/generate_plans.py writes six bookmarked production master plans,
CE_ConstructionData, and the reproducible numeric manifest in tests/fixtures.
just plans-check verifies reproducibility, geometry and runtime contracts;
plans-generate explicitly regenerates artifacts. Only numeric geometry/metadata
is retained; game assets are read from the local reference, never copied.

CE_Construction.Resolve matches every required macro against the captured race's
native module definitions. Unsupported/missing racial layouts block construction.
It stores the plan ID and ten exact cumulative macro lists in the racial profile.
Ordinary sector profiles never silently fall back to another race. The existing
explicit debug-create fallback to Argon remains separate.

Each shell gets a fixed 10 km cubic plot. CE_Construction.Generate is an
identity/token-guarded request handler, not a random geometry generator.
CE_ConstructionStages loads the master once, retains its native finalsequence,
and submits later stages against that same sequence. It validates stage metadata,
active prefix count, exact macro order and preserved entry IDs before processing.
Native stage ranges are zero-based; stage ten is validated by its actual prefix,
since its native unbookmarked-tail range reports count/count.

CE_Construction owns queue admission, task recovery, funding/builder handoff and
readiness. Only active-prefix modules count toward readiness; future master-plan
entries do not. Lost tasks retry the same master and stage. Hub destruction clears
the master/IDs and preserves the earned-level replacement policy. CE_Placement
now owns only per-hub retry counters and five-minute backoff. No random direction
retries, plot growth or relocation fallback remain.

First-generation level-1 seeds, including reset hubs, retain exact-object
InitialHub permission. A validated native build is published in
$ce_initial_build_hubs; ui/ce_initial_construction.lua rechecks that fresh
membership, civilian ownership and native build readiness before force completion.
The shared AssignBuilder routine excludes these initial hubs, including delayed
completion and task recovery, so neither build startup nor reconciliation reserves
a builder for seed/reset construction.
CE_Accounts retains build storage and its manager but funds it only for queued or
active construction outside initial completion. Idle storage retains leftover
credits and cargo without budget top-ups; the hub operating account remains funded.
Readiness revokes permission before any later expansion. Ordinary replacements,
later discoveries and upgrades use funded native builds. Debug-create/advance
shortcuts remain independently authorized. Native force completion does not
validate resource delivery.
While initial builds are authorized, a one-second cue retries completion at most
every two seconds and checks readiness. It becomes inactive when the permission
list is empty, avoiding a five-minute reconciliation delay if the first Lua event
arrives before the native build is ready.

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
Diagnostics remain at the root. `insertInteractionGroup` recreates station,
wares and unrest subgroups during each preparation, plus a subgroup for each
positive-rate ware. Stock commands mutate virtual reserves after accruing elapsed
consumption, then refresh offers and diagnostics without changing delivery/payment
totals. Progress commands add 3600 supplied seconds up to the current requirement.
Both command families consume the snapshot's existing unrest token before mutation.

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

The selected-hub panel requests `CEHubStatus/refresh` immediately on opening or
selection changes and at most once per second thereafter. Cleanup, invalid
selections and special map modes clear the request throttle; hovering alone
does not request updates. `CE_Diagnostics.RefreshSelectedHub` validates the live
registered civilian hub and reset guard, republishes only that hub's diagnostics
and the shared snapshot collection, then raises `CEHubStatusUpdated`. The Lua
decoder invalidates its one-second cache while retaining last-valid fallback
rows. This path does not accrue reserves/growth or update offers; the economic
tick remains once per game minute.

`ce_hub_status.lua` owns membership normalization and the shared positional-to-named
snapshot decoder. Its `progressHint` formatter owns the status-only level tooltip:
supplied time and one status, missing goods on separate lines, and compact
construction/earned-upgrade/maximum-level states. Data warnings replace progress
details. The map adapter supplies the current snapshot without composing messages.
Map `get` caches player blackboard membership/snapshots for one real
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
Optional trailing positions: 17 fixed debug population, 18 Argon fallback flag,
19 initial-build completion permission. Old version-3 snapshots omit these fields.
Stale snapshots always disable initial-build completion permission.
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
to reserve rebasing, accrual and qualification respectively. Rebasing preserves
earned growth; the obsolete `ResetHistory` alias has been removed.

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
The five hub summary rows are fixed. With no events the ware heading is also
fixed; otherwise the event list, ware heading and wares scroll together.
Every scrolling row uses `addRow(true, { interactive=false })`, matching vanilla
informational capacity rows. Native `calculateMinRowHeight` groups a selectable
row with subsequent unselectable rows; making the entire list unselectable forces
the whole list to fit and prevents scrolling. Fixed summary rows remain unselectable.
`maxVisibleHeight` caps the single table at 40% of the screen height, rounded down
to whole pixels. Bottom placement rounds `getVisibleHeight()` up, rounds the
resulting y position down, and leaves two extra pixels for native widget rounding.
Short lists use only
the height they need. `reserveScrollBar=true` leaves room in the variable-width
last column. There are no page controls or five-ware limit.

Before native updates rebuild the frame, CE records `GetTopRow` for the same hub
only when the result is numeric, retaining the previous position if the native
table is unavailable. Drawing defaults a missing position to the first scrollable
row and restores it through `setTopRow`, clamped when the basket shrinks. Switching
hubs, native selection modes or cleanup resets the position. The Lua fixture
checks header/ware row modes, large and empty lists, viewport bounds at several
screen heights, scroll restoration and the one-table contract. It also executes
vanilla's fixed/minimum row-height functions against the mock row measurements
to catch unscrollable groups exceeding the table cap.

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

`just check` is the everyday gate: translations, generated plan verification,
all discovered controller/tooling tests, XML/reference checks and Lua contracts.
`plans-verify` only checks generated artifacts; standalone `plans-check` also
runs the focused geometry and construction tests. The everyday gate relies on
normal discovery for those tests instead of executing them twice.

`just check-release` adds the real local Git release/archive integration suites;
the release tool uses this gate. `just check-full` additionally runs `schema-only`.
`just schema` retains controller tests plus native schemas; `schema-only` passes
`--skip-tests`, explicitly announces the omission, and retains static validation
and merged AI checks. Full checking therefore executes controller tests once.
`just validate --timings` (also supported by schema/schema-only) reports stage,
module and slow-test wall times through `tools/check_timings.py`, including on
failure. Test timings include per-test setup and cleanup, but not class fixtures.

`tools/md_expressions.py` owns process-local 8,192-entry LRU caches for normalized
paths and compiled ordinary expressions. Cache keys are original source strings;
only immutable strings/code are shared. Every evaluation uses the current Runner
environment, with fresh literal values. Special expressions, validation and native
effects stay in `md_test_runtime.py`. XML trees and profile fixtures remain private
to each runner, so tests can modify shipped action trees without stale node caches.

Release fixtures lazily prepare a pristine working repository and bare remote
once per process, then copy both into each test's temporary directory and repoint
origin. Copies use independent files, not hardlinks or object alternates. Tests
still execute real Git operations, including rejection hooks and rollback paths.
`just test-tooling` exercises interpreter/check-runner contracts; Git fixture
isolation is exercised by `just test-release`.

`tests/support.py` owns fixture data, reference resolution and the reusable
profile fixture. `support_construction.py`, `support_startup.py`,
`support_unrest.py` and `support_sales_tax.py` own focused shared fixtures;
test suites do not import helpers or setup methods from other test suites.
Release/archive tests share the disposable local Git fixture in
`test/release_support.py`. Lifecycle tests execute real account/manager
provisioning libraries with native side effects mocked.
`tools/check.py --reference` passes its resolved path through `CE_REFERENCE` to
all fixtures; `X4_REFERENCE` and `X4_TOOLKIT` set defaults for isolated worktrees.
`tools/md_test_runtime.py` dispatches fully qualified library calls by the shipped
MD script name. Controller forwarding calls preserve existing test interception.

Payment watchers remain at `CE_Trade.WatchDeliveryPayment` with the same child
cue names, conditions and captured `$Payment`. Only synchronous action bodies
delegate to `CE_TransactionLog`; receipt cancellation stays in the original
child cue. Account extraction likewise keeps caller namespaces, action order,
funding policy and manager ownership unchanged. These refactorings introduce
no saved-state migration or fixes to the ownership/raid review findings.

## Construction status

Diagnostics append an optional construction phase at snapshot position 22:
planning, layout_retry, build_retry, or an empty string. The Lua adapter
uses it for status/progress text. This field never authorizes force completion.
The staged production path and initial-build authorization are described above.

## Full debug reset

`CE_DebugReset` owns a persistent removal queue and confirmation token. Its Lua
adapter exposes a two-step action on sectors and hubs. MD validates debug mode,
context and token. Reset freezes controller ticks and debug mutations, invalidates
population responses and native layout callbacks, then detaches old records.
Only registered CE-owned hubs/build storage and tracked CE raid ships are removed.
Captured objects survive; docked visitors and the player block destruction.

Cleanup survives save/load and waits for actual object removal. Then the existing
population/reconciliation path creates fresh level-1 records using current sector
profiles. A matching population response completes reset; initial hubs complete
their validated first native stage automatically. Replacements and upgrades build normally. Settings and historical financial/logbook records are preserved.
Removed experiment stations are outside the production registry. Clean up those
specimens with the old build before switching versions, or use a fresh test save.

## Debug advance to a chosen level

The interaction testing section offers levels 2-10; only targets above an active
hub's current level are enabled, with no pending expansion. Lua rechecks fresh
state on click. MD resolves a bounded command list, checks native readiness,
identity, civilian ownership and absence of a pending plan/task, then queues the
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


## Fixed-population debug creation

The optional sector interaction action sends `CESectorTesting / create_hub_5b`
with the sector identity. MD validates the sector and rejects any live registered
hub, including construction sites and captured hubs. `$ce_hub_sectors` publishes
occupied sectors separately from hub snapshots; Lua rechecks it at activation.
The native no-actions fallback is limited to prepared hub/eligible-sector entries.

`CE_DebugCreate.Request` validates the frozen sector profile, or resolves an Argon
fallback through the existing profile/component builders. It saves the selected
profile on the record without modifying shared sector/race caches. A failed
fallback leaves existing records unchanged. `EnsureRecord` is shared with normal
reconciliation. Fresh records start at level 1; retained records keep earned level
and growth. A station-creation failure retains the override for normal retries,
but grants no completion permission until a hub actually exists.

`PopulationOverride` is 5000000000.0f. It takes precedence before reconciliation
eligibility and population updates. Reconcile also processes overridden records
without waiting for the native population bridge. Native population data remains
unchanged. `DebugProfile` and `DebugFallback` survive loss/replacement; ordinary
records have no override and retain the 100M creation threshold.

`DebugInitialHub` is a saved, exact object identity. The accepted construction
callback and minute ticks publish a fresh snapshot before `CEInitialBuildReady`.
The callback explicitly reads the controller registry across the namespace boundary.
Lua checks current membership, snapshot permission, civilian ownership and native
build readiness, then invokes ForceBuildCompletion and sends `initial_complete`.
MD still waits for native module readiness before declaring operation. Completion,
hub loss, identity mismatch or ownership change revokes permission. Automatic
replacements and subsequent upgrades do not inherit it; layout failures/save loads
retain permission for the same requested hub. No force-completion state is shared
with debug target-level advancement.
