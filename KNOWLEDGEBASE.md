# Mod-local Knowledgebase

Code ownership belongs in [ARCHITECTURE.md](ARCHITECTURE.md). Start with the
[README](README.md) for an introduction and the
[developer documentation](docs/DEVELOPMENT.md) for development guidance.

## 2026-09-24 - extension-options-settings

- READ: installed packed Mod Support APIs v195 declares ID `ws_2042901274`.
  `Simple_Menu_API.Register_Options_Menu` registers on its `Reloaded` signal.
  `Make_CheckBox` calls onClick with checked=0/1; `Make_Slider` takes min/max/step
  and calls onSliderCellConfirm with value/valuechanged. Native helper.lua also
  documents fractional slider steps; gameoptions.lua uses a 0.01-step slider.
- IMPLEMENTED: separate CE_Options presentation and CE_Settings per-save state.
  All five settings belong to the save, not profile userdata. Ensure only fills
  missing keys. Default debug visibility is false; tax messages default true.
  Multipliers now range 0.1-10.0 in 0.1 steps (superseding the initial 1.0 cap);
  tax ranges 0-50 in whole percentages.
- READ/FIXED after native screenshot: unspecified checkbox width filled the
  slider column and stretched its symbol. Both dimensions now use the API's
  `Helper.standardTextHeight` reference, following native gameoptions.lua's
  equal-text-height checkbox pattern. Native rendering of the fix is pending.
- Demand multiplier applies to frozen definition rates, never to already-scaled
  rates. Changes settle old consumption first, retain reserves and deal/offer
  identities, then recompute rates and targets. Active unloading still defers
  offer edits. Time multiplier changes required supplied seconds, preserving
  earned growth; normal minute ticks own actual qualification/construction.
- Tax=0 skips the transfer. Notifications=false suppresses ticker and logbook
  only. Debug visibility gates menu building, stale callbacks and placeholder
  fallback, but does not cancel asynchronous debug work already requested.
- MOCKED: 152 action tests passed, including live transitions, reservations,
  unloading, tax endpoints, callbacks and retained defaults. All three Lua suites
  passed, including default-hidden hub/sector debug actions. These checks do not
  establish native menu rendering or save/load acceptance.
- MEASURED: x4validate includes research XML stored under `.validation/` in its
  payload/reference scan. Keep extracted research copies as `.xml.txt`; otherwise
  they introduce unrelated external text references into this mod's validation.
- Full restart required for the new MD modules and dependency; /reloadui alone
  cannot install this backend. Once installed, setting changes apply in-session.
- VALIDATED: final `just schema` passed all 152 action tests, native MD schemas,
  reference checks and merged build-storage AI validation. `just lua` passed all
  three suites; `git diff --check` passed. No in-game acceptance was performed.

## How this Mod Works

### 2026-09-24 - debug-checkbox-component-id

- MEASURED: save_002 load beginning at debug.txt:2556 reports GetNPCBlackboard
  rejecting cdata as its entity argument during right-click interaction. The
  deployed debug reader passed C.GetPlayerID() directly, unlike ce_hub_status.
- FIXED: convert through ConvertStringToLuaID(tostring(C.GetPlayerID())) before
  reading the debug flag. No settings-state or MD change is required.
- MOCKED: returning a real LuaJIT uint64_t and rejecting unconverted IDs makes
  the old code fail in debugEnabled. This replaces the permissive numeric mock.
  Lua-only fix: /reloadui suffices after deployment; native retest remains pending.

### Demand, payment and progression

- READ (2026-09-24): `CE_Trade.RecordDelivery` pays configurable sales-tax income (default 15%) to
  `faction.player` from `faction.ownerless` for completed civilian purchases in
  a currently player-owned sector, regardless of seller. It uses actual
  transferred quantity and deal unit price after consuming the duplicate guard.
  Seller payment and `$Paid` remain the original transaction value. Zero-value
  deliveries pay no tax; separate build-storage purchases do not enter this path.
  Native payout still requires in-game verification. MD changes require a full
  restart; UI `/reload` is insufficient.

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
  snapshots are selected by hub ID. No singleton adoption path remains.
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
  ware. New games use price-normalized category budgets (see the final-demand
  entry below); existing frozen profiles keep their saved quantities. Hub purchase
  prices remain `ceil(min + (max - min) / 10)`.
- Advancement from level L requires (L+1) cumulative supplied game hours times the configured time multiplier. All
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
  accounting to prevent duplicate credit. Obsolete disabled listeners have been removed.
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

