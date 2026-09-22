# Mod-local Knowledgebase

Code ownership belongs in [ARCHITECTURE.md](ARCHITECTURE.md). Start with the
[README](README.md) for an introduction and the
[developer documentation](docs/DEVELOPMENT.md) for development guidance.

## How this Mod Works

### Demand, payment and progression

- Every sector with at least 100 million accessible population gets one ownerless hub with
  ten economic levels. Base X4 9.00 is required, with no DLC. No custom faction,
  diplomacy changes, production or habitation modules are introduced.
- Population uses Lua `C.GetSectorPopulation`, the vanilla map's Accessible
  population source, queried every five game minutes. Workforce growth/bonus is
  not used. Tokens reject duplicate/stale replies; failed readings are omitted
  rather than treated as zero. The bridge works without UI Extensions.
- Rates scale by population / 8,524,100,000, preserving Argon Prime's diagnostic
  rates. Replenishment targets are ceil(two hours of scaled consumption). Creation and replacement require
  at least 100,000,000 population. Existing hubs below the threshold are retained;
  the threshold does not clamp their demand scaling.
  Local staples now resolve from the saved population race and live workforce resources.
- Registry records are keyed by sector. Each delivery watcher has its own
  namespace and captured record reference. UI/AI membership uses `$ce_hubs`;
  snapshots are selected by hub ID. The singleton marker is only read for adoption.
- Delivery watchers do not inherit Init's local `$Definitions`. A bare lookup in
  `PublishDiagnostics` produced an empty ware snapshot after each delivery until
  the minute tick repaired it; debug.txt confirmed the failed lookup. Reference
  committed live demand records and display order (formerly definitions). Regression coverage executes
  delivery accounting and snapshot publication without local definitions.
- Population changes accrue at the old rate before recomputing completed-level
  rates, preserving reserves and growth. Zero population pauses
  an existing hub; it never creates a new one. Native galaxy rollout and Lua/MD
  object roundtrips still need in-game validation.
- Civilian demand activates only after construction; construction purchases
  never replenish civilian reserves. Each unlocked ware has one public virtual-cargo,
  real-money offer, a two-hour reserve target and price
  `ceil(min + (max - min) / 10)`. `UpdateWarePrice` runs on unlock and normal
  offer refresh, so price changes can reach saved hubs without resetting
  progress through `ApplyLevel`.
- New wares start with empty reserves; existing rates rise 25% only after a completed upgrade. All unlocked
  wares, including intoxicants, count toward qualification; level 10 adds no new
  ware. These quantities and prices are diagnostic balance, not final tuning.
- Advancement from level L requires L+1 cumulative supplied game hours. All
  active positive-rate wares must have reserve stock; no requirements means no
  growth. Shortages pause progress without resetting it. Consumption drains each
  ware independently to zero. Earliest exhaustion determines exact supplied time.
- `CE_Reserves` owns fractional balances, target/shortfall calculations and growth.
  Completed deliveries accrue elapsed consumption before adding actual cargo.
  Late deliveries cannot cover prior shortages; surplus is retained without cap.
  `Buying now` is native advertised availability after subtracting reservations;
  reservations count as supplies only on completed delivery.
- Capture buyer and seller at trade start and bind completion to the exact deal,
  following RML_Trade_Wares. Remove the persisted transfer guard before
  accounting to prevent duplicate credit. The former galaxy-scoped completion
  listener missed deliveries and is retained disabled for compatibility, not
  used for accounting.
- Subtract native reservations from advertised availability and defer offer
  rewrites during unloading. Pausing new reservations still consumes reserves and
  permits existing deals to finish; the pause setting persists. Reservations and
  account top-ups alone are not evidence of recorded consumption or payment.

### Ware unlocks

| Level | Newly unlocked wares | Units/game hour on unlock |
|---|---|---|
| 1 | Food rations, water | 2,000 each |
| 2 | Energy cells | 10,000 |
| 3 | Medical supplies | 500 |
| 4 | Refined metals, silicon wafers | 300, 200 |
| 5 | Microchips | 100 |
| 6 | Scanning arrays, advanced composites | 40, 200 |
| 7 | Advanced electronics | 40 |
| 8 | Soja husk, nostrop oil | 500 each |
| 9 | Spacefuel, spaceweed, maja dust | 100 each |
| 10 | No new wares | Increased existing consumption |


### Construction, recovery and saves

- One earned upgrade queues a native expansion. Completed-level demands continue
  until the entire target plan is operational; only then change level, localized
  name, rates and wares, and reset growth to zero. Target completion is distinct
  from completed-level module readiness. No downgrades are implemented.
