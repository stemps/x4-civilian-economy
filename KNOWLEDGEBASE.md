# Mod-local Knowledgebase

Code ownership belongs in [ARCHITECTURE.md](ARCHITECTURE.md). Start with the
[README](README.md) for an introduction and the
[developer documentation](docs/DEVELOPMENT.md) for development guidance.

## How this Mod Works

### Demand, payment and progression

- One ownerless Argon Prime hub has ten completed economic levels. Base X4 9.00
  is required, with no DLC. No custom faction, diplomacy changes, production or
  habitation modules, galaxy placement or population scaling are included.
- Civilian demand activates only after construction; construction purchases
  never count as fulfillment. Each unlocked ware has one public virtual-cargo,
  real-money offer, a two-hour backlog cap and price
  `ceil(min + (max - min) / 10)`. `UpdateWarePrice` runs on unlock and normal
  offer refresh, so price changes can reach saved hubs without resetting
  qualification through `ApplyLevel`.
- New wares start with zero demand; existing rates rise 25% only after a completed upgrade. All unlocked
  wares, including intoxicants, count toward qualification; level 10 adds no new
  ware. These quantities and prices are diagnostic balance, not final tuning.
- Advancement from level L needs a full rolling L+1 game-hour window for every
  ware: at least 90% of scheduled consumption delivered, backlog no greater than
  30 minutes of consumption for at least 90% of the window, and no continuous
  breach longer than 15 minutes. Cap-discarded demand remains scheduled
  consumption and never counts as fulfillment.
- Per-ware history has closed 60-second buckets plus a partial bucket excluded
  from evaluation. Accrual splits at exact boundaries and computes
  threshold-crossing times before capping. Buckets retain generation,
  deliveries, good seconds, leading/trailing bad seconds and longest internal
  breach. Joining adjacent bad runs prevents late bulk deliveries or tick
  boundaries from erasing shortages.
- Capture buyer and seller at trade start and bind completion to the exact deal,
  following RML_Trade_Wares. Remove the persisted transfer guard before
  accounting to prevent duplicate credit. The former galaxy-scoped completion
  listener missed deliveries and is retained disabled for compatibility, not
  used for accounting.
- Subtract native reservations from advertised availability and defer offer
  rewrites during unloading. Pausing new reservations still accrues demand and
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
  name, rates and wares, and reset qualification. Target completion is distinct
  from completed-level module readiness. No downgrades are implemented.
- Required-module damage pauses demand and resets qualification on the
  one-minute controller tick, retaining a pending upgrade. Hub destruction
  preserves earned level, backlog and delivery totals but discards the upgrade;
  rebuilding accrues no demand. Builder replacement retries every five minutes
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
  save. Start leveling from a pre-prototype save. Uncounted deliveries/history
  cannot be recovered from visible offers. Reload of current leveling state
  refreshes names/diagnostics without resetting history or requeuing
  construction.

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

### Using the testing menu

With **kuertee UI Extensions**, right-click the
hub and open **Custom Actions → Civilian Economy — Testing**.

- Level/target, service state, qualification history and per-ware demand/cap,
  availability and reservations are displayed. Hover a ware for fulfillment,
  payments, supply/service scores, longest shortage and rate. Reopen to refresh
  the minute/event snapshot.
- **Force finish current construction** invokes the native workshop shortcut. It
  may bypass materials and time; never use it as evidence of ordinary construction.
- **Queue next upgrade — testing** bypasses qualification only. It still requires
  construction and does not grant goods, satisfaction or payment.
- **Pause new civilian reservations — testing** keeps accruing demand but offers
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
- `race.workforce.resources` maps to `food_<race>` baskets in `baskets.xml`:
  Argon uses food rations/medical supplies, Paranid soja husk/medical supplies,
  and Teladi nostrop oil/medical supplies. The Terran DLC supplies `food_terran`.
  These are native workforce-resource definitions; changing them has race-wide
  scope rather than per-sector control and needs consumption/sustain testing.
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