- READ (2026-09-24): `CE_Notifications` announces upgrade construction after a
  valid task reaches `StartBuild`, once per saved target level. Completion is
  announced on the level-commit transition after `UpdateOffers`, with separate
  text for new goods, increased existing demand, and paused offers. Both use
  the message ticker and General logbook with a hub map link. Initial builds,
  repairs and retry/reload ticks do not independently count as upgrades.
  Full restart required; notification display remains an in-game check.

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

- READ (2026-09-24): `libraries/common.xsd` documents `show_notification` as a
  non-interactive message-ticker notification (default timeout five seconds),
  `show_interactive_notification` as a target-monitor interaction, `show_help`
  as tutorial/help text, and `write_to_logbook` as a persistent log entry.
  Vanilla `md/notifications.xml` uses General log entries with `money`,
  `object` and `interaction="showonmap"` for station-defence rewards, and has
  optional generic money-added notifications. `md/diplomacy.xml` pairs ticker
  messages with log entries. CE tax income uses that pair, with localized
  sector/ware details and native money formatting. `transfer_money/@result`
  supplies the actual amount paid; zero results produce no success message.
  Notification display still needs in-game verification.

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


## 2026-09-22 - final-demand-budget-balance

- IMPLEMENTED: default demands normalize category budgets using native
  `ware.averageprice`, converted from money to credits with `/ 1Cr`.
  Baseline units/hour = `max(10, 10 * floor(budget / price / 10 + 0.5))`.
  Local food/energy/medicine: 150,000 Cr; water/imported food: 75,000 Cr;
  industrial goods: 250,000 Cr; luxuries: 100,000 Cr, each per ware per hour
  at unlock and at 8,524,100,000 accessible population.
- Three-field adapter rows remain explicit units/hour, even when average price
  is unavailable. Optional fourth-field `'budget'` rows normalize once before
  saving ordinary three-field definitions. Native Boron water receives the water
  budget; imported workforce baskets exclude water and pharmaceuticals.
- USER DECISION: new games only. Existing frozen race/sector/record definitions
  retain placeholder rates, construction choices, progress, reserves and trades.
  No migration or schema bump. Restart plus a newly initialized game is required
  to see this balance; UI `/reload` cannot apply MD changes.
- CALCULATED from extracted vanilla base/Split/Boron/Terran prices: Argon Prime
  steady-state gross revenue is 152,500 Cr/hour at level 1, 6,069,000.24 at level
  10 without DLC foods, and 6,396,734.62 with all four DLC food wares. These are
  sales ceilings assuming all demand is supplied by one seller, not net profit;
  construction and initial two-hour reserve filling are excluded.
- `BudgetBalanceTests` executes shipped resolver/controller actions against
  extracted prices and checks 19 unlock quantities, every level's gross revenue,
  rounding, invalid prices, explicit overrides, racial substitutions and saved
  placeholder retention. These are mocked checks, not native-engine acceptance.
- VALIDATED: `just validate` passed 92 tests and reference checks; `just schema` passed full native schemas and the merged build-storage AI check. In-game acceptance remains outstanding.


## 2026-09-22 — synchronous-library-refactor

- IMPLEMENTED: demand preparation/commit, native trading/funding and diagnostics
  now live in CE_Demand, CE_Trade and CE_Diagnostics. Existing controller library
  entry points forward synchronously; persistent cues and captured records stay
  in CE_OwnerlessHub. No save migration or schema change was added.
- Profile Build takes explicit native ProfileRace/null and uses DiscoveredRace
  for iteration. CaptureSectorProfile never temporarily replaces the caller's R.
- SyncWare owns derived targets and shortfalls. Candidate rate rows carry only
  ware/rate/price. RebaseAccrual names clock rebasing accurately; ResetHistory
  remains a compatibility alias. Existing synchronization boundaries remain.
- Both UI consumers share snapshot decoding. getFresh/isHub bypass the map cache
  for testing commands; retained display snapshots do not authorize commands.
- READ: checker --reference previously set CE_REFERENCE while fixtures hardcoded
  a different path. Shared tests/support.py now consumes that configuration, with
  X4_REFERENCE/X4_TOOLKIT defaults supporting isolated checkouts.
- Supersedes the earlier two-pane architecture notes: the supported map hook
  still emits one five-column table, with summary rows above the ware rows.