- Required-module damage pauses consumption and growth on the
  one-minute controller tick, retaining a pending upgrade. Hub destruction
  preserves earned level, growth and delivery totals, loses reserves and discards
  the upgrade; rebuilding consumes nothing. Builder replacement retries every five minutes
  when a suitable idle ship exists. Preserve leftover build storage, cargo and
  reservations.
- Cumulative plans preserve prefix indices/positions and use native
  straight/cross connector snap offsets. Module counts are
  4/6/8/11/13/16/19/21/23/27. Every upgrade adds storage/connectors; levels
  4/7/10 add S/M docks and 6/10 add piers.
- The hub is placed near the sector outskirts. `ReserveGrowthPlot` targets bounds +/-6/4/16 km around the hub (12 x 8 x 32
  km). Compute positive per-side deficits, check and extend exactly those
  amounts, then verify bounds before unlocking upgrades. Preserve
  larger/off-center plots; an already-covered layout needs no extension.
  Rejected checks keep the upgrade lock. Reconciliation retries after the
  placeholder becomes a container. Actual collision volumes, pier approaches and
  plot acceptance remain runtime gates.
- Legacy energy-only `Start` state is detected and canceled by the separate
  `Init` namespace before new state is created; a logbook warning blocks the
  save. Start leveling from a pre-prototype save. Existing leveling saves migrate once to empty reserves and zero growth; old
  deliveries were already consumed. Pending upgrades remain earned. Subsequent
  reloads preserve balances, growth and native trade/build references.

### Hub appearance and optional testing UI

- `ce_civilian_hub_macro` is indexed in `index/macros.xml`, reuses the generic
  factory component/control room and sets `mapob_tradestation` /
  `si_tradestation` artwork without workforce capacity or ownership claim.
  New/replacement hubs use it; previously saved station macros are not migrated.
- The dedicated `ce_civilian_hub` module set uses `type="tradingstation"`,
  `player="true"` and `constructionvesselrequired="true"`. Earlier notes
  recorded `player="false"`; it was restored to vanilla convention. No race
  association or GOD entry is added. The lack of race association avoids normal
  race-specific `get_module_set_macro` selection; the namespaced ID avoids
  InitUniverse's exact-ID standard trade-station ware injection. No global icon
  parameters are patched. The intended 2.5 map scale and construction appearance
  remain unverified.
- Optional kuertee UI Extensions integration follows Supply Chain View hooks;
  the economy does not require it. Commands use `AddUITriggeredEvent` to
  `event_ui_triggered`, revalidate the target against the registry and use
  arrays for snapshots to avoid MD/Lua table-key translation issues. Reopen to
  refresh.
- Installed UIX `prepareActions` returns false when native
  `GetNumCompSlotPlayerActions` is zero, even with custom sections prepared.
  Closing before drawing can leave mouse bounds uninitialized. CE preserves
  native success and allows its populated section only for the exact registered
  hub on failure. It neither fabricates native trade actions nor changes other
  objects' menus.

### 2026-09-20 — civilian map status

- Version-3 snapshots show remaining supply time, reserve bars, buying and
  incoming units, and one cumulative growth bar. Empty is red, below 15 game
  minutes is yellow; low supplies still earn growth. Sort by urgency on opening
  then retain stable ware-ID ordering until selection closes. Five rows per page.
- Incompatible snapshots are unavailable, never fabricated empty supplies. Invalid
  current-version snapshots retain copied last-valid rows marked stale. Next-level
  unlocks come from the saved sector profile. Cache refresh is one real second;
  MD publishes each game minute and on delivery.
- Native source exposes `MapMenu.createSelectedShips(frame)` as the selection
  table slot and `refreshMainFrame` as its rebuild request. Preserve one table
  and bottom positioning. Native percentage bars use a one-pixel anchor cell
  with a status bar extending behind the following transparent icon/text cell,
  following vanilla storage-bar layout. Both fill and numeric label refresh
  through function-valued properties.
- The adapter uses exact registered, valid, known component identity rather
  than station class, so construction placeholders can use the same display.
  No ownership changes or UI Extensions dependency are introduced. Mocked Lua
  checks cover registration, identity, refresh, pagination, percentage bars and
  preservation of native hover text. Updated bar layout remains a runtime gate.
- MD now appends `$PauseReason` as snapshot field 12, retaining every earlier
  index. It derives the reason alongside readiness without changing economic
  rules: constructing, wrecked/damaged required modules, zero population,
  ownership changed, hub unavailable or other unavailable modules. The native
  component properties `.exists`, `.isconstruction` and `.iswreck` distinguish
  construction from confirmed wreckage. Generic non-operational modules are not
  automatically called damaged. Old snapshots use the generic paused label until
  refreshed. The separate testing switch pauses new offers, not consumption.