- Native save/load, trading and rendering remain in-game acceptance gates.
  Full game restart is required for these MD changes; /reload is insufficient.
- VALIDATED: just schema passed 93 action tests, all seven runtime MD schemas,
  merged data/reference checks and the merged build-storage AI schema. just lua
  passed all three suites, including fresh-command-versus-cached-display checks.
  Canonical source comparison preserved the full persistent Init cue tree and
  all seven extracted trade/diagnostics action bodies (qualified refs normalized).
  No native in-game acceptance test was performed.

## 2026-09-22 - UI state and offer-loop simplification

- IMPLEMENTED: wareCode supplies stable nonlocalized states for labels, sorting,
  colors and rebuild signatures. classify supplies shared hub facts; the existing
  per-view message priorities are preserved. Neither helper changes MD economics.
- The map renderer now has separate selection, geometry, summary, ware-row and
  pagination helpers. All helpers populate the same single native table; deferred
  callbacks still resolve current snapshots by hub/ware identity.
- UpdateOffers prunes expired deals and builds a temporary ware-keyed unloading
  set once per call. Multiple deals for one ware remain guarded; no saved hub
  fields or incremental transfer cache were added.
- READ: ForgetHub immediately delegated to AccrueAll after its redundant SyncAll.
  UpdateHub readiness does not read reserve-derived values, and both branches
  synchronize via accrual/rebasing before funding. Removed only those two
  controller calls; public calculation/offer/diagnostic boundaries remain.
- MEASURED: all five UI formatters matched the pre-refactor source for 2,691
  synthetic input combinations, including missing snapshots, warnings, progression
  and ware states. This is mocked Lua evidence, not native rendering acceptance.
- Full restart is required for the MD changes. No save migration, balance changes
  or new translation keys were introduced. In-game acceptance remains outstanding.
- VALIDATED: just schema passed 95 action tests, all seven runtime MD schemas, reference/merged-data checks and the merged build-storage AI schema. just lua passed all three suites; git diff --check was clean. No native gameplay test was performed.

## 2026-09-22 - native-hub-startup-contracts

- READ/MEASURED: native scriptproperties.xml marks constructionplanentrydata as
  pseudo, not an actual datatype. The final load's failed `$Sequence.{$i}`
  assignments occurred before build queueing. Vanilla finalisestations.xml reads
  sequence-entry `.macro` directly. CE validation/readiness now retain only native
  macro/entry-ID values, never the entry intermediate itself.
- MEASURED: the same final load rejects the five combined `@... ?` profile
  existence expressions. Existence checks use `?` alone; optional value access
  remains a separate operation. Earlier loads were excluded from this repair.
- MEASURED: profile budget arithmetic retained money type after division by 1Cr,
  warning on the subsequent +0.5f. Explicit LF casts on price and 1Cr precede
  arithmetic now. This supersedes the earlier implication that `/ 1Cr` alone
  ensures numeric credits; intended budgets and rounding are unchanged.
- IMPLEMENTED: accepted layouts and recovered tasks share StartBuild, which binds
  hub/sector from the captured record, processes construction, funds/manages build
  storage and immediately invokes existing builder selection. No eligible builder
  retains the five-minute reconciliation retry. No free initial module is added.
- TEST CONTRACT: construction-entry fixtures are non-storable pseudo-values and
  the expression runner rejects `@...?`. A narrow typed-money fixture reproduces
  the original normalization warning. The startup suite executes real CE libraries
  around mocked native actions, including out-of-order hub completions, expansion,
  no-builder retries, failed queue creation and reload recovery.
- No saved-record migration, snapshot-version change or translation key was added.
  Native geometry, delivery and builder deployment still require a full restart
  and a disposable pre-mod save/new game; mock success is not native acceptance.
- VALIDATED: just schema passed all seven runtime MD schemas, merged data and
  merged build-storage AI validation; just lua passed all three suites. Final
  just validate passed 108 action tests and reference checks. Deployed MD hashes
  match the validated worktree. Native gameplay acceptance remains pending.

## 2026-09-22 - native-startup-acceptance-and-plot-blocks

- MEASURED, last save_017 load after the startup repair: 33 hub sites created;
  the same 29 hub IDs reached layout acceptance, build start, full requested
  build-storage funding and builder assignment. No CE runtime errors or repaired
  profile/money/sequence warnings occurred. One localisation lookup advisory remains.
- Four other created sites stopped at ReserveGrowthPlot: the native safety check
  refused enlargement from 5 km half-size to the required 6/4/16 km envelope.
  They never requested layouts. Six separate invalid-components rejections had
  hub=null (three unknown races, three Xenon); these are not the four empty sites.
- Native construction queueing/funding/assignment is now observed, but completed
  modules, deliveries, expansion and save/load acceptance are still unverified.
- Current plot-failure messages omit hub/sector identifiers. Consecutive creation
  messages associate the four failures with sites, but the log does not identify
  their sectors; the user's Argon Prime observation is not independently mapped.

## 2026-09-22 - current-plot-first-retries

- IMPLEMENTED: a new hub tries native generation in its existing plot, without
  pre-reserving the static fixture's future-level envelope. Build storage is
  created after layout validation, then normal construction/funding/builder
  selection runs. Native construction still supplies all initial modules.
- Native generation failure permits a checked increment of up to 2 km on each
  plot face, capped at 16 km half-size per axis. Equal increments preserve center;
  existing larger plots never shrink. These bounds are tuning choices, not a
  measured claim that every racial level-ten layout fits.
- Failed or capped enlargement can reposition only the same completely empty,
  uninitialized shell, at most three times. A native sequence, accepted/completed
  plan, storage, build, pending callback or operational hub prevents relocation.
  Safe-position placement avoids other plots and requests clearance for the plot
  plus one growth increment. No station destruction or forced overlap is used.
- LOCAL SOURCE: common.xsd documents incremental extension, safepos.radius as
  required clearance (not search range), and warp sector-relative placement.
  Vanilla x4ep1_mentor_subscription.xml warps the HQ; its nearby storage/CV TODO
  reinforces the stricter CE requirement that relocated shells have no storage.
  Bounded _scan discovery parsed 550 base+DLC MD/AI XML files, zero unreadable.
- Internal CE_Placement.State cue data tracks attempts/failures/next eligibility/
  resize intent/placement count by hub identity. Hub loss removes its entry.
  Public record fields, profile adapters and snapshot v3 are unchanged; no
  migration or older-save repair was added.
- Retry logs include hub ID, sector ID/name, level/token, attempt count, reason,
  earliest retry time, plot half-size/center, enlargement and placement outcomes.
  Failed native warp movement is distinguished from an actual coordinate change.
  Five-minute cooldown is enforced; the next reconciliation can make the actual
  wait nearly ten minutes. Malformed layouts/build failures do not enlarge plots.
- MOCKED: current-plot success even with enlargement denied; bounded growth/moves,
  rejected/no-op native actions, preservation of off-center/oversized plots,
  established operation and base IDs, duplicate/stale callbacks, retained retry
  state across reload and a save-state stand-in, per-site cleanup and log fields.
  Real save/load, native relocation, materials delivery and completed dock/storage/
  pier remain in-game acceptance gates. Test only the final load of each debug log.
- Full restart and a disposable new game/pre-mod save are required for acceptance.
- VALIDATED: just schema passed 118 action tests, eight MD schemas and merged
  build-storage AI validation; all three just lua suites and git diff --check
  passed. These checks do not establish native construction acceptance.

## 2026-09-22 - native-current-plot-startup-and-state-cue

- MEASURED: latest save_017 load begins at debug.txt line 2556. Captured through
  line 3792 / game time 235648.20: the same 33 created hub IDs attempted and
  accepted layouts, started builds, had balance equal wanted build funding, and
  received builders. All 33 initial attempts used 5000m half-sizes on each axis.
  No generation failure, enlargement or relocation retry occurred. This proves
  the initial layouts fit the original 10x10x10 km plots for this cohort.
- Argon Prime hub 0x1b4405, sector 0x75b8c, accepted three entries on attempt one;
  native task 0x8ebc started and builder 0x80d8c was assigned at gate distance 1.
  There were no completed-level operational messages in this capture. Materials,
  completed modules, expansion, relocation and save/load remain acceptance gates.
- Six separate invalid_components diagnostics had hub=null (three unknown race,
  three Xenon missing pier/connectors). These are not failures of the 33 sites.
- FOUND/FIXED: the new State cue used check_value=false without checkinterval or
  onfail. Native parsing rejected it with 'event condition required'; XSD passed
  it. Replace its condition with event_cue_signalled: dormant event-driven storage,
  no polling or data reset. Add a CE-wide condition-mode regression that rejects
  the original cue and checks all shipped cue conditions. Native parse after this
  correction still needs a full restart; /reload is insufficient.