- User screenshots confirmed the first text-based implementation displayed hub
  data but exposed an unsupported em-dash glyph and excessive tooltip text.
  It is replaced by printable `N/A`, field-specific two/three-line tooltips and
  tables without pipe separators. The detailed map tooltip was removed; at the
  user's request, a two-line hover with only level and compact population was
  restored. It clears on leaving the hub, special modes and map cleanup.
- No custom-row interface for the vanilla station popover was found in extracted
  Lua: `SetMapStationInfoBoxMargin` controls margins, while the `infobox` block in
  `libraries/parameters.xml` controls appearance/offsets. This is a source-search
  finding, not proof that no engine extension exists. The user chose to retain
  basics in the bottom panel for now rather than add a separate summary card.

### Using the testing menu

With **kuertee UI Extensions**, right-click the
hub and open **Custom Actions → Civilian Economy — Testing**.

- Level/target, operational state and cumulative growth are displayed. Hover a
  ware for reserves, consumption, target, buying and incoming quantities. Reopen
  to refresh. Construction replaces growth progress while an expansion is pending.
- **Force finish current construction** invokes the native workshop shortcut. It
  may bypass materials and time; never use it as evidence of ordinary construction.
- **Queue next upgrade — testing** bypasses the growth requirement only. It still requires
  construction and does not grant goods, satisfaction or payment.
- **Pause new civilian reservations — testing** continues consuming reserves but offers
  no new stock for sale to the hub. Existing reservations finish normally. During
  unloading the offer rewrite waits until the trade finishes; pause is not a trade
  cancellation. Resume using the same menu. The pause setting survives saves.


## Game Engine Findings

- A station is not an entity blackboard: the prototype's station marker write
  failed. Persist exact hub identity on `player.entity.$ce_hub`, repaired from
  the registry during reconciliation; UI and builder policy use the same
  reference.
- Construction placeholders fail station/container class checks. UI
  identification needs a valid component plus exact hub identity. Delay
  station-account creation and `can_safely_extend_build_plot` until the hub is a
  container; build storage can have its own funded account before then.
- Unstaged construction plans require stage 0 and build method `default`. The
  engine warned and clamped the prototype's stage 1 to 0 without losing its
  plan.
- `common.xsd` defines `extendbuildplot` inputs as incremental additions.
  `buildplot.max` is a half-size about the plot center: `rml_claimplot` doubles
  it for dimensions, while `Setup_Gamestarts` passes it directly to
  `set_build_plot`. Treating full dimensions as half-sizes can double the
  intended plot.
- Table iteration requires `.keys.list`, not bare `.keys`. The limited test
  interpreter originally accepted the invalid form; runtime errors exposed it.
  Readiness scans must also stay within the current construction sequence count.
- Event listeners bind to a particular hub; do not assume reassignment of `$Hub`
  retargets them. Instantiate a start listener per hub and cancel it on
  destruction. Dispatch `WatchLevelHub` from `LevelTick` after Init's child
  listener is active; the initial Init-time signal arrived too early. Address
  cues by their MD namespace (the prototype's `Start.WatchHub` address was
  wrong).
- X4 treats unescaped parentheses in localized text as comments. Escape the
  level suffix's parentheses. Screenshots also showed missing em-dash glyphs and
  clipped submenu text; use compact ASCII labels with multiline tooltips for
  details.

## Relevant Vanilla Concepts this Mod Interacts with

### Trade and ownerless stations

- `scriptproperties.xml`: `trade.amount` is availability; `offeramount` includes
  reservations. `update_trade` exists, but the located vanilla uses primarily
  mutate deals. Reservation-preserving persistent offer updates remain a runtime
  verification requirement.
- `rml_trade_wares.xml`, `TradeOffer_TradeOrder_Completed`: completion's
  `event.param` is the deal received as `event.param2` at start. Count its
  `.transferredamount`, not the offered/reserved quantity, and use its unit
  price.
- `create_trade_offer virtualmoney="true"` means no transaction takes place. A
  paid sink uses virtual cargo with `virtualmoney="false"` and funded object
  accounts. `diplomacy.xml` provides precedents for `transfer_money` from
  `faction.ownerless`; CE account/payment behavior still needs a fresh runtime
  test.
- Ownerless stations lack normal trade-manager initialization;
  `build.buildstorage` skips their completed-station init signal. CE explicitly
  creates an ownerless manager with Argon appearance and emits station
  initialization on activation.
- Native build storage seeks a builder only when ready and does not apply CE's
  sector-hostility policy. CE disables only that branch for its marked hub and
  assigns early; native `DeployToStation` handles travel/deployment.
- Vanilla shortage collection walks stations of active faction economy managers.
  An ownerless scripted hub cannot be assumed to trigger NPC industrial
  expansion.

### Construction and appearance

- `create_station` accepts a construction plan; vanilla prefab construction uses
  `station_gen_factory_base_01_macro`, construction state and queued processing.
  `add_build_to_expand_station` accepts a cumulative plan. CE checks saved build
  references and native queued/in-progress counts before retrying; native plan
  merging and entry identity preservation still need runtime verification.
- `libraries/parameters.xml` maps station classes to icon scales: headquarters,
  shipyard and wharf 3; equipment dock, trade station and pirate base 2.5;
  defence station 2; other station and construction 1.5. These are global class
  mappings, not proven per-object overrides. `libraries/icons.xml` separates
  `mapob_*` map symbols from `si_*` HUD symbols; selecting artwork alone does
  not prove scale.
- The Argon trade-station macro sets identification, faction-headquarters and
  HUD icons, but also workforce capacity 250 and ownership claim 1. Copying the
  whole macro for appearance would introduce unrelated behavior.
- Vanilla `menu_station_configuration.lua` exposes
  `ForceBuildCompletion(UniverseID)`. Its workshop button checks
  `GetCurrentBuildProgress(container) >= 0` or
  `IsBuildWaitingForSecondaryComponentResources(container)`. CE mirrors those
  conditions and guards exact hub identity. CE adds no gamestart restriction;
  internal native restrictions remain unverified. Forced completion proves
  neither material delivery nor ordinary builder behavior.

### Population, workforce and sector state (design research)

These findings came from the extracted vanilla/DLC schemas and scripts during
civilian-economy design. They describe possible integration points, not features
implemented by this mod. Runtime effects require separate verification.

- Planetary population is not merely flavour. `libraries/mapdefaults.xml` and DLC
  equivalents define planet/moon `maxpopulation`; vanilla `menu_map.lua` calls
  `GetSectorPopulation()` and reads `populationworkforcefactor`. Absence of a
  population property on the MD sector datatype does not imply engine absence.
- Sector `worlds/world` entries associate sectors with celestial parts and can
  weight their contribution with `factor` (for example, Ianamus Zura VII uses
  `0.5` for a body also referenced by Ianamus Zura IV). Resolve shared system
  definitions as well: Sol bodies are defined in `Cluster_106_macro`, while Earth
  and Mars sectors reside in other clusters. Do not assign a cluster-wide sum to
  every sector, treat missing `maxpopulation` as zero, or mix Timelines mission
  definitions with sandbox populations.
- Station workforce, planetary definitions, engine-derived sector population and
  the mutable terraforming population stat are distinct. Workforce is available
  through `container.workforce.amount/.capacity/.amounts`; terraforming population
  through `cluster.terraforming.stat.population.value` and `set_terraforming_stat`.
  Their runtime interaction is unverified; `maxpopulation` is not an established
  writable live population counter and does not imply a simulated civilian economy.
- `parameters.xml` defines workforce growth's population contribution as
  `<population limit="10000000000" step="1000000" max="1000" />`, with a +1,000%
  availability cap; the UI multiplies the factor by 100 for display. The same
  workforce block defines sustain, update cadence and capacity-dependent growth.
- Source correction (2026-09-21): do not equate `race.workforce.resources` with
  `food_<race>` trading baskets. `wares.xml` defines `workunit_busy/idle`
  production inputs, with DLC methods for Split, Boron and Terran. Boron inputs
  include water, bofu and medicine; Split includes chelt meat, scruffin fruit and
  medicine. `GM_LargeSupply` uses the native workforce-resource property directly.
  CE uses that same property; exact runtime mapping still needs engine verification.
- `space.economy` and `space.security` have `mapdefaults.xml` defaults and MD
  `set_space_*` / `reset_space_*` actions. Explicit values supersede parent spaces.
  Vanilla uses them in station placement (`finalisestations.xml`), hostile encounter
  chances (`encounters.xml`) and war eligibility (`x4ep1_war_subscriptions.xml`,
  security threshold `0.75`). They affect existing systems; they are not independent
  civilian prosperity scores.
- Sector ownership is derived from claiming stations, with
  `sector.iscontested`, `.contestingfactions` and `faction.willclaimspace` exposing
  related state. Changing a claiming station's owner can affect sector ownership;
  do not assume a direct sector-owner setter.
- Vanilla `boarding.xml` uses per-object MD variables on actors. That precedent
  does not establish support or persistence on sectors/clusters, nor does it
  override CE's observed station-blackboard failure. Retain the proven registry.

### Terraforming as a possible supply-contract mechanism

- `libraries/terraforming.xml` provides native recurring supply examples:
  `eco_clinic_supply` uses medical supplies, population-scaled resources, a payout,
  cooldown and delivery drone. `eco_campus_supply` selects 2–3 wares from a larger
  list and pays 250% of its price. These are useful analogues, not CE dependencies.