- A pre-existing localized-name expression advisory remains in ce_ownerless_hub.
  Last-load triage and contextual inspection found no further CE runtime errors.
- VALIDATED: 119 action tests, eight MD schemas, merged build-storage AI schema,
  all three Lua suites and git diff --check pass after the cue correction.

## 2026-09-22 - map-pagination-selectable-row-crash

- MEASURED: final load begins at debug.txt line 2556. Map failures at game times
  236758.56, 236764.16, 236770.09 and 236772.27 report row 12, column 5:
  "Button defined in an unselectable row." Stack enters native createMainFrame
  through CE's map onUpdate wrapper. Row 12/column 5 is CE's Next page button;
  this is pagination rendering, not an exception inside the right-click callback.
- LOCAL SOURCE: native helper.lua addRow documents nil/false as unselectable and
  true as a selectable row without payload. Its serialized selectable flag is
  boolean row.rowdata. Vanilla map button rows use addRow(true, ...).
- FIXED: only the pagination row requests selectable row data. Summary, ware and
  inserted filler rows remain unselectable; the one-table contract is unchanged.
  This applies whenever more than five wares need pagination, not only level four.
- VALIDATED: strict Lua frame mock rejects active buttons in unselectable rows.
  Mutating the pagination call back to the old form reproduces the exact 12:5
  error. Tests cover a level-four six-ware basket, partial last page and return
  to five wares without pagination. All three just lua suites and diff checks
  pass. Actual native map rendering still needs user verification.
- Lua-only correction: /reload suffices; no game restart required for this fix.

## 2026-09-23 - bounded-native-ware-scrolling

- User preference replaces map-panel pagination with a scrolling ware list.
  The panel includes all wares, caps at 40% of Helper.viewHeight and bottom-aligns
  using getVisibleHeight (not getFullHeight). Rows 1-6 keep summary/headings fixed;
  ware rows have fixed=false. Exactly one table preserves MapMenu.viewCreated.
- Native helper.lua documents maxVisibleHeight as enabling the scrollbar and
  fixed as non-scrolling header rows. getVisibleHeight applies the cap. Native
  map code uses getVisibleHeight for placement and GetTopRow/setTopRow for state.
- reserveScrollBar=true reserves width from the flexible fifth column. CE captures
  the same hub's current top row before nativeUpdate rebuilds, restores/clamps it,
  and resets on selection change or cleanup. No new translated text is needed;
  existing unused pagination keys are retained.
- VALIDATED: all three just lua suites pass. Coverage includes 40 wares at 720,
  1080 and 1440 screen heights, fixed headers, all rows present without buttons,
  retained scroll position, shrinking/empty baskets and the one-table invariant.
  Native mouse-wheel/scrollbar behavior remains an in-game verification step.
- Lua-only change: /reload suffices.

## 2026-09-23 - debug-advance-to-target-level

- Added localized Advance to level 2-10 debug actions. They bypass growth and
  automatically finish construction as requested by the user. Requires an active
  ownerless hub without pending construction; current/lower levels are disabled.
- MD maps a bounded command list and verifies readiness/identity/task guards.
  It sets Target (never Level directly), then uses the existing cumulative module
  requirements and generation pipeline. A direct 1-to-10 request needs the full
  17-functional-module basket and preserves completed base IDs.
- Internal CE_DebugAdvance.State targets authorize automatic completion. Existing
  public saved records and snapshot v3 are unchanged. Native tasks emit a Lua event
  with a component parameter (explicitly supported by common.xsd raise_lua_event).
  Lua rechecks fresh state/progress before the existing ForceBuildCompletion API;
  completion asks MD to refresh readiness. Missed events retry on minute ticks.
- Invalid, duplicate, lower/out-of-range, busy and wrong-hub commands do not queue
  extra layouts. Owner changes or hub loss revoke permission. Layout failure/reload
  retain a pending request; ordinary queue_upgrade never auto-completes.
- MOCKED: 124 action tests and all three Lua suites pass, including complete
  1-to-10 orchestration, preserved modules and post-construction level commit.
  Native automatic completion and its UI/event timing require in-game acceptance.
- Only the English translation file exists; keys 124-125 were added there. README
  and docs are unchanged. Full restart required for the new MD script/handlers;
  /reload alone only exposes the UI and cannot activate the backend.
- VALIDATED: just schema also passes all nine MD scripts, merged AI validation
  and content checks; git diff --check passes.