- The MD API includes `initialise_terraforming` with a cluster and environment
  part name, project/event/stat actions and project lifecycle events.
  `add_terraforming_project` accepts inline conditions, effects, resources,
  deliveries and related project data. Resource `pricescale="population"` is
  defined per 100,000 inhabitants; repeat/cooldown, payout and ware-selection
  options support recurring contracts.
- Sector `worlds/world` entries help locate celestial part names; they are not
  proof that every body is a supported terraforming target. Initialization on
  arbitrary clusters and access to the UI without a terraforming mission remain
  unverified. Prototype those gates before adopting this mechanism.

### Scripted offers and NPC economy integration

- Vanilla scripted-offer precedents include `rml_barterwares.xml`,
  `gm_barterwares.xml` and `order.mining.routine.xml`. `create_trade_offer` selects
  buy/sell direction through `buyer`/`seller`, a host through `object`, virtual
  cargo through `virtual`, and public eligibility through `playeronly="false"`.
  This does not bypass normal faction/trader eligibility or guarantee delivery.
- `trade.find.free.xml` scans `find_buy_offer` without an offer-origin filter.
  Its gates include the trader's ware basket, operating spaces, known/eligible
  trade partners and minimum offer volume. `excludemissions` defaults to true;
  attaching a `missioncue` can exclude an offer from ordinary NPC trading.
  Source eligibility alone does not prove identical handling of virtual offers.
- Free traders consult `global.$EconLogic_NotableBuyOfferTable.{faction}` before
  their generic scan. `factionlogic_economy.xml` rebuilds it during shortage
  evaluation; injected entries would be transient and could displace priorities.
  CE does not use this channel.
- `factionlogic_economy.xml` evaluates sector/ware shortages, weights nearby
  sectors and can request production modules/factories. This works through faction
  economy managers, so it does not establish that CE's ownerless demand triggers
  NPC expansion. Vanilla also staggers sector evaluation with short delays.
- `common.xsd` permits `event_trade_completed space=`, mutually exclusive with
  buyer/seller filters, and documents `event.param` as a trade offer and
  `event.param2` as a trade order. Broad listener coverage/volume was not established
  by the research; CE's failed galaxy listener is evidence against assuming it.
  Use the exact-deal RML pattern described above for civilian accounting.

### 2026-09-20 — civilian-hub mission research

Source inspection of the local extracted game files, not an in-game test or an
installed-mod effective-tree audit:

- `md/genericmissions.xml`, `Manager` and `EvaluateSectorMissions`, explicitly
  exclude both `faction.ownerless` and `faction.civilian` from normal offer
  stations. CE hubs therefore need deliberate mission integration. A global
  removal of those exclusions would affect unrelated stations too.
- Vanilla separates the generic scheduler, `GM_*` offer/lifecycle wrappers,
  `GMC_*` chains, and reusable `RML_*` objective libraries. RML calls commonly
  take `MissionCue`, `EndSignalCue`, and `StartStep`, returning feedback to their
  caller. Check each library's actual interface and failure handling.
- `libraries/md.xsd` defines `create_offer`, `create_mission`, mission threads,
  briefing objectives, objective updates, timers and abort handling. Offer
  location and commissioning faction are separate inputs. `GM_SupplyFactory.Start`
  additionally exposes client/owner overrides, localized text tables, rewards,
  conversation/event offers and offer visibility controls. A valid client and
  successful native offer display on an ownerless CE hub remain runtime gates.
- `RML_SupplyFactory` checks actual cargo against cargo targets; it is not a
  suitable direct completion test for CE's virtual civilian consumption.
  `rml_deliver_wares.xml` explicitly deprecates itself in favour of
  `RML_Trade_Wares`, which tracks specified trade offers. For contracts on CE's
  continuously refreshed public offers, a dedicated completion tracker using
  existing delivery accounting is a design candidate, not a tested feature.
- `RML_Transport_Passengers_V2` supports an NPC, start object, destination,
  optional automatic boarding and a timeout; destination/dock destruction is
  handled explicitly. `RML_Harvest_Resources` allows any player-owned collector
  or specified collectors. `RML_Protect_Object` supports groups, timers and
  external end signals. Delegation eligibility is specific to each objective.
- Candidate CE missions: shortage relief, sustained supply, passenger transfer,
  convoy protection and construction support. CE-specific triggers/rewards
  require custom MD state and accounting; mission text alone changes no economy.
  Keep any future mission controller separate from the existing hub controller.

## Experiments and validation limits

- **Construction inspection (save_018, 2026-09-18):** the four-module
  placeholder had a deployed builder, hull parts/claytronics in build storage
  and a processor waiting for energy cells. A trader reserved cells but was
  still at its supplier; reservation did not mean delivery. Civilian readiness
  was false with no civilian offer. Disappearing material offers were explained
  by real build-storage stock.
- **Replacement/overlap (save_019):** the user reported hub replacement, builder
  replacement and overlapping deliveries. Old build storage predated reload and
  retained materials/outgoing reservations without build tasks. It was not
  evidence of a duplicated hub, and deleting it would disrupt cargo/trades.
- **Accounting failure:** account top-ups and sales occurred while recorded
  deliveries/payments stayed zero and internal demand rose. This exposed the
  galaxy-listener defect and motivated exact-deal listeners. Old reports of
  visible trade/replacement cannot validate leveling qualification. Test fresh
  deliveries, not trades already unloading during an update. Continuous NPC
  supply also prevented a controlled prototype cap test.
- **Plot/UI repair:** screenshots confirmed clipping/missing glyphs; source
  review confirmed the doubled-plot defect, but did not establish the exact
  obstruction pictured. Later logs confirmed invalid table iteration,
  out-of-range readiness scans, early listener dispatch and placeholder
  clearance calls. Mouse-bounds errors were observed; zero native actions and
  the role of the module-set player flag remain inferred causes. Repair checks
  are not live-game acceptance.
- **Local validation scope:** Python checks execute shipped MD action trees
  through a limited interpreter, stub native lifecycle actions and copy
  reference graphs for persistence tests; they do not emulate X4 or its save
  serialization. Lua tests use mocked UI behavior. Geometry checks cover
  prefixes, classes, snap offsets and margins, not actual collision/docking
  clearance. Plot tests cover centered growth, off-center preservation,
  rejection and oversized no-op plots.
- `tools/generate_plans.py` regenerates only CE's cumulative plans. Full schema
  checks cover MD and the in-memory patched native `build.buildstorage` AI,
  comparing errors with the vanilla baseline because direct validation skips the
  diff-rooted script. Construction-plan data and macro asset properties have no
  bundled declared schema. Historical passing test counts are not evidence of
  current runtime success.
- **Remaining gates:** fresh paid food/water accounting, reservation/event
  ordering, natural qualification, plan merging, every expansion, plot/docking
  geometry, save/reload during builds/trades, recovery, construction-site
  interactions and icon scale. Use the runtime guide and record shortcuts
  separately; no full leveling runtime pass is established by the source notes.

### Local check commands

```powershell
python tools/check.py
python tools/check.py --schema
uv run --with lupa python tools/test_debug_menu.py
```

Restart X4 after source updates before testing. These local checks do not emulate
the game; use the runtime test guide for acceptance.

## 2026-09-21 — local-population-profiles

- Implemented a separate synchronous MD profile resolver with string-ID overrides;
  see ARCHITECTURE for the adapter contract. Reads live race/ware lookup lists,
  supports new races and replaced workforce resources, and skips missing cargo.
- Population race is inferred once from sector ownership, with explicit macro-ID
  overrides. It is not a measured demographic breakdown and remains stable on conquest.
- Level 8 imports unique foreign staples; local foods retain level 1 rates. Terran
  industrial/luxury defaults differ. Water and pharmaceuticals are not exotic food.
- Source and mocked-action checks cover base/DLC recipe fixtures, conversion wares,
  migration and unchanged-load history preservation. Native reservation completion,
  profile discovery and save serialization still require an in-game acceptance pass.
- MD source checks: `macro.id` is the internal macro identifier (`macro.name` is
  display text); table size uses `.keys.count`, not `.count`. The test interpreter
  is permissive here, so property-schema inspection remains necessary.
## 2026-09-22 — sector-reward-feasibility

READ from extracted vanilla sources; these are integration candidates, not
implemented or runtime-tested CE rewards:

- `common.xsd:20007` exposes object-scoped `add_player_discount`, including
  optional ship sales/upgrades; `19571` onward exposes commissions. Amounts
  represent fractions of ware price variation, not a flat percentage off the
  current price (`1011`). `md/diplomacy.xml:4367` uses station discounts.
- `common.xsd:39205` provides race-specific `add_workforce`, capped by habitation
  capacity; `md/inituniverse.xml:237` uses it. Scripted immigration is a candidate
  for faster growth; a dynamic station growth multiplier was not established.
- `md/diplomacy.xml:1943` centralizes `Success_Evaluation`; `2037` assembles
  success chance and `2038` caps ordinary rolls at 99. The library receives no
  destination parameter. Station-targeted callers would need to pass target
  context for a sector bonus; action 7 evaluates success at operation start
  (`4218`), not completion.
- `md/terraforming.xml:330` and `1857` onward use `set_skill` on crew templates;
  training also uses `add_skill`. This supports a custom recruitment/training
  service, but does not establish a universal sector-local hiring hook covering
  both station actors and shipyard crew purchases.
- `common.xsd:38738` defines object-specific trade subscriptions with optional
  duration; `md/signal_leaks.xml:1886` supplies a vanilla usage precedent.
- Design consideration: CE qualification includes NPC deliveries. Sector level
  alone would grant player rewards without proving player contribution. Player
  eligibility, existing-benefit preservation and reward lifecycle need separate
  design before implementation.

## Profile reload lookup repair

- Runtime debug.txt confirmed `Failed to set table[].argon` and equivalent ware
  errors during Reload. MD string table keys require a literal `$` prefix;
  native factionlogic_staticdefense.xml uses `{'$' + $Ship.idcode}` likewise.
- Profile dictionaries now consistently prefix ware/race/sector string keys,
  including configured overrides and deduplication. Stored ID values stay plain.
  The old test interpreter stripped `$` inside quoted strings and permitted
  invalid profile writes; both behaviors are corrected and regression-tested.
- Empty saved definitions can be rebuilt on load while retaining backlog and
  lifetime counters. Already-cleared qualification history cannot be restored;
  rebuilding changed definitions starts a fresh window. Unchanged valid profiles
  retain their existing history.

## Resilient profile and details refresh

- Profile builds must not clear saved definitions in place. Candidate definitions,
  race and rates now complete and validate before commit; failed refreshes retain
  last-valid economics. Level application consumes saved definitions rather than
  repeating native profile discovery.
- Active membership is separate from rate, so zero-population demand still has
  display identity. Metadata migration does not reset qualification. Retired
  records retain trade guards, offers and counters but are excluded from details.
- Snapshot fields 13/14/15 add version 2, profile error and stale status while
  preserving the existing 12-field contract. A missing/incomplete row set is not
  interpreted as an empty civilian economy. Preserve last-valid rows and expose
  the failure until recovery; do not mask failures as fresh data.
- Failure-injection tests cover missing lookups, invalid keys with continued
  execution, incomplete candidate/rate stages, duplicate/invalid rates, isolated
  delivery scopes, unchanged reloads, migration and intentional empty profiles.
  Native in-game validation remains required; mocks do not emulate all MD errors.

## 2026-09-22 - reserve model supersedes rolling qualification

- Earlier dated history/fulfillment notes describe the replaced implementation.
  Current behavior is defined in the sections above and root ARCHITECTURE.
- Saved `$ReserveVersion=1`, `$GrowthSeconds`, `$Last` and per-ware `$Reserve`
  replace minute buckets. Migration does not remove native trades, accounts,
  pending builds or captured listener references. Library/cue namespaces stay stable.
- Full surplus is retained, targets round upward, whole-unit shortfalls round
  downward before subtracting reservations. A positive tiny rate can buy one unit.
- Native Helper `statusbar:createDescriptor` evaluates current/start/max functions
  but reads `valueColor.glow` directly. Pass static colors and rebuild on warning
  changes; preserve order across those rebuilds. This prevents a Lua runtime error.
- Automated action and Lua tests cover exact exhaustion, cumulative pauses,
  non-retroactive deliveries, migration, surplus, pending transitions, profiles,
  stale recovery and ordering. Native disposable-save acceptance is still needed.

- Reserve rollout local validation: `just check` passed 67 MD action tests and
  all Lua integration tests; `just schema` passed full MD and merged AI checks
  with no introduced errors. No native gameplay pass was performed for this
  reserve version. Full X4 restart is required before disposable-save testing.

## 2026-09-22 - two-pane-civilian-panel

- READ: native MapMenu cargo rows use `cellBGColor=rowgroup_background_default`
  and an adjacent status-bar anchor behind a transparent icon/text cell
  (`reference/ui/addons/ego_detailmonitor/menu_map.lua`, around 20262).
- Applied that pattern to the civilian ware pane; level and population live in
  the left pane, alongside cumulative growth. Growth time overlays its bar.
- Dark local green/amber/red bar fills avoid bright backgrounds under white
  labels. Helper documents Lua color alpha as 0-100 (RGB remains 0-255).
- Lua checks cover both panes, reserve/progress bars, cargo background properties,
  stable ordering, pagination, warnings, missing data and narrow-window geometry.
  Actual in-game spacing still requires visual confirmation.


## 2026-09-22 - compact-supply-pane

- READ: vanilla cargo uses statusbar start=current stock, current=future stock,
  and posChangeColor for incoming quantities; CE now follows this for reserves.
  Incoming still contributes neither consumption time nor growth until delivered.
- Background colspan from ware column through Buying now fills visible column
  gutters while preserving native cell geometry. No global border size changes.
- Explicit icon widths are necessary for left-aligned labels over full-width bars;
  the prior growth text used an implicit icon size and appeared shifted left.
- Buying now delegates localized grouping/shorthand to native ConvertIntegerString
  with the same parameters as cargo. Lua tests mock the formatter; actual native
  threshold/localization behavior is delegated to the engine, not reimplemented.
- Checked compact panes, stock/incoming bar segments, pagination and stale/error
  recovery with just check and just lua. In-game visual confirmation is pending.

## 2026-09-22 - combined-ware-supply-row

- Combined the name and remaining-time fields under one heading and one shared
  blue-stock/green-incoming bar. Separate internal text cells reserve room for
  each label; explicit widths avoid overlapping the right-aligned time.
- Shortened Running low to Low and Buying now to Buying in the English catalog
  (the repository's only translation file). Other ware statuses stay unchanged.
- The economy, thresholds and snapshot contract are unchanged. Lua checks cover
  combined bar width, live labels, reservation segments and pagination; actual
  in-game appearance remains a visual acceptance check.

## 2026-09-22 - ware-row-baseline

- User screenshot showed Water's name/time below its status and buying quantity.
  The row also contains wrapped left-pane unlock text. Mixed icon-label and text
  cells appear to align differently when that shared row grows taller.
- Ware name/time now use ordinary text cells like status/buying; the reserve bar
  remains in its preceding anchor. This removes mixed label widget alignment.
  Native visual confirmation is still required; Lua mocks do not reproduce
  engine vertical placement in a tall row.
- Ware statuses are now Needed, Low, Supplied, Full and Paused.


## 2026-09-22 - independent-pane-heights

- User screenshot confirmed that aligning text widgets alone did not solve shared
  row height: wrapped left unlocks still stretched an Energy Cells row.
- Replaced shared table rows with independent title/left/right tables under one
  frame border. Native MapMenu uses multiple tables under a shared border (e.g.
  orderHeaderTable / orderHeaderTableRight around lines 10489-10492).
- Lua layout checks simulate additional left-pane height and verify unchanged
  right-table height. This is a structural test, not an in-game visual check.
- Lua-only change: /reload suffices for this layout update. Old localized labels
  such as Needed now still require the previously requested full game restart.


## 2026-09-22 - positional-viewcreated-contract

- READ: reference MapMenu.viewCreated around line 7028 binds player/search/sidebar/
  rightbar/selectedShips/topLevel/map by positional arguments (one extra right-info
  table when searching). createSelectedShips is followed by the map render target.
- READ: widget_fullscreen.lua:7640-7641 looks up the supplied render-target ID and
  multiplies GetRelativeMousePosition's return without guarding nil coordinates.
- Runtime debug.txt after the three-table change repeatedly reports invalid
  GetRelativeMousePosition parameters and nil posX at 7641. Added tables shift the
  native bindings, explaining why there was no direct CE exception in the log.
- Removed the three-table integration in favor of the user's fallback: one table,
  summary above wares. Previous notes claiming independent tables were ready based
  on mock row heights were incomplete; the tests missed the native ID contract.
- Regression checks now require exactly one table from the selection hook. A UI
  /reload is needed after this Lua repair; restart if the damaged UI cannot reload.
  Actual in-game recovery remains to be confirmed.


## 2026-09-22 — frozen sector profiles and native racial construction

- Schema 4 snapshots every sector before population filtering; race-level demand and
  component choices persist through conquest, later eligibility, reload and replacement.
  Sector overrides were removed. Existing construction schemas require a fresh game.
- Native `get_module_definition` supports race/category discovery without faction
  filtering. `macro.numpierdocks` measures capital pier capacity; `numdocks` S/M tags
  measure dock areas. Choose functional capacity, not hardcoded race names/macros.
- `create_construction_sequence` is asynchronous unless `immediate` is supplied;
  `event_object_construction_sequence_created` supplies the resulting sequence/null.
  Native finalisestations.xml provides the pattern. `base` preserves existing layout;
  verify entry IDs/macros and the functional basket before queueing expansion.
- Readiness now uses saved sequence entry IDs, including generated connectors. Static
  Argon module-count arrays are not applicable to racial layouts. Target layouts and
  build tasks are separate state; a lost task reuses the saved target layout.
- Source/test evidence: every macro in native Terran dock, storage, pier-base and
  connector groups has a default recipe using only Terran construction materials
  (plus energy cells). This verifies recipe compatibility, not actual NPC deliveries.
- Runtime acceptance still required: empty station shell/build storage, native geometry
  for all loaded races, construction with NPC deliveries, save/load during generation
  and builds, and subsequent expansions. Mock tests do not prove engine behavior.
