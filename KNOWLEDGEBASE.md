## 2026-10-10 - english-source-0001

- IMPLEMENTED: English moved from `t/0001-l044.xml` to `t/0001.xml` (root
  `<language>`, no id), the convention for all mods using x4-modkit. Page/text ids
  are unchanged. Translation checks are `x4mod translations`; CE's own percent
  escape contract is `tests/mod/test_translation_escapes.py`.
- MEASURED: of 40 installed mods with a `t/` folder, 38 ship `0001.xml` (26 only
  that, 12 also `0001-l044.xml`) and 2 rely on `0001-l044.xml` alone; vanilla ships
  only `0001-l044.xml`. 24 of 26 full `0001.xml` files use `<language>` without id.
- UNVERIFIED: whether the engine falls back to `0001.xml` per missing entry in
  another locale. Coverage checks require every entry anyway.
- RISK: a manual (Nexus) install over an old folder keeps a stale
  `0001-l044.xml` beside the new `0001.xml`; which one English uses is unverified.
  Release notes should ask for a clean reinstall.

## 2026-10-10 - unrest-off-setting

- DESIGN: `CE_Settings.State.$Unrest` (default true; absent in older saves, so
  `Ensure`/`Read` treat it as on). Off keeps every record at 0 through one
  invariant: `CE_Unrest.AccrueInterval` calls `Clear` instead of accruing, and
  every accrual boundary (minute tick, deliveries, events, save load) passes there.
  The tax penalty, `Tick` incidents, raid lifecycle and debug unrest commands also
  check the setting directly, so a stale stage cannot act.
- `Clear` resets `$Eligible` and the per-ware deadlines. Re-enabling therefore
  starts the normal 2 h hub grace and 1 h per-ware grace instead of charging
  deprivation from while unrest was off. Cooldowns are kept.
- Switching off withdraws all raid groups of every hub, debug groups included,
  and expires all CE production pauses (`RestorePauses` lifts them within 1 s).
  Native `set_object_hacked` effects (max 10 min) and a module destruction already
  in progress cannot be cancelled and finish on their own.
- Snapshot slot 20 is `[]` while off. The Lua decoder ignores an empty payload, which
  hides the map row, tooltip line and debug unrest subgroup without separate checks.
- In-game acceptance (withdrawal, map row, tax restore message) is still open.

## 2026-10-06 - external-hubs-api

- IMPLEMENTED: `CE_ExternalHubs` lets another mod designate a civilian-owned station
  (god entry id or station object) as its sector's hub. See ARCHITECTURE.md "External
  hubs API" for the contract. Levels commit without construction; the station is never
  built on, renamed, funded for builds, given builders or replaced.
- READ (feasibility sweep): before this change every hub path assumed a CE-built
  `ce_hub_<race>` station. Readiness required CE plan entry IDs (`CheckReady`),
  `Queue` grafted `ce_hub_<race>` onto any civilian hub without a completed sequence,
  `AssignBuilder`/build funding reacted to any build in the station's build storage,
  the builder AI patch excluded every `$ce_hubs` member from native recruitment, and
  debug reset destroyed every civilian-owned registered hub. All are now guarded by
  `$R.$External`.
- READ: vanilla identifies god stations from MD with `find_station
  godstationentry=[...] multiple="1" space="player.galaxy"` (`md/setup.xml:1166`).
  `libraries.xsd` also offers god `<category tags>` / `godentrytags`, but nothing in
  vanilla or DLC uses it and custom tag names are unverified, so the API uses ids.
- READ: vanilla passes callback cues as values and signals them with
  `signal_cue_instantly cue="$Var"` (`md/cinematiccamera.xml:989`); the cue datatype
  has `exists` (`scriptproperties.xml:2195`). Cross-extension calls use `check="false"`
  (`ego_dlc_mini_02/md/setup_dlc_mini_02.xml:102`). Vanilla god.xml places
  civilian-owned stations from construction plans (`god.xml:2726`).
- MOCKED (19 tests in `tests/mod/test_external_hubs.py` + reset and Lua cases):
  adoption before Init, idempotent re-registration, rejections, max level, damage
  status, dormant loss and re-adoption, debug paths, raid berth fitting. Mutation
  checks: removing the `Queue`, `AssignBuilder`, build-funding, rename/reconcile and
  dormant guards each fails a test.
- MEASURED: `just sample-validate --update` on `samples/client-mod` reports no issues
  (god.xml selector, plan/macro references, MD and merged god.xml schemas).
- MEASURED (debug.txt, 2026-10-06, sample added to an existing 9.00 save at game time
  238523): registration -> `ExternalHubsChanged` -> `find_station godstationentry` ->
  `rejected`/`not_found` event -> client listener all ran within the same second, and
  the sample's plan/god diffs loaded without errors. The god entry was NOT placed in
  the existing save by then (nothing named `ce_sample_client_hub`). Whether god places
  it later is unmeasured (CE retries every reconcile); test placement on a new game.
- MEASURED (debug.txt, 2026-10-06, new game `custom_creative`): god placed the sample
  station; at game time 1.03 it was registered, adopted (`modules=1`), funded
  (7,232,600 Cr) and operational (`status active`) before CE's first population reply
  created the 36 ordinary hubs at 2.03. Debug advance at 37.32 committed level 1 -> 3
  without construction and emitted `level`; destroying the station at 64.34 emitted
  `lost` (level 3 retained). So the one-entry god plan, its `constructionsequence`
  entry IDs and `planmodule` readiness all work in-game. Log ended at 66 s: the
  no-rebuild check needs a reconcile after about 5 minutes of game time.
- MEASURED (same game, log to 434 s): the reconcile at 301.32 created no station in the
  dormant sector (all 36 construction sites date from 2.03). The minute tick at 121.05
  sent a redundant `status hub_unavailable, station=null` after `lost`; NotifyStatus now
  stays silent for dormant records (regression test added), not yet re-run in game.
- UNVERIFIED IN GAME (remaining): re-adoption of a respawned station; traders delivering to a single M
  dock; the level-up notification text (450-452); `remove_trade_offer` on debug reset.

## 2026-09-30 - sector-rewards-reintegration

- The 2026-09-23 sector rewards work (commit `97ab3ac` on the deleted branch
  `codex/sector-rewards`) was never merged. It was recovered via the reflog,
  pinned as `recovered/sector-rewards`, and cherry-picked onto main.
- SUPERSEDES the 09-23 entries below on these points: the snapshot stays at
  version 3 and the reward payload is position 23 (not v4/position 17); hub
  records are owned by `faction.civilian`, so reward eligibility checks that owner
  and price/radar partners exclude ownerless and civilian-owned stations; reward
  text IDs moved from 140-173 to 400-433 because main reused 140-159 for settings
  and debug text; all 16 locales carry the reward keys; the unlock logbook text
  (419) uses MD `%1`/`%2` placeholders like the other MD-formatted keys.
- UI: main's summary layout (population, level bar, next level, status/unrest
  rows) is kept. Row 5 now shows warnings/unrest on the left and the bonus summary
  on the right; the Supplies/Bonuses buttons are fixed row 6 with `rowdata=true`
  (the native validator requires row data for active buttons). Demand events and
  the active view scroll below. The 09-23 compact-header and `+25% demand` text
  changes were not carried over.
- `tools/check.py --schema` now validates every diff-rooted MD file (currently
  `md/diplomacy.xml`) with the same patch applier as the AI diffs.
- Trade price value reads `N% of price range` (was `N modifier points`). READ:
  `common.xsd` `pricemodifieramount` is a percentage of the ware's price variation
  range, so the effective share of the current price varies per ware.
- Diplomacy value reads `+N% success chance` (was `+N success points`). READ:
  vanilla `Success_Evaluation` sums base, agent (+10 per experience level) and
  bribe chances in percentage points, caps at 99, and succeeds when a seeded 1-100
  roll is below it, so one CE point is one percentage point relative to vanilla.
  The hint states the 99% cap.
- MEASURED (debug.txt, 1468 px view, temporary `[CE] MapLayout` logging): the
  Bonuses view lifted the bottom-anchored panel because Helper estimated all five
  bonus rows at 49 px (two lines) while only one wraps on screen. Per-cell logs
  showed the last (status) column measured at 158 px, wrapping "Unlocks at level N"
  in the estimate only. Helper sizes the last column without the reserved
  scrollbar space; a narrow wrapped last column therefore over-estimates height.
  Fix: columns 1-2 stay 44% in both views (tabs no longer shift), bonus name spans
  1-2, benefit 3-4, status column 5 at about 26% of the width. Lua regression
  asserts the status width. In-game re-check pending.
- READ (helper.lua createDescriptor ~5040-5070): with `reserveScrollBar=true` and
  no scrollbar needed, Helper widens the variable last column at descriptor
  creation, after our draw measured heights. That is why the estimate used 158 px.
- READ (widget_fullscreen.lua drawTableSection ~6102, table setup ~14524): a
  scrolling table draws whole rows only, starting at the first non-fixed row, and
  keeps min(cap, max(drawn, minimum)) as its height. Helper's getVisibleHeight()
  returns the full cap, so a bottom-anchored scrolling panel sat up to one row too
  high (user observed about one line on a level 10 hub).
- Fix: `renderedHeight` in ce_map_status.lua mirrors that rule for anchoring, and
  the table uses `reserveScrollBar=false`. A mutation check (anchoring on
  getVisibleHeight again) fails the Lua regression. In-game re-check pending.
- User-confirmed in-game: level 1 and level 10 hubs keep a stable bottom edge in
  both tabs after the renderedHeight fix.
- Demand events now sit above the tabs (user request). This PARTLY SUPERSEDES the
  2026-09-27 concurrent-sector-events rule that events always scroll: they are
  fixed above the tabs only while a height budget fits (`eventLayout`), and fall
  back to scrolling below the tabs otherwise. Up to seven events can be active
  (one per demand group). Lua tests cover both layouts, including the 720 px
  fallback with seven events. In-game check pending.
- Runtime acceptance from the 09-23 entries is still outstanding.

## 2026-09-29 - layout-snapshot-refresh

- READ: saved `$Construction` snapshots (`Init.$RaceProfiles`, `$R.$Construction`)
  expect exact per-level macro lists, but plan IDs (`ce_hub_<race>`) stay stable
  across mod versions while `libraries/constructionplans.xml` is re-read each game
  start. Before this fix nothing re-resolved a snapshot once definitions existed,
  and `$LayoutFingerprint` was written but never read.
- MOCKED (control test): with a stale snapshot, a replacement hub loads the new
  plan by ID and fails `stage_macro_mismatch` on every 5-minute retry. Geometry-only
  plan changes (same macros/counts) never failed; macro or count changes did.
- A failed FIRST load also kept the rejected master in `$R.$FullSequence`, so
  retries reused it instead of reloading the plan. Now cleared while `$PlanIDs`
  is empty.
- IMPLEMENTED: snapshots carry `$Fingerprint`. `CE_Construction.RefreshSnapshots`
  runs on save load: stale or invalid race/debug snapshots re-resolve once per race.
  "Committed" = `$PlanIDs` non-empty or a live build: such records keep their
  snapshot, which matches their saved native master. Uncommitted records and every
  lost hub (`ForgetHub`) adopt the current profile snapshot via `AdoptSnapshot`.
  Invalid races are retried each load, so a DLC or adapter installed later recovers.
- Committed records whose snapshot is unstamped/stale but has the same plan ID
  and identical per-level macro lists (`MatchSnapshot`) are re-stamped in place;
  their master and IDs are untouched. Only genuinely different layouts log
  `Hub keeps its saved construction layout`, on every load while the hub stands.
- Tool: `generate_plans.py` hashed generator sources as raw bytes, so a CRLF
  checkout (`core.autocrlf=true`) made `just plans-verify` report STALE with
  identical geometry. Hashes now normalize CRLF; artifacts regenerated, only the
  fingerprint changed.
- UNVERIFIED in-game: that the engine re-reads a changed plan behind an unchanged
  ID on save load (expected, library data loads at game start).

## 2026-09-28 - civilian-hub-current-state-only

- The controller is `CE_CivilianHub` (`md/ce_civilian_hub.xml`). Older mod saves
  are explicitly unsupported; test from a save that never loaded the mod.
- Removed ownership repair, singular demand-event migration, old event UI decoding,
  hub-keyed raid conversion, old announcement-flag repair and obsolete aliases.
- Failed partial raid launches are CURRENT behavior, not legacy saves. Their
  explicit `launching` phase routes to safe cleanup; prepared raids retain their
  lifecycle, pilot AI markers, and current-version save/load continuity.
- Genuine `faction.ownerless` funding and native faction checks remain unchanged.
- VALIDATED: `just validate` passes 274 controller tests and static references;
  `just lua`, `just test-tooling` (14 tests), translations (249 entries in each
  of 16 locales), and `just schema-only` pass. All six merged AI patches have
  no introduced schema errors.
- SUPERSEDED 2026-09-29: `just check` stopped at stale generated construction
  fingerprints; the cause was CRLF hashing (see layout-snapshot-refresh).
- Historical entries below describe earlier implementations, not compatibility
  guarantees. Full restart required; native acceptance remains unverified.

# Mod-local Knowledgebase

## 2026-09-28 - measured fit and native staged expansion revision

- MEASURED diagnostic smoke, token 1, game time 241625.87-241628.44,
  fingerprint `cbea8c9f618be334d35cd685c1fad754f61ce0dc9a7085adb430acbede086844`:
  finished with six failed races, two successful level checks and no bulk or
  docking runs. Calibration yielded 55 distinct native module AABBs across all
  six races; the imported numeric fixture records the log hash. Saved first-entry
  IDs changed from Boron `0x2175` to `0x2183` and Terran `0x26cc` to `0x26da`
  when loading the level-2 named plan. All 14 prior IDs were absent for each race.
- READ: vanilla constructionplans.xml `arg_advancedcomposites_prefab_04` uses
  `bookmark="1"` at entries 15, 23 and 37, with an unmarked final tail. Vanilla
  factionlogic.xml and factionlogic_economy.xml expand prefab stations using
  their existing sequence's `finalsequence` and an incremented stage number.
- IMPLEMENTED: CE now uses a bookmarked master plan per race and retains one
  native sequence per site. Stage boundaries, current stage and entry IDs are
  checked before construction; readiness uses only the active prefix. Future
  operational modules fail acceptance. This follows the native source pattern;
  successful CE stage expansion is still pending the next smoke run.
- MEASURED offline from imported native bounds: all six fitted layouts satisfy
  a 50 m plot margin and 50 m conservative functional-AABB separation in 10 km
  cubes at all ten levels. Deck spacing now varies by racial fit; a single
  extra downward connector at Split level 6 separates storage from the pier.
  These checks do not establish connector collision or approach clearance.
  Existing production layouts and selected functional capacity tiers are unchanged.
- MEASURED validation: fitted generation is reproducible; all 27 focused tests
  pass. `just validate` and `just schema` each pass 310 repository tests, with
  no introduced MD or merged AI schema errors. Lua and 264 translation keys
  in all 16 languages pass. Full restart and a new native smoke run are required;
  the revised native stage/geometry acceptance is not yet measured.

## 2026-09-28 - first connector-spine native smoke and diagnostic revision

- MEASURED in debug.txt, token 1, game time 242352.55-242356.31, template
  `39cc7d0870d040bab1fa89faea68c735f4c201b19b5a55f88cc5db2141c9f175`:
  all six smoke cases failed, two level checks passed, zero bulk/sample/docking
  cases ran. Argon/Teladi level-1 pier bounds reached x=6188.5 m; Paranid
  x=5788.5 m; Split x=5095.2 m, beyond the +5000 m plot edge. Boron/Terran
  level 1 became operational, then level-2 sequence validation failed before
  bounds checking. Their exact mismatch was not logged and remains unresolved.
- READ: the initial generator centres module origins, not full native bounds,
  and uses fixed branch lengths. Its static passes never established containment
  of full modules. New native calibration exports all selected level-10 macros,
  regardless of how early construction fails. Geometry dimensions/partial corner
  logs from the first run cannot reconstruct a complete native bounds catalogue.
- IMPLEMENTED: finite deterministic fitting from measured AABBs, immutable
  cumulative centring, exact native sequence diagnostics, independent ID/transform
  snapshots, and a smoke-only action with explicit passed/failed/skipped summary.
  Fitting uses conservative functional AABB separation and assumed 50 m margins;
  it does not validate connector collisions or docking approach volumes.
- PENDING: run the diagnostic smoke after a full restart, import its complete
  calibration, regenerate fitted plans, and diagnose native expansion identities.
  No fitted layout or revised native smoke result is claimed yet. The first
  failing geometry remains provisional until measured input is available.
- MEASURED revision checks: `just spine-check` passes 24 focused tests;
  `just validate` and `just schema` pass 307 repository tests with no introduced
  schema errors, including merged AI patches. `just lua` and `just translations`
  pass; all 16 locales contain the same 264 keys. These checks do not resolve
  the native geometry or expansion failures described above.

## 2026-09-28 - connector-spine prototype

- READ: native Boron and Split cross junctions have three horizontal arms, not
  four orthogonal arms. Boron, Paranid, Split, Terran and Teladi storage examples
  attach vertically; a universal horizontal attachment rule fails on their snaps.
  Snap names are case-normalized in native plans. IMPLEMENTED: this prototype
  also enforces matching tangent/up directions on `snap_aligned` ports, not just
  coincident positions/opposing normals; native attachment remains a runtime gate.
- IMPLEMENTED: isolated CE_SpineExperiment plans use three branches per deck,
  actual racial snap transforms, larger capacity tiers at levels 4 and 7, and
  immutable cumulative entry prefixes. Their source is base+DLC reference XML,
  not an installed effective-tree merge. Runtime availability, native bounds,
  identities, construction and docking are separate acceptance gates.
- MEASURED: the six generated racial plan sets pass static snap/graph/origin
  checks at all 60 levels. Level-10 total entries including connectors are Argon
  98, Boron 84, Paranid 89, Split 84, Terran 85 and Teladi 98. These figures do
  not establish mesh clearance, actual native loading, construction or docking.
- READ: construction-plan entry pseudo-values expose IDs/macros but not geometry.
  The experiment validates generated XML transforms statically, uses native
  macro bounding boxes for plot containment, and logs actual built module
  transforms/dimensions. Mocked lifecycle tests are not engine measurements.
- HISTORICAL pre-smoke status: the new 600-site experiment had not yet run. The earlier
  600/600 native result below belongs to the previous randomized forward planner
  and must not be attributed to this connector-spine prototype.
- MEASURED: `just spine-check` passes reproducibility plus 17 focused tests;
  `just validate` and `just schema` each pass all 300 repository tests. Native
  schemas report no introduced errors, including the separately merged AI
  patches. `just lua` and `just translations` pass, with 261 keys in each of
  16 locales. Native runtime acceptance remains pending a restarted scratch save.

### 2026-09-28 - status-only-level-tooltip

- The level-progress tooltip is composed by `CEHubStatus.progressHint`, not by
  concatenating progress, state and action prose. It labels accrued growth as
  supplied time, lists each missing ware once, and omits general instructions.
- Construction and earned upgrades omit the supplied-time counter. Stale or
  failed-demand-refresh warnings replace details rather than presenting retained
  snapshots as a current growth status. Snapshot format and simulation are unchanged.

## Station planning and reset

- MEASURED (2026-09-27): forward planning passed 600/600 fresh 10 km cubic
  sites, 100 each Argon, Split, Boron, Paranid, Terran and Teladi. All 6,000
  native requests succeeded without retries. This validates plans, not actual
  construction or ship docking, and is not a guarantee for every random seed.
- Native removal from a construction sequence can also remove descendants.
  Backward pruning lost required modules; build cumulative plans forward instead.
  Validate exact module baskets, allowed connectors and retained entry IDs/macros.
  Store all ten plans before constructing a fresh hub; retry extensions on the
  same base and discard incomplete candidates.
- Pier discovery must include both base and add categories. A base-only filter
  excluded single-approach piers. Approach exclusion volumes, not visible module
  size alone, constrain placement. Selection does not fix pier orientations.
- Native constructionsequence may be null; check before reading count.
  Check cue.exists before cancellation. Repeating native callback listeners
  inherit their parent namespace so each result advances the same planner.
- Full debug reset clears CE records and cached profiles, removes only tracked
  CE-owned objects, and reinitializes from current population/ownership. Settings
  and player finances survive. Removal is asynchronous: retain identities until
  gone, protect docked visitors, and never recreate hubs during cleanup.
- Native finalisestations.xml constructs finished modules with
  apply_construction_sequence. CE uses this only for exact first-generation hubs
  authorized during first initialization or debug reset, after all ten plans
  validate. Permission survives planning retries but is consumed on application
  or hub loss. Replacements/upgrades and pre-existing saves use normal builds.
- MEASURED (2026-09-28): native station creation can immediately create empty
  build storage. Initial completion must allow idle storage while excluding active
  build tasks. Unfinished docking bays can lack `.docked`; treat that as no visitors.
- Native build storage can emit `event_object_built_station` on an instant hub's
  first later upgrade. Skip duplicate native initialization only for registered CE
  hubs with an existing trade NPC. MD helpers called across scripts must qualify
  nested `include_actions` references; unqualified names resolve in the caller.
- MD formatted notification text requires `%%` for a literal percent sign, including
  after numbered placeholders (`%4%%`). Unformatted UI labels need no such escaping.
- Native TextDB dynamic IDs require a constructed reference string; drop_cargo
  amounts output requires the wares output attribute too.

## 2026-09-27 - hacking-surveillance-broadcast

- IMPLEMENTED: CE_Sabotage.Apply selects ce_news_hacking for successful production,
  turret, shield and cargo incidents. DestroyModule.Confirm retains ce_news_sabotage
  only after confirmed wreck/removal. Incident details and localized captions are
  unchanged; both clips reuse the existing English sabotage headline (292).
- IMPLEMENTED: station-hacking.png and its generation prompt live in images/broadcast.
  The encoder builds the third clip with the existing red scrolling strip, and the
  release archive allowlist explicitly includes videos/ce_news_hacking.mkv.
- MEASURED: the hacking clip fully decodes to 288 H.264/yuv420p frames, 1280x720,
  24 fps, 12 seconds. Rendered frame visually inspected. Playback in game remains
  unverified. Full game restart required for changed MD and new cutscene assets.
- TESTED: just validate passed 248 controller tests, native cutscene schema checks,
  XML parsing and the default x4validate pass. just test-release passed 62 tests,
  including archive inclusion of the new clip. Full script schema compilation was
  not run for the single changed cutscene-key value.

## 2026-09-28 - manifest-dependency-audit

- READ: installed manifests identify `ws_2042901274` as `Mod Support APIs`,
  `kuerteeUIExtensionsAndHUD` as `kuertee UI Extensions and HUD`, and
  `VerboseTransactionLog` as `Mycu: Verbose Transaction Log`.
- READ: `CE_Options` directly references `md.Simple_Menu_API`; UIX debug actions
  and receipt details guard callback availability, while VTL receipt updates
  check extension enablement and its data contract. The manifest declares the
  first required and the latter two optional, with their installed display names.

## 2026-09-27 - complete-language-coverage

- IMPLEMENTED (2026-09-28): `content.xml` uses SCV's 16-language `text`
  entry pattern for extension descriptions, separately from the runtime `t/`
  strings. Keep language 44 identical to the root English description.
- READ: `reference/t` contains 16 locale files. The matching SCV set is
  7, 33, 34, 39, 42, 44, 48, 49, 55, 81, 82, 86, 88, 90, 359, 380. The reference
  language registry enables 13: Turkish/Ukrainian are commented out and Bulgarian
  is absent. Providing text does not enable a game language.
- IMPLEMENTED: CE keeps `t/0001-l044.xml` as its single English source and ships
  15 additional locales. SUPERSEDED 2026-10-10: English moved to `t/0001.xml`. This supersedes older English-only notes below. All
  translations were authored within Codex from the gameplay context.
- TESTED: `just translations` covers 229 entries per locale and 22 regressions,
  including missing files, multiple pages, duplicates, empty text, language IDs,
  parentheses and formatting. Lua format argument order must match English;
  numbered MD arguments may be reordered but not lost or duplicated. Coverage
  cannot establish linguistic quality or in-game layout fit.
- TESTED: `just validate` passed 234 controller tests, XML parsing and x4validate
  with no reported issues; `just lua` passed the debug menu, population bridge
  and map status suites. No MD/AI changes were made, so the optional full script
  schema compilation was not requested.
- READ: `ui/ce_hub_status.lua` divides population by 1e6, 1e9 and 1e12 for
  text IDs 73-75. Localized unit labels must retain those magnitudes; changing
  a billion label to a hundred-million label without changing the value is wrong.
- READ: news videos bake English IDs 291-292/296 into their images. The localized
  runtime captions and log/ticker messages do not change those rendered headlines.
  Full game restart required for new text files.

## 2026-09-27 - nested-debug-controls

- READ: installed UI Extensions documents `insertInteractionGroup(parentId,
  groupId, text)` inside `prepareSections_on_end`; repeat group insertion on every
  menu opening because the action tables are rebuilt. Only the root uses
  `Add_Custom_Actions_Group` at registration.
- IMPLEMENTED: diagnostics stay at the debug root. Construction/level, wares and
  unrest controls occupy nested groups, with one subgroup per positive-rate ware.
  Random stock sets virtual reserves between the accrued current balance and the
  two-hour target; zero empties them. Neither action records delivery or payment.
- IMPLEMENTED: ware and one-hour growth-progress commands share the existing
  MD-owned unrest token to reject stale/replayed requests. Consumption is settled
  before mutation; progress is capped at the current requirement. In-game menu
  navigation and command behavior still require verification.
- TESTED: `just lua` and `just schema` passed, including 218 controller tests,
  random-reserve bounds, selected-ware isolation, replay rejection, progress caps,
  subgroup placement and native schema checks. The test runtime samples random
  ranges deterministically; it does not simulate the engine's random distribution.

## 2026-09-26 - broadcast-interaction-and-station-conversation-research

- READ: CE_UnrestNotifications.Broadcast explicitly supplies the cutscene
  interaction; OpenBroadcast stops event.param3 and opens the incident object
  (or surviving sector) on the map. It does not currently call an NPC.
- READ: reference/libraries/common.xsd:31139 makes play_cutscene/interaction
  optional. Its silent attribute suppresses flashing only (7598 onward), and
  abortable is ignored for target-monitor cutscenes. Omitting interaction is
  the source-supported approach to a passive broadcast; prompt disappearance
  remains UNMEASURED in game.
- READ: reference/md/notifications.xml:2906 and 2953-2963 provide the vanilla
  handoff: interactive monitor cutscene, stop_cutscene, then start_conversation
  actor=... conversation=... convparam=... type="unqueued". The same file at
  3021 supplies a target-monitor cutscene without interaction.
- PROPOSED, not implemented: sabotage can pass an incident snapshot to a custom
  conversation with the station manager, offering damage details, map and goodbye.
  Current payload contains only object/sector, so details must be added. Recheck
  station/manager existence when clicked; queued video may outlive either.
  Native add_npc_line uses page/line voice data, not a free-form text attribute;
  dynamic report presentation and custom voice/subtitle behavior need testing.

## 2026-09-26 - production-broadcasts-and-left-ticker

- IMPLEMENTED: every raid/sabotage Broadcast submits the full IncidentText to the
  left message ticker for 12 seconds and logs it once. The right target monitor
  plays the approved red scrolling news video with a short native caption.
  Null cutscene IDs fall back to the interactive alert without another ticker/log.
- IMPLEMENTED: attack details distinguish production, turret and shield sabotage,
  cargo ejection and module destruction. Native component.module supplies the
  containing module for affected turret/shield equipment (scriptproperties.xml).
  Destruction captures station/module names before removal, then reports only
  confirmed destruction. Raids identify their source hub, sector, tier and fleet.
- IMPLEMENTED: removed the dedicated video experiment, test/preview menu actions,
  playback diagnostic logs, synthetic assets, experiment strings and comparison
  generator mode. Real incident debug actions remain available.
- USER-APPROVED: images/broadcast/ supplies the two production artworks. The
  generator (just news-videos) fits the whole image above an 84px red banner;
  bold white text (English IDs 291-292,296) scrolls left at 110px/sec.
- MEASURED: production clips decode to 288 H.264/yuv420p frames, 1280x720 at 24fps,
  12 seconds. Their frames matched the approved MP4 comparisons before cleanup.
- READ: play_cutscene supports caption/interaction but no general body text,
  dynamic image or priority parameter. Video references omit the MKV suffix.
  Native queuing can delay the right monitor independently of the left ticker.
- READ: old Announced also guarded raid lifetime and failed-departure cooldown
  refunds. CombatStarted now owns those duties; Announced deduplicates departure
  warnings. Old v2 state migrates from the prior flag to preserve active deadlines.
- USER-VERIFIED: the earlier native-video experiment played in-game. Its caption
  showed a missing-glyph box for an em dash; use ASCII hyphens in game strings.
- UNMEASURED IN GAME: final incident ticker readability, production video queuing
  and module detail display. Full restart is required for changed MD/text assets.
- READ: the installed extension is a junction to this workspace; no copy needed.
- VALIDATED: cleanup passes 213 controller tests, native MD/cutscene and merged
  AI schema checks, Lua checks and release tests. Rebuilt ZIP contains only the
  two production videos, byte-identical to the workspace assets.

## 2026-09-26 - trade-and-fixture-extraction

- SOURCE: `CE_Accounts` owns funding and manager provisioning;
  `CE_TransactionLog` owns optional seller-payment requests, tax labels and
  receipt publication. Both contain synchronous libraries only. Existing
  controller/trade entry points and `CE_Trade.WatchDeliveryPayment` plus its
  child cue identities, conditions, captured `$Payment` and cancellation remain.
- MEASURED: expanding the new include-actions calls and comparing XML element
  names, attributes, text and order reproduces the pre-refactor `CE_Trade`
  tree exactly (comments/formatting excluded). All other existing MD files are
  byte-identical. The ownership and raid review findings remain intentionally
  unaddressed at the user's request.
- SOURCE: construction, startup, unrest and sales-tax fixtures now live in
  focused `tests/support_*.py` modules. Release/archive tests share
  `test/release_support.py`; no suite imports another suite. Lifecycle tests
  exercise real funding/manager libraries with only native effects mocked.
- MOCKED: all 205 MD tests, Lua checks, 60 release-tooling tests and the installed
  VTL integration test pass after extraction. Native save/load remains an
  in-game acceptance boundary; full restart is required for the MD extraction.
- VALIDATED: `just schema` reports no issues, including all six merged AI
  patches. A subsequent static pass without the backup in the mod also passes.
  Keep XML baselines outside the mod: the validator included the ignored
  `.snapshots` backup in its reference inventory (98 payload files with this
  backup, 79 after moving it out), although schema checks target live scripts.

## 2026-09-25 - review-ownership-and-raid-lifecycle

- MOCKED, not in-game verified: executing `UpdateHub` with the existing
  `LifecycleTests` fixture after changing hub ownership to player sets
  `PauseReason=owner_changed` but still invokes `FundAccounts`. SOURCE:
  the non-ready branch only checks existence/wreck status before funding;
  `CE_Trade.FundAccounts` has no ownerless guard for either station account.
- MOCKED: a version-2 raid whose ship loses its pilot enters withdrawing but
  remains registered after repeated lifecycle ticks at age 10000. SOURCE:
  `CE_RaidBehaviour.Withdraw` places both departure and eventual destruction
  inside the pilot-present guard. Such a surviving ship retains its group slot.
- MOCKED: replacing a version-2 raider's pilot after departure leaves the new
  pilot without CE version/sector markers on the next tick. SOURCE: marker
  initialization is in Prepare; the legacy lifecycle repair does not run for
  version-2 groups. AI guards require those markers. The frequency and native
  circumstances of pilot replacement/loss remain unmeasured.
- Review only: these runtime paths were not changed. Reproductions used the
  shipped MD action interpreter and existing fixtures with native effects mocked.

## 2026-09-25 - release-runtime-selection

- SOURCE: SCV's release archive whitelist covers UI Lua, MD and translations;
  CE also requires XML under `aiscripts`, `assets`, `index` and `libraries`.
  CE's shared archive selector includes these and nested `extensions` XML so
  local builds and tagged reconstruction use the same runtime membership.
- SOURCE: the first release suggests the next minor version from the existing
  manifest when no release tags exist. Do not pre-create `VERSION`: SCV's
  inherited history guard rejects a VERSION file without a matching release tag.
- SOURCE: release receipts and the Nexus file binding live in ignored
  `dist/nexus/`; preserving them matters for safe resumption after uncertain
  network responses. The released manual is read from its Git commit, not from
  later edits in the working tree.

## 2026-09-25 - capital-drone-capacity-aborts-launch

- MEASURED IN GAME: debug.txt at 241496.72 records `raid_3` at hub 0x4acfe,
  followed by cargo-drone provisioning failure on ship 0x1a7f38 with count 1.
  There is no departure-accepted or piracy-started transition for that launch.
  Failure precedes CE ownership/fleet setup; partial ships use weapons-held
  withdrawal. This explains the reported neutral, ungrouped, non-fighting ships
  in this failed test, rather than proving active piracy or scanning is broken.
- SOURCE: the Argon L destroyer has ten drone slots; a read-only merge of the
  currently active installed mods also returns ten, with no ship-macro override.
  Unrestricted generated
  loadouts may fill that shared bay before mandatory cargo drones are added.
  `generate_loadout flags="units" invertflags="true"` excludes ordinary drones;
  `drones` is a separate flag for ability drones. Capital equipment now excludes
  ordinary drones, then adds and verifies the required five cargo drones.
- LIMIT: the old log did not record the other drones or free capacity, so the
  exact loadout occupancy in that run remains unmeasured. New diagnostics record
  capacity, total units, free slots and cargo drones, plus partial-launch aborts.
- MOCKED: finite ten-slot bay reproduces the one-cargo-drone result with nine
  pre-existing other drones. The revised launch reaches seven CE-owned ships,
  an L-led fleet, armed piracy and one popup after departure. The former mock
  incorrectly treated add_units as unbounded and apply_loadout as a no-op.


## 2026-09-25 - native-station-retaliation-restored

- User removed the never-fight-stations requirement. Removed four combat weapon
  patches, the CE station handler/helper, AttackHandler exclusion and four
  handler-only movement/order patches; removed the handler from Plunder/Attack.
  Raid AI now consists of five native-script patches and no custom AI helper.
- Native combat, station retaliation and turret targeting are restored. MD still
  supplies Plunder mode 0 (ship robbery), preserves 3:1 eligible-player weighting,
  and manages departure, lifetime, caps, withdrawal and sector replanning.
- Attack's phase/sector guard remains, without target-class restrictions. Old
  station avoidance markers are ignored and removed during capture cleanup if
  present. No station-triggered disarm/regroup remains.
- This supersedes the strict station protection described in earlier entries and
  removes the event-payload error source entirely. The blocking-action version
  fixes below remain necessary. Full restart and older-save retest required.
- VALIDATED: focused raid tests and just schema pass, including merged AI patches.
  In-game combat and old-save resume recovery remain acceptance checks.

## 2026-09-25 - raid-ai-event-and-resume-errors

- MEASURED: live debug.txt reports repeated event.param.isclass failures in
  MoveWait, Wait and Plunder from CE's AttackHandler exclusion. CE prepended the
  payload check before native event matching; unrelated signals can carry strings
  or lists. Move the guard after the native event check_any and use optional
  station/container lookups. The dedicated CE handler also guards its payload.
- MEASURED: on loading at 241481.02, ordinary combat pilots report fighter,
  bigtarget and capital-steering returns being assigned to $movesuccess, although
  the installed merged Attack script assigns that result only to move.generic.
  Movement also resumes with missing/invalid $safepos. This precedes the new CE
  raid launch at 241739.37.
- SOURCE-VERIFIED defect / INFERRED cause of these resume errors: CE inserted
  five blocking waits without sinceversion markers or script-version increments.
  Egosoft aiscripts.xsd defines sinceversion on blocking actions, and native
  move.generic uses it for added waits. Version the new waits at MoveGeneric 24,
  Attack 28 and Plunder 7. This targets older pre-CE saves; saves already written
  with misaligned execution state are not proven recoverable by these markers.
- Installed merge inspection found no skipped sources: Attack also has fs_pat,
  MoveGeneric galaxy_trader, and AttackHandler kuertee_friendly_fire_tweaks and
  pirate DLC. These fixes do not rewrite other mods or mask missing return values.
- Regression checks cover native station combat eligibility, phase/sector guards
  and new-wait versioning. Native resume recovery still needs a full-restart test on an older
  save; mocks do not implement the engine's saved execution stack.

## 2026-09-25 - native-cutlass-live-comparison

- CLOSED: user abandoned the cutlass investigation. Removed ce_raid_status.lua,
  its addon registration and diagnostic-only tests. No CE map-list substitute
  or selected-ship diagnostic hook remains; native raid AI is unchanged. The
  observations below are retained as investigation history, not pending tests.

- ALLEGIANCE COMPARISON at 242280.22: CE 35409935 and newly selected vanilla
  pirate 626612 both have reveal=100, commands unlocked, started/enabled default
  Plunder and no queued orders. CE is enemy/hostile, not ally; vanilla is covered
  as Paranid and is ally, not enemy/hostile. User reports the vanilla cutlass.
  Native MapMenu distinguishes allied order rendering (SetMapRenderAllAllyOrderQueues)
  from player orders. Allied disclosure is now the leading explanation, not
  inactive Plunder or missing scanning. The exact native marker-renderer condition
  is not exposed in Lua, so this correlation is not a proven hostile-icon rule.
  Do not alter CE allegiance/disguises or AI merely to force an icon.

- FOLLOW-UP MEASURED: at 242136.61/242183.55, scanned CE commander 35409935
  has revealpercent=100, operator_commands=true, active/enabled default Plunder
  and no queued order. User still sees no cutlass. Scanning is NOT sufficient;
  the earlier information-disclosure hypothesis is unconfirmed and must not be
  presented as a fix. Installed effective Plunder order definition/icon mapping
  is unchanged; saved map order/allied-order toggles are both false. Diagnostics
  now include native isally/isenemy/ishostile to compare apparent ownership rather
  than infer allegiance from Argon disguise. Root cause remains unresolved.

- MEASURED in debug.txt at 241793.10 and 241832.74: CE commander 1775577 and
  vanilla pirate 422663 both have default Plunder, state started, enabled true,
  no queued orders and no commander. CE revealpercent=0/operator_commands=false;
  vanilla revealpercent=100/operator_commands=true (covered as Argon).
- Native infounlocklist.xml sets operator_commands at 80 percent. Information
  disclosure is the leading explanation for the missing native cutlass, not a
  proven rendering cause yet. Next acceptance step is normally scanning the CE
  commander, selecting it again and comparing icon plus diagnostic visibility.
  Do not force global information unlocks or change Plunder to test this theory.
- MEASURED: GetNPCBlackboard returns CE combat/withdraw booleans as 1/0 in this
  session. Lua consumers must accept numeric boolean values (not only true/false).
- Separate log error: installed Assailer Sector Patrol 1.11 (fs_pat),
  aiscripts/sectorpatrol.xml:20 uses location condition $fs_space.zone.exists,
  although fs_space is a required sector parameter defaulting to null. Invalid
  parameter causes repeated UI order-location errors; no CE source owns this code.

## 2026-09-25 - native-cutlass-diagnostic

- User means the native cutlass beside the ship marker, not a map-list name icon.
  Removed CE's list decoration. Native parameters.xml holomap/orders/icons uses
  prefix order_; icons.xml defines order_plunder and MapMenu's legend lists it.
  Vanilla SCA jobs and CE both configure Plunder as the default order. The native
  marker's missing-display cause is NOT established; do not infer engine inability
  from getOrderInfo's separate Lua object-list ownership guard.
- ce_raid_status.lua now only logs selected ship data with CE debug enabled:
  owner/pilot/commander, scan reveal and operator_commands access, default/current
  orders and state, CE phase markers. One-second checks, unchanged-state suppression,
  max 30 records per map session; no orders, map settings or rendering are changed.
- To compare live CE and vanilla pirates, reload UI and select each on the map;
  inspect [CE] Native raid icon lines in debug.txt. Native result remains pending.

## 2026-09-25 - raid-map-activity-icon

- SOURCE-VERIFIED: native MapMenu.getOrderInfo returns empty order icons for
  non-player-owned ships. Running Plunder does not automatically expose its icon.
- CE decorates getContainerNameAndColors with the native order_plunder inline
  icon and localized ReadText(1041,231) tooltip. Requires live, name-unlocked CE
  ownership, pilot behavior version 2, combat enabled, no withdrawal, and enabled
  default Plunder. Escorts, departure/regroup and captured ships do not qualify.
- Indicator describes the active piracy behavior, including pursuit/collection,
  rather than the instant of issuing a cargo demand. No simulation names or orders
  are changed. Rendering still needs native in-game acceptance.
- Native object-list refresh runs every two seconds, so phase/order changes are
  re-read without a CE polling loop. MOCKED: LuaJIT checks phase transitions,
  capture/privacy guards, tooltip formatting and idempotent deferred registration.

## 2026-09-25 - predictable-sector-local-raids

- SOURCE: native `order.plunder` builds a valuable-cargo table using the smartchip
  price threshold and excludes minable wares; CE now scopes the replacement to
  container cargo. `move.seekenemies` already exempts `player.occupiedship` from
  purpose restrictions, but CE's former post-filter removed that exception.
- SOURCE: capital Plunder signals resupply when transport drones are missing.
  CE provisions and verifies five Argon cargo drones before accepting a new
  capital group (`add_units` otherwise defaults to the temporary hub owner).
  This is a plausible contributor to the reported docked destroyers, not a
  proven explanation of those particular ships' live orders.
- SOURCE: `move.generic` expects `move.gate` to cross sectors and emits a retry
  error when it returns without doing so. The previous CE gate-level rejection
  violated that contract. Version-2 guards reject the destination/route in the
  caller before invoking gate travel, signal local replanning and wait five
  seconds. MD reissues local movement at most once per 30 seconds.
- SOURCE: native defence computers dispatch turret lists and low-attention
  attack strength independently of pilot Attack orders. CE filters these paths
  as well as station retaliation; guarding only `order.fight.attack.object`
  cannot prevent autonomous station fire. Missile turret targets remain allowed.
- IMPLEMENTED: departing groups hold weapons, fly to a safe rally point, and
  wait for every surviving member's undocking/order completion. The L commands
  capital groups; escorts use `assignment.attack`. A 10-minute deadline rolls
  failed departures into tracked safe cleanup without a success popup. The
  45-minute piracy lifetime starts on successful departure. Popup guards,
  phase/deadline/order references and cooldown reservations are saved.
- SOURCE: native Wait with `holdfire=true` restores saved weapon modes on abort.
  Departure Wait uses `holdfire=false`; MD owns the hold/rearm transition so
  leaving Wait cannot restore stale hold-fire modes over the piracy setup.
- IMPLEMENTED: true-owner plus pilot version markers scope all new hooks;
  apparent pirate cover cannot bypass them. CE blocks cover, resupply and
  offload trips. Full commander holds or lost required drones retire the group.
  Existing active groups are not migrated to behaviour version 2.
- MOCKED: loaded player fighters, cheap goods, empty ships, berths, missing
  drones, departure timeout/reload, exact fleet leadership, station aggression,
  weapon filtering, bounded replan, capture/boarding and lifetime/relief cleanup.
- UNMEASURED IN GAME: complete capital departure, native demand/comply/refuse,
  coordinated attacks, high/low-attention station avoidance, and continued relief
  deliveries. Source/schema/mock checks cannot prove these engine behaviours.


## 2026-09-25 - capital-destroyer-commander

- User requirement: the L destroyer commands a capital raid, with both M ships
  and all four S escorts below it. Light/strong raids retain their first M leader.
  New groups save an explicit Leader selected during creation; the destroyer
  replaces the initial M selection. Only that leader receives Plunder.
- LOCAL SOURCE: `order.plunder.xml` excludes spacesuits and laser towers, not L
  ships; the Argon destroyer storage macro supplies 2300 container capacity.
  Native cargo demands are therefore retained on the capital commander.
- Ownership transfer and command assignment are separate passes. Because the L
  spawns after some escorts, assigning earlier ships immediately would reference
  a commander still owned by the hub. All ships must have CE ownership first.
- MOCKED: all three tiers assert exactly one Plunder order, the expected leader,
  and every other ship assigned to it with matching CE ownership. Existing saved
  fleets retain orders; new launches use this hierarchy. Native fleet behavior
  remains an in-game acceptance step. Full restart required.
- VALIDATED: `just validate` passed 193 backend tests and reference/attribute
  checks; `git diff --check` passed. Full schemas were not rerun for this
  commander-selection/control-flow change.

## 2026-09-25 - distinct-free-raid-berths

- MEASURED IN GAME (local debug.txt, game time 241095.02): capital attempt at
  hub 0x4aa0c selected `dockingbay_arg_m_01_hightech_macro` 0x4aa17 twice. Native
  creation rejected the second Minotaur because the first ship already occupied
  the dock. The failure happened before the destroyer; compatibility was not
  sufficient to allocate a multi-ship wave.
- LOCAL SOURCE: `common.xsd` match_dock supports free=true and defaults to
  external storage=false berths. Native `scenario_combat.xml` uses free=true
  for docking selection. CE now enumerates free operational compatible external
  docks and excludes those already selected for the same synchronous wave.
  Known capacity shortages reject before creating any ship or group. Unexpected
  native creation failures retain the existing partial-group cleanup.
- User-facing capacity feedback now distinguishes insufficient free docks from
  an engine application failure. Diagnostic capacity messages include tier,
  size, free candidate count and selected-berth count; raid failures set their
  incident kind instead of logging null.
- MOCKED: raid fixtures return stable dock identities and reject occupied berth
  reuse. Tests require seven distinct capital-wave berths and reject a one-M-berth
  hub or occupied L pier without spawning ships, announcing success or spending
  cooldowns. Native launch after the correction remains unverified.
  Full restart required; no UI-only reload can install the MD allocation change.
- VALIDATED: `just schema` passed 193 backend tests, native MD schemas, reference
  checks and merged AI schemas for the combined fleet and docking corrections.
  `git diff --check` passed.

## 2026-09-25 - one-fleet-per-raid

- MEASURED IN GAME (user report): strong raids appeared as M/S/S plus a lone M.
  The launch loop gave both first and second M ships independent Plunder orders,
  then assigned only later ships to the first M.
- New raids now give only the first M a Plunder order. All other ships, including
  the second M and capital-tier L, receive native defence commander assignment
  to that M. This follows the native `cpu_ship_manager.xml` assignment pattern.
  Active saved raids are not reissued orders; the change applies to new launches.
- MOCKED: every tier verifies exactly one Plunder order and a common commander
  for all remaining ships. Actual fleet behavior still needs in-game acceptance.
  Full restart required for the MD launch change.

## 2026-09-25 - five-raid-groups-per-hub

- User balance change: five active groups per hub, no global cap and no separate
  capital-group cap. Withdrawals still occupy slots. Ordinary 60-minute launch
  and four-hour capital cooldowns remain; debug launches bypass both.
- Groups previously keyed by hub cannot represent multiple concurrent waves.
  New groups have monotonically allocated numeric IDs and an explicit Hub field.
  Legacy component-keyed entries receive their original hub field lazily and
  retain ships, deadlines, boarding protection and cleanup state. Numeric and
  component keys coexist until old groups finish; no destructive migration.
- Cleanup checks the explicit origin hub. Clear-unrest dispatch withdraws all
  matching groups, including legacy entries, without affecting other hubs.
  The localized cap failure now names only the five-group per-hub limit.
- MOCKED: five capital waves at each of two hubs succeed (ten globally); a sixth
  wave at the same hub is rejected, including when a group is withdrawing.
  Tests cover legacy migration, all-local clear, capture cleanup and unchanged
  normal capital-cooldown fallback. Native save/load migration still needs
  in-game confirmation. Full restart required for the MD changes.
- VALIDATED: `just schema` passed all 191 backend tests, native MD schemas,
  reference checks and merged AI schemas. `git diff --check` passed.

## 2026-09-25 - raid-pilot-blackboard-and-text-ids

- MEASURED IN GAME (user log, game time 241055.56): a debug light raid reached
  ship creation, then failed writing `$ce_unrest_sector` and
  `$ce_unrest_withdraw` on the ship component; its incident text evaluated null.
  Prior mocks accepted component variables and calculated literal text IDs,
  so their success did not validate either engine contract.
- LOCAL SOURCE: `scriptproperties.xml` defines `$<variable>` on entity, not
  component. Native `cpu_ship_manager.xml` writes ship state through
  `$CPUShip.pilot.$noattackresponse`. CE now stores and reads raid markers on
  pilots in MD and both AI patches. Lifecycle repairs missing markers on tracked
  saved raids or replacement pilots; captured ships remain exempt.
- LOCAL SOURCE: native dynamic text lookup uses
  `readtext.{$Page}.{$TextOffset + 1}` (`gmc_assisted_task.xml`), not arithmetic
  inside `{page,id}` literals. CE now selects constant translated tier and
  composition strings before formatting the raid notification.
- MOCKED: raid fixtures now reject ship marker writes; the expression harness
  rejects nonconstant literal text IDs. Tests cover all tier labels, pilot state,
  old-group repair without duplicate popups, and both reported invalid forms.
  Actual launch/notification behavior after this correction still needs an
  in-game retest. Full restart required for MD and AI changes.
- VALIDATED: `just schema` passed 188 action tests, native MD schemas, references
  and all merged AI patches. The final 14-test incident suite additionally passed
  pilot-based gate guards, player/NPC weighting and captured-ship exemption.
  `git diff --check` passed.

## 2026-09-25 - civil-unrest-native-incidents

- LOCAL SOURCE: `common.xsd` exposes docked `create_ship`, scoped
  `set_object_hacked` with a returned component list, manual production pause,
  native cargo drops, interactive notifications and `destroy_object`.
  `rml_buildstation.xml` uses destruction on operational station modules;
  destruction is distinct from removing a construction-plan entry. CE waits for
  a missing/wrecked target to confirm success. An explosion alone is insufficient.
- LOCAL SOURCE: `order.plunder.xml` searches for cargo targets through
  `move.seekenemies`, demands cargo and attacks on refusal. Its target parameter
  is not a general trader-target override. CE therefore filters native eligible
  contacts immediately before selection and weights player traders 3:1. The
  separate `move.gate` guard prevents tagged CE ships using outbound gates.
  Both patches exempt ordinary ships and player-captured raiders.
- IMPLEMENTED: saved shortage state lives on each hub record. Scoring runs before
  reserve consumption, counts only the tail after depletion and grace, recovers
  at twice accumulation speed and uses the worst ware per category. Recovery is
  clamped before adding later shortage: calm supplies cannot prepay deprivation.
  Category assignments are frozen with resolved racial profiles; legacy records
  classify existing definitions without regenerating demand.
- IMPLEMENTED: all player station types qualify for real sabotage, including a
  final operational module or dock. Native affected lists/dropped quantities and
  destruction confirmation gate success popups. Saved cooldowns, pending
  destruction, pause deadlines and raid groups own cleanup across saves. Player
  intervention through the native station overview pause control revokes CE's
  temporary-pause ownership rather than being overwritten at its deadline.
- IMPLEMENTED: normal and debug incidents share handlers and alerts. Debug
  requests consume command-specific snapshot tokens, validate fresh hub/debug
  state, retain target applicability/caps and never substitute another effect.
  Partial raid launches remain tracked while withdrawing without a success
  popup. Captured ships are released; boarding delays disposal. Clearing unrest
  withdraws debug groups too, while explicit raids can otherwise be tested at
  calm scores.
- MOCKED: action tests cover grace, partial delivery, recovery, hysteresis,
  critical warning guards, tax transitions, exact debug dispatch, replay rejection,
  native-effect failure, cargo limits, final-module eligibility, raid composition,
  partial launches, captures and boarding. Separate accounting tests confirm
  stage penalties reduce only CE's additional sector reward. Lua tests cover
  real-effect menus, stale tokens, unrest display and manual-pause interception.
- UNMEASURED IN GAME: physical wreck/rebuild and collateral behavior, collectible
  cargo, actual dock launches/loadouts, combat/targeting and sector containment,
  native alert interaction, and save/load during effects or boarding. Schema and
  action-mock success must not be promoted to native gameplay acceptance.
- VALIDATED: `just schema` passed 185 action tests, 18 full MD schemas, reference
  checks and all three merged AI schemas with no introduced errors. The added
  tax-penalty accounting test then passed with the 14-test sales-tax suite.
  `just lua` and `git diff --check` passed after the final UI/documentation edits.
- Only English translations currently exist; unrest keys are synchronized there.
  Full game restart required; `/reloadui` cannot install the new MD/AI/faction
  behavior. README and `docs/` remain unchanged.

## 2026-09-23 - player-facing-lockbox-benefit

- Present lockbox discovery as Discover lockboxes with Enabled/Disabled, based
  on unlock and active eligibility. Keep locked/suspended reasons in Status.
  Tooltips describe discovery and retained locations, not survey timing or counts.
  The underlying cadence, filters and diagnostic payload remain unchanged.

## 2026-09-23 - active-without-recipients

- User preference: unlocked bonuses display Active whenever the hub qualifies,
  even with zero workforce, trade or radar recipients. Recipient counts remain
  informational; remove the No eligible recipients presentation distinction.
  Native applicability and grant logic are unchanged. Lua regression covers all
  three zero-recipient cases remaining green/Active.

## 2026-09-23 - styled-view-tabs

- Replaced the View dropdown with two centered native buttons in fixed row 5.
  Both stay enabled; the selected tab has a persistent blue background and bold
  text, the other the standard background and regular text. Selection no longer
  relies on disabled styling. Reclicking the selected tab does not reset scrolling.
- The existing single-table contract, first scroll row 6, and Supplies reset on
  hub change remain. Lua checks cover style, switching, reset and no-op selection;
  in-game visual acceptance is pending.

## 2026-09-23 - unique-growth-tooltip-lines

- Paused hubs return the same message from state and action formatters. The map
  growth tooltip now deduplicates nonempty progress/state/action messages in that
  order, preserving distinct guidance. Regression covers the known pause reasons.

## 2026-09-23 - progress-overlay-and-reward-colors

- Replaced the half-width progress layout with a full-width bar: column 1 anchors
  the bar, while a transparent icon spanning columns 2-5 overlays right-aligned
  next-level text. This uses the existing native storage-bar layering pattern.
- Reward status colors are presentation keys, updated via native color callbacks:
  active green, suspended red, locked/unavailable gray, no recipients amber.
  Overall status reflects supply eligibility; a particular bonus can still be
  locked or have no recipients while that overall status is active.
- Lua checks model colspan width and exercise all five row-status colors plus
  summary changes without rebuilding the panel. Native visual acceptance pending.

## 2026-09-23 - compact-hub-header

- The fixed header now has five rows: title; population with right-aligned level;
  half-width progress with right-aligned next-level details; bonus status; View.
  Column 2 ends at the panel midpoint, allowing both views to share this geometry.
- Bonus column headings start the scrolling section directly. Eligibility details
  live in status/benefit tooltips; the operational/ownerless/population explanation
  is no longer shown. Next-level text uses `+25% demand`.
- Keep first scroll row 6 consistent across initialization, view switching, hub
  switching, cleanup and scroll clamping. Lua checks cover alignment, half-width
  geometry and native minimum-height calculation; native visual acceptance pending.

## 2026-09-23 - diplomacy-bonus-diagnostic

- `[CE] Diplomacy:` records the native station-targeted calculation at operation
  start: action, target, sector, before, bonus and final. Zero bonuses are logged
  for control cases; guaranteed-success actions bypass the calculation and log.
- The log is inserted after CalculatedSuccessChance, so final includes the native
  99 cap; before is AssembledSuccessChance minus CEBonus. No roll or outcome is
  changed. Debug text uses MD `%s` placeholders, including numeric values.

## 2026-09-23 - bonus-view-navigation

- User screenshots showed disabled current-view buttons looking unavailable,
  while the other view appeared highlighted. Use the native View dropdown with
  explicit startOption, matching menu_map.lua's createDropDown API and
  onDropDownConfirmed(_, id) signature. Preserve the single-table widget contract.
- Bonuses omits shortage ware names (available under Supplies), uses a compact
  sector-local eligibility explanation and wider benefit column with headings.
  Lua checks cover selection, switching back, hub reset and native minimum height;
  final native rendering still requires in-game acceptance.

## 2026-09-23 - level-ten-widget-minimum-height

- MEASURED: profile debug.txt after the Argon Prime test upgrade to L10 logged
  widget rejection twice: 621 pixels available, 648 minimum required. X4 remained
  running; this log does not establish a fatal engine crash. Evidence snapshot:
  `.validation/level10-before/debug.txt` (game times 236489.66 and 236493.00).
- ROOT CAUSE: native widget_fullscreen.lua `calculateMinRowHeight` groups each
  selectable row with subsequent unselectable rows. CE's entire scrolling list
  had nil rowdata, making it an indivisible block despite maxVisibleHeight.
  Scrolling rows now use true rowdata; fixed summary rows remain unchanged.
- Regression executes the reference native minimum-height function using fixture
  row heights, including a negative control with the old nil rowdata. This is
  source-executed validation, not an in-game rendering acceptance test.
- The same log rejected `%d` in MD-formatted reward-unlock text (key 159), at
  each crossed unlock. Changed that MD-only key to `%s`; Lua string.format keys
  keep their numeric specifiers. Runtime retest remains required.

## 2026-09-23 - sector-rewards-implementation

- Implemented source paths for immigration, NPC ware prices, station-targeted
  diplomacy/espionage, station radar sharing and lockbox surveys. Balance and
  eligibility live in CE_RewardRules; saved state belongs to each sector record.
  Runtime acceptance is outstanding; see ARCHITECTURE's native acceptance section.
- READ: `common.xsd` price amounts use the ware price variation range, not a flat
  current-price percentage. Player modifier actions accept IDs, allowing CE-only
  removal. Native radar access uses paired requests in `md/diplomacy.xml`; repeated
  adds are not an idempotency mechanism. Coexistence/serialization needs runtime proof.
- READ: `menu_station_overview.lua` exposes per-race native growth change,
  sustainable population and target through GetContainerWorkforceInfluence, plus
  ShouldContainerFillWorkforceCapacity. Immigration uses these constraints without
  changing global workforce parameters or adding a native growth influence.
- READ: influenceconfigurations.xsd supports `radarrange`, but
  stop_script_influences clears all stoppable script influences on an object.
  CE uses station sharing instead of a temporary ship range multiplier.
- READ: set_object_long_range_scanned is used by scenario_tutorials.xml to mark
  objects; its lockbox marker persistence and remote visibility remain runtime gates.
  CE records marked objects to avoid counting the same survey result repeatedly.
- Implementation hazard: checking supply only after a delivery hides the preceding
  shortage. Reserve accrual now invalidates immigration fractions when the elapsed
  interval contains uncovered time. No extra credit is granted for that gap.
- Hub snapshot v4 adds a reward payload; UI accepts v3 without rewards. Only English
  is currently shipped, and all added text uses its localization page.
- Native success evaluation uses a seeded integer roll and a strict comparison;
  preserve that comparison, guaranteed-success branch and native cap. CE advertises
  success-calculation points, not a claimed exact final percentage.
- READ from md.xsd: only signal_cue_instantly accepts a param attribute;
  deferred signal_cue does not. Reward signals carry sector/record context using
  the instant form. Treat the validator's unknown-attribute INFO as actionable
  unless an actual engine/vanilla precedent establishes otherwise.

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

### 2026-09-24 - optional-verbose-transaction-log

- VTL v114 (`VerboseTransactionLog`) is optional. Its `transfer_money` Lua event
  only annotates; its `TransferMoney` MD cue also pays money and must not be used
  alongside CE's payout. Tax labels use the Lua event and are verified in-game.
- MEASURED: delivery completion, AI order completion and player receipt occur at
  different times; even the account notification reached Lua 17ms after the ledger
  entry. VTL requires exact timestamps, so event timing cannot reliably label
  deliveries. Its amount/time matcher can also confuse equal simultaneous payments.
- IMPLEMENTED: the delivery adapter finds a unique native `orderqueue_remove`
  receipt by seller, exact cents and completion-to-account-event window (at most
  30 seconds). It stores the receipt ID in VTL's `lookupTable` and synchronously
  calls `mvtl.onGameLoad` to refresh VTL's cache. Missing/disabled VTL, unsupported
  data, missing/ambiguous receipts and existing descriptions are left unchanged.
  This depends on VTL internals and may need maintenance after VTL updates.
- Native ledger queries require `UniverseID` values (`C.GetPlayerID()` and
  `ConvertIDTo64Bit` for blackboard components); blackboard access requires Lua
  IDs. Tests must distinguish these representations.
- MEASURED: the blackboard converts MD money to Lua credits. Pass the original
  money value; dividing by `1Cr` first double-scales it (51800 internal cents
  became 5.18 Lua credits). Native transaction-log amounts remain in cents.
- USER-VERIFIED: delivery names now render correctly. New receipts store `ceWare`
  alongside VTL's description; UIX renders its localized name in the empty Detail
  cell without setting `entry.ware` (which would enable trade expansion). Ware
  Detail rendering is covered by automated tests but awaits in-game verification.
  Temporary troubleshooting output is removed; old entries are not migrated.

### 2026-09-24 - tax-negative-transfer-result

- MEASURED: debug.txt at game time 240902.10 records the new debug hub
  `0x1a6ee4` receiving 1,666 water, with sale value 6,164,200 internal cents.
  Its tax branch ran but `transfer_money/@result` was -924,600 cents. The
  positive-result guard therefore suppressed both ticker and General logbook.
  No before/after player balance was recorded, so this does not establish
  whether the old transfer credited or debited the player.
- SUPERSEDES the original transfer-result assumption below: tax now uses
  `reward_player`, following `reference/md/gm_supplyfactory.xml:661`, and
  computes credited income from the synchronous `player.money` delta. The
  trace includes requested income, balances and the notification setting.
- READ: native `ego_detailmonitorhelper/helper.lua` handles `script_add`
  financial entries as mission rewards. That is the expected generic label
  for the replacement payout; creation/display of its native transaction entry
  still requires an in-game test. CE's descriptive tax entry remains in General.
- MOCKED: tax tests now mutate the player balance rather than inventing a
  positive transfer return. They cover the reported water sale, no/negative/
  partial credited income, current sector ownership, duplicate guard and
  notification/percentage settings. Native rounding is not modeled.
- VALIDATED: `just schema` passed all 153 action tests, native MD schemas,
  reference checks and the merged build-storage AI check. Full restart is
  required; the replacement payout has not yet been tested in-game.

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

- READ (2026-09-24, updated after the negative-transfer-result test):
  `CE_Trade.RecordDelivery` pays configurable sales-tax income (default 15%) via
  `reward_player` for completed civilian purchases in
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

- Promotional images live in `images/`; `assets/` retains the native game layout.
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

Force finish requires an actual native build task. Pending planning or retry
state alone cannot enable it.

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
  sector/ware details and native money formatting. SUPERSEDED assumption:
  `transfer_money/@result` was originally treated as positive paid income;
  the later water-delivery test above disproved that sign assumption. Messages
  now use positive player-balance delta after `reward_player` instead.
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

### Population consumers and change sources (vanilla sweep, 2026-10-01)

READ over base + all DLC md/aiscripts/libraries/ui (747 base + 448 DLC files);
engine formulas are invisible, so each engine-side link is marked.

- Consumers: (1) station workforce growth (`parameters.xml` workforce/growth/population,
  surfaced as the "Sector Population" influence of `GetContainerWorkforceInfluence`);
  (2) build plot price, `parameters.xml` `plot/population factor="0.01" max="25"`,
  per 1M inhabitants (schema text only); (3) terraforming: many projects require
  population >= 10,000, `pricescale="population"` supplies, per-planet housing targets
  (100M-1B); (4) `citylevel` planet shader param, 0..10B -> 0..1; (5) UI only (map
  sector panel, encyclopedia, station overview tooltip). No aiscript, job, gamestart,
  faction goal or other mission reads population. Script-readable form is only
  `cluster.terraforming.stat.population.value` (read-only); no sector property.
- Terraforming is base game. Stat `population` (`terraforming.xml:80`) defaults to 0,
  has no min/max, and project effects can only ADD to it (min/max/value/onfail ignored).
  Repeatable housing projects: bubblecity +10k, habmodule +5M, housing_dense +15M,
  arcology +200M, housing_luxury +100, Boron housing_ocean +5M. Worlds: Scale Plate
  Green, Black Hole Sun, Getsu Fune, Frontier's Edge, Atiya's Misfortune, Eighteen
  Billion, Memory of Profit, Ocean of Fantasy; Tharkas Cascade and Emperor's Pride
  setups are never triggered. These planets have no `maxpopulation`, so
  `vanilla-sector-populations.md` shows 0 for them, but they can reach billions.
- No vanilla decrease path: random events and side effects never touch population;
  `set_terraforming_stat id='population'` is only used for setup (0) and debug cues (10B).
- Cradle of Humanity `Story_Terraforming` cue `Ch8_Terraforming_Effects`
  (`ego_dlc_terran/md/story_terraforming.xml:14206+`): Segaris (Terranova) and Gaian
  Prophecy (Sutton), both without `maxpopulation`, are initialised at 0 and then raised
  hourly 1k -> 75M (Gaian x1.2) via `set_world_population amount=`, not via the stat.
- No script or UI code links population to sector owner.
- MEASURED 2026-10-01 (throwaway probe extension, source archived in toolkit
  `.claude/backups/ce_terraform_probe-2026-10-01/`; user's ~66h save where
  vanilla had already initialised Black Hole Sun, partname `planet001b`, stat 0):
  `set_terraforming_stat population` 0 -> 400,000,000 was confirmed by reading the stat
  back, but `C.GetSectorPopulation` for Black Hole Sun IV (factor 1) and V (factor 0.75)
  stayed 0 at +2s, +60s and +6min. CE's registry had no record for either, and no
  `[CE] Population:` line appeared. So within a running session the terraforming stat
  does NOT feed sector population, and CE does not react to it. The earlier inference
  ("yes, via world factor") was wrong for this window. Positive control is INFERRED
  only: CE logged no population changes for its tracked sectors, which it would have
  if `GetSectorPopulation` returned 0 everywhere.
- MEASURED 2026-10-01, same save after save + reload: the map showed Black Hole Sun IV
  at 400M (USER-VERIFIED). CE's first reconcile after load created two new construction
  sites in one pass; their initial civilian funding was 2,870,400 and 2,148,400, ratio
  1.336, matching 400M : 300M (the 0.75 world factor). That the two sites are Black
  Hole Sun IV and V is INFERRED from timing and that ratio; the log line names no sector.
  So the engine computes sector population from the terraforming stat times the world
  factor, but only refreshes it on game load. CE picks it up on its first reconcile
  after load. A new record gets its population at creation, so no `[CE] Population:`
  line is logged. Vanilla workforce growth probably shares the same lag (INFERRED, it
  uses the same engine value). Not yet tested: project effects instead of
  `set_terraforming_stat`, `set_world_population amount=`, conquest.

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
uv run --with lupa python tests/lua/test_debug_menu.py
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

## Native plot and startup contracts

- Fresh hubs use the existing plot and prepare all ten cumulative plans before
  applying level 1 directly for initial seeding, or creating build storage for
  normal replacement/upgrade construction.
- Only native generation failure permits safe plot enlargement, at most 2 km
  per face per attempt and 16 km half-size per axis. Preserve the center and
  never shrink existing plots. Try three candidates before enlargement/backoff;
  malformed plans or build-task failures do not establish insufficient space.
- At most three relocations are allowed, only for a completely empty, uninitialized
  shell without storage, accepted plans, build tasks or a pending callback.
  Native safepos.radius is required clearance, not a search radius. Established
  stations never relocate. These are bounds, not universal fit guarantees.
- Saved retry state belongs to CE_Placement.State.Sites, keyed by hub identity;
  loss/reset clears it. A dormant state cue needs event_cue_signalled, because
  an actions-less condition-less cue is completed and cannot safely own state.
- Initial operational readiness follows native module completion, funding and
  builder assignment. A clean schema check does not establish in-game readiness.

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

## 2026-09-27 - temporary sector demand events

Historical single-event model; superseded by concurrent-sector-events below.

- IMPLEMENTED: eleven events modify only a sector hub's existing consumption.
  Events last 7200 game seconds, with independent 10800-21600-second gaps, including
  the first event after initialization. Positive effects roll +25-100%; bumper
  harvest, industrial slowdown and smuggling crackdown roll -25-50%.
- Event state lives on the sector registry record, not the hub object. Its affected
  ware list is frozen at start and survives replacement and save/load. Event
  multipliers always compose with frozen base definitions, never previous rates.
- Expiry must split both reserves and unrest at the same historical endpoint.
  Rate commit rebases `Last` to current game time, so the expiry wrapper restores
  the boundary before consuming the normal-rate tail. Merely clearing the event
  on the minute tick would overcharge deliveries crossing the deadline.
- Snapshot v3 optional slot 21 carries event display, applicability and a separate
  command token. The map keeps one table, adding a fixed event row conditionally.
  Debug triggers replace the existing event and preserve normal notifications;
  early ending schedules the ordinary gap. No laws or policing are changed.
- Automated action/Lua tests cover arithmetic and UI contracts. Native rendering,
  ticker timing and save serialization remain in-game acceptance checks.
- VALIDATED: `just schema` and `just lua` pass. The shipped-action expiry case
  consumes 450 units across two hours at 200/hour plus half an hour at the normal
  100/hour; a subsequent delivery adds only its actually transferred stock.
# 2026-09-27 - civilian-hub-ownership

- Source-verified: vanilla `civilian` has locked relations, including Xenon and
  Kha'ak hostility, and no primary race. Keep explicit manager appearance selection.
- Hubs now use civilian ownership. Keep historical MD names and plan IDs for saves;
  migrate only registered live ownerless hubs, without replacing their objects.
  Manager/build-storage repair also handles partial ownership propagation.
- Creation tests the sector owner's enemy relation toward civilians, not nearby
  enemies or the player's relations. Existing hubs survive the eligibility check;
  destroyed hubs wait for non-hostile ownership before reconstruction.
- Funding still comes from `faction.ownerless`; changing ownership does not change
  the established account funding mechanism. `ce_unrest` remains separately owned
  and explicitly neutral toward civilians and ownerless objects.
- Automated migration tests exercise MD actions with mocked native ownership;
  native construction continuity and attack selection remain unverified in game.

# 2026-09-27 - raider-appearance-provenance

- READ: `libraries/factions.xml` assigns `faction_scaleplate` color and icon to
  `ce_unrest`; this dates to `e8039e4` (2026-09-25, Unrest). This is not a paint
  assignment. `CE_Raids.Request` creates ships as the hub owner without explicit
  paint; `CE_RaidBehaviour.Prepare` transfers them to `ce_unrest`.
- READ: `a42cc6a` (2026-09-27) changed hub ownership from ownerless to civilian,
  also changing the initial owner selected by raider creation. Vanilla
  `libraries/themes.xml` maps ownerless to `paintmod_0008` and civilian to
  `paintmod_0001`; `libraries/paintmods.xml` defines these as desaturated and
  unmodified respectively. INFERRED: this may explain the newly observed red
  hulls; the screenshot's exact paint ID and ownership-transition rendering have
  not been measured in game. Do not describe red as an explicit CE livery.
- READ: vanilla `themes.xml` supports fixed and weighted random paint selection.
  `common.xsd` exposes creation-time `paint`, `add_paint_mod`, and independent
  faction icon/decal selection through `set_faction_identity`. Custom CE paint
  and a dedicated emblem can be configured separately from relations/AI.

- SUPERSEDED by the explicit livery implementation later on 2026-09-27: newly
  created raiders now specify `paintmod_0018` (Grey Steel) and `ce_unrest` uses
  `ce_unrest_skull` for its icon/decal. The earlier observations above describe
  the previous implementation. Existing ships are not repainted.
- READ/MEASURED: the vanilla Scale Plate icon resolves a `.tga` texture reference
  to a `.gz` catalog member containing an uncompressed 256x256 DDS with nine mip
  levels. CE follows that encoding with an extension-qualified path; the release
  asset allowlist must include the `.gz`, not just the XML referencing it.
- MEASURED: x4validate scans XML even under repo-local `.snapshots/`; give backup
  copies a non-XML suffix such as `.xml.bak` to keep them out of mod validation.

# 2026-09-27 - skull-decal-square-investigation

- USER-OBSERVED: Grey Steel applied, but the skull rendered as a solid light
  square on ship hulls. Previous static success did not verify native rendering.
- USER-OBSERVED follow-up: the skull is visible in the target window. The UI
  texture path therefore works; the failure is specific to hull-decal use.
- MEASURED: the installed skull `.gz` is byte-identical to the workspace asset;
  debug.txt records access to it. Its DDS header matches vanilla Scale Plate's
  dimensions, pixel flags, BGRA masks, pitch, mip count and caps; only reserved
  exporter metadata differs. All nine mip levels have valid alpha data, including
  transparent corners at the base level. This rules out an opaque-square source
  image, but does not prove the engine sampled this texture on the hull.
- READ: vanilla Scale Plate and Terran faction declarations use active/inactive
  icons without an explicit image override. CANDIDATE repair: remove CE's
  redundant `image="ce_unrest_skull"` override and retain the skull icons and
  texture unchanged, isolating faction decal wiring. Root cause and in-game
  effectiveness are still UNVERIFIED; do not record this as a confirmed fix.

- SUPERSEDED by user confirmation later on 2026-09-27: removing only the faction
  `image` override restored the visible skull hull decal. Keep active/inactive
  icons and let the engine derive the decal; do not restore that override.
- MEASURED: the game extension folder is a junction to this development repo.
  Edits are already deployed through it; local testing needs no ZIP installation.
- Black Steel comparison requested after the successful skull test: creation
  paint changed from Grey Steel (`paintmod_0018`) to Black Steel (`paintmod_0017`,
  vanilla ware name `{20114,10171}`). Existing ships retain their paint; restart
  and spawn a new raid to compare. The new appearance is not yet user-verified.

## 2026-09-27 - concurrent-sector-events

- IMPLEMENTED: `DemandEvents` version 2 holds an ID-keyed active collection and
  one command token. Migration retains the old event's exact deadline, strength
  and ware list without announcing its start; the old cooldown is discarded.
- Same-ware intersection, not merely event names or group identity, prevents
  conflicts. Frozen baskets remain authoritative after upgrades. Ending one
  event normalizes only its goods and retains all unrelated modifiers.
- Minute rolls use seven demand groups. With K applicable groups including
  occupied ones, each unoccupied group rolls 1/[120*(K-1)+1]. The +1 accounts for
  immediate success on the expiry tick; omitting it biases the renewal average.
  No cooldown or catch-up exists. A single available group runs consecutively.
- MEASURED in seeded simulation, not the game: group counts 2-7 average within
  5% of one active event, with both quiet periods and concurrency. Tests derive
  the denominator and duration from shipped MD actions. Debug starts and changes
  in eligibility are excluded from this equilibrium claim.
- Expiry accrual processes chronological deadlines, removes equal-time events
  together and recomputes rates once per boundary. Restore `Last` after rate
  commit before accruing the tail; otherwise late updates lose elapsed demand.
- Snapshot v3 slot 21 now carries `[2, rows, eligibleIDs, token]`. Legacy payloads
  remain displayable but cannot authorize the new start/end debug protocol.
  The map retains one table; multiple events scroll instead of becoming fixed
  rows that could crowd out goods at small resolutions.
- Native save migration, ticker presentation and panel rendering still need
  in-game acceptance. Full restart required for the MD and localization changes.
- VALIDATED: 248 controller tests, `just validate`, `just schema`, `just lua`
  and `just translations` pass. Schema checks report no introduced errors;
  roots without a bundled schema remain outside native XSD coverage.

## 2026-09-27 - map-height-rounding-and-scroll-recovery

- MEASURED: debug.txt at game time 242049.56 rejects a table with 572 pixels
  available and 573 required. At 242050.30, ce_map_status.lua:180 fails in
  math.min because the saved top row is nil. A mocked nil GetTopRow result
  reproduces that exact Lua failure; native table rejection causing the nil
  return is inferred from the sequence, not separately instrumented.
- READ: native helper getVisibleHeight caps height without rounding. CE used a
  fractional 40% cap and tight bottom placement. WITHDRAWN: rounding as the cause
  of this failure. The same error recurred at 242404.53 after the UI reload;
  the native scroll-group contract below explains why extra clearance did not help.
- IMPLEMENTED: floor the cap, ceil visible height before bottom placement,
  floor y and reserve two extra pixels. Preserve the last numeric scroll position
  when GetTopRow returns nil; default missing state to the first scrolling row.
- Tests cover fractional viewports, explicit wrapped-cell heights, level-10
  scrolling, short lists, missing widgets, recovered widgets and selection resets.
  These are simulated geometry/lifecycle checks, not native rendering acceptance.
- Lua-only change: /reloadui suffices. In-game acceptance remains pending.
- VALIDATED: all three `just lua` suites and `git diff --check` pass.

## 2026-09-27 - native-scrollable-row-boundaries

- READ: widget_fullscreen.lua calculateMinRowHeight requires each selectable row
  and its following unselectable rows to fit together. Table creation falls back
  to requiring the full content height when scrolling would not reduce that
  minimum. CE made every row unselectable, so long ware lists could not scroll.
- FIXED: each non-fixed row now uses true row data and interactive=false, exactly
  as vanilla menu_map.addCapacityRow does. Summary rows stay fixed/unselectable;
  event rows, scrolling headings, wares and empty-state rows have independent
  scroll boundaries. This adds no buttons or data actions.
- MEASURED: executing the native fixed/minimum-height functions in the Lua
  fixture rejects the previous renderer at a 288-pixel cap with 981.75 pixels
  of content. All three just lua suites pass after the fix, including synthetic
  573-content/572-cap geometry, concurrent events and missing-widget recovery.
- The old mock checked geometry but omitted native row grouping. Passing those
  earlier checks did not establish native scrolling. In-game acceptance of the
  corrected renderer remains pending; /reloadui suffices.

## 2026-09-28 - selected-hub-reservation-refresh

- USER-OBSERVED: incoming cargo eventually showed its green segment after the
  minute tick. The issue was stale publication, not the bar's colour or formula.
- READ: native scriptproperties.xml defines trade.offeramount as available trade
  amount plus reservations. Vanilla map status bars use start=current stock and
  current=future stock. CE already follows both conventions.
- The selected map panel now requests diagnostics immediately and once per
  second through CEHubStatus/refresh. MD validates registry identity, civilian
  ownership and reset state before publishing, then signals CEHubStatusUpdated
  to invalidate the Lua cache without losing fallback data.
- Presentation refresh must not call AccrueAll, UpdateHub or UpdateOffers. It
  reads committed reserve/growth state and live offer reservations; economic
  simulation remains on the minute tick. Hover alone triggers no refresh.
- MOCKED: just lua covers the request lifecycle and publication cache bypass,
  including a 15,000-unit reservation and cancellation. just validate passes
  283 controller tests, including state preservation and rejected refreshes.
- Full restart is required for the MD handler. Live timing and cancellation
  acceptance still require in-game verification; mocked tests are not engine
  timing measurements.

## 2026-09-28 - spine-stage-indexing-and-preflight

- MEASURED: smoke token 1 at game times 241581.25-241582.99 failed all six
  races at level 1 before construction. The harness incorrectly assumed
  one-based stage boundaries. Recorded stages 1-9 are zero-based inclusive;
  stage 10 reports full entry count for both first and last. The queued level-1
  sequence exposes only the active prefix. The numeric observation fixture
  retains all six races and the source-log hash; it does not measure later
  queued sequences or establish the meaning of the final range properties.
- IMPLEMENTED: validate the first nine ranges and require the exact queued
  prefix count, macro basket, active stage and previously exposed entry IDs.
  Validate final-stage contents directly instead of guessing tail boundaries.
- IMPLEMENTED: CE_SpinePreflight queues all ten stages before any smoke/sample
  construction, cancels each build and waits up to 30 game seconds for its
  queue to drain. It retains the native full sequence when returning to level 1.
  Failures block construction; preflight checks are separate from physical
  passes. Geometry and module selections are unchanged.
- MOCKED: recorded range regressions and queue lifecycle tests cover a bad
  final basket, no preflight processing/force completion, retained sequence,
  queue drain timeout and construction bypass prevention. Revised native
  preflight, expansion, docking and appearance acceptance remain pending.
- VALIDATED: just validate and just schema pass (315 tests); just spine-check
  passes all generated plans and 32 focused tests; just lua and just translations
  pass. Native schemas report no introduced errors; six diff-rooted scripts
  lack direct bundled schemas, with affected merged AI scripts checked separately.
  Full game restart required; /reloadui cannot load this MD change.

## 2026-09-28 - spine-angle-types-and-repeat-initialization

- MEASURED: smoke token 1 at game times 242112.80-242131.10 completed all 60
  queue preflight checks and passed physical level 1 for all six races. Every
  race failed its level-2 physical validation. No bulk or docking cases ran.
- NAMED CHECKER DEFECT: native MD rejected angle modulo (9.42478rad %
  6.28319rad), producing 63 TRANSFORM_CHANGED rows even with identical printed
  old/new transforms. Previous numeric-only mocks incorrectly accepted modulo.
  The old operational=0 field represented aggregate validation failure, not a
  measured count of operational modules. Level-2 physical acceptance is unresolved.
- READ/MEASURED: build.buildstorage's built-station event sends init station for
  non-player, non-ownerless stations. Each racial level-2 event asserted that a
  trade NPC already existed. CE's existing guard covered registered hubs only.
- IMPLEMENTED: typed angular differences with both one-turn wraparound
  equivalents replace modulo. The test runtime preserves angle addition,
  subtraction and absolute values and rejects modulo; it is still not a complete
  native units emulator. BUILT now labels its aggregate result validation_passed.
- IMPLEMENTED: explicitly mark created experimental stations; extend the existing
  initialization guard to marked civilian stations with a trade NPC. Their first
  initialization and unmarked non-CE stations retain native behavior.
- MOCKED: regressions exercise all rotation axes, wraparound, tolerance and real
  changes; initialization cases vary ownership, registration, marker and manager.
  Native corrected expansion/initialization acceptance remains pending. Geometry
  and module baskets are unchanged. Full game restart required, not /reloadui.
- VALIDATED: just validate and just schema pass with 316 tests; just spine-tests
  passes 33 focused cases; just lua and just translations pass. Merged native AI
  schemas report no introduced errors. Backup snapshots use .bak suffixes so the
  toolkit does not mistake an archived diff for a live game-path patch.

## 2026-09-28 - spine-five-race-smoke-and-blackboard-scope

- MEASURED: token 1 at game times 241557.54-241590.52 finished with five smoke
  races passed and one failure. Argon, Paranid, Split, Terran and Teladi passed
  all ten physical stages. Boron passed stages 1-5 then failed at 6. All 60
  preflight checks passed; no bulk or docking cases ran. No angle arithmetic or
  transform-change errors remained. Physical level checks passed 55 of 56 attempted.
- MEASURED: 50 existing-trade-NPC assertions remained. The log also reports six
  failed set_value writes to station.$ce_spine_experiment. NAMED ROOT CAUSE:
  the station component cannot hold that entity blackboard variable. WITHDRAWN:
  the previous station marker implementation could protect experimental hubs;
  its numeric/table mock did not model the failed native assignment.
- IMPLEMENTED: publish a separate union of tracked current and retained objects
  on player.entity.$ce_spine_objects. AI checks this membership plus civilian
  ownership and an existing manager; first initialization remains native. Publish
  refreshes after cleanup and clears absent-run membership. INIT_GUARD logs native
  inputs. The regression station fixture rejects MD variable storage on stations.
- INFERRED: Boron's aggregate station-span guard caused level-6 failure. All 38
  module geometry rows were emitted, with positions matching generated coordinates
  within tolerance and no preceding transform/identity errors. Actual station
  dimensions were not logged, so the physical extent and its cause are unresolved.
- IMPLEMENTED: STATION_BOUNDS logs all three native spans; STATION_BOUNDS_EXCEEDED
  logs excess metres by axis. Position, missing/operational module and transform
  failures retain distinct reasons. These aggregate spans are not plot-relative
  corner coordinates; macro corner checks remain independent. No geometry,
  thresholds, module tiers or production records changed. Native acceptance of
  the registry guard and Boron diagnosis requires another smoke run after a full
  game restart; /reloadui is insufficient.
- MEASURED distinction: Boron's level-6 pier reports live width 2118.313 m,
  while its calibration max.x=1059.156 and center.x=859.153 reconstruct a
  400.006 m macro interval. Native component size and reconstructed macro
  intervals therefore differ; their semantics must not be treated as equivalent.
  This does not by itself establish a collision or justify shrinking the pier.
- VALIDATED: just validate and just schema pass (318 tests), just spine-tests
  passes 35 focused cases, and just lua / just translations pass. Merged native
  AI schemas report no introduced errors. These checks do not establish native
  membership publication or resolve Boron's aggregate span discrepancy.

## 2026-09-28 - corrected-native-half-extents-and-boron-refit

- MEASURED: smoke token 1 at 241764.74-241798.52 finished with five races passed,
  Boron failed at level 6, and no trade-NPC assertions or experiment MD errors.
  INIT_GUARD saw null managers initially and stable existing managers thereafter.
  This verifies the player-entity membership fix for this smoke run.
- MEASURED: Boron level 6 spans were 10192.055 x 3999.997 x 8475.701 m, exceeding
  width by 192.055 m. MODEL RECONCILIATION: native boundingbox.max acts as
  half-extents around boundingbox.center. Corners center +/- max reproduce all
  46 recorded non-Terran station spans within 0.002 m, including Boron's failure.
  Terran differs by up to 83.27 m; its native-size discrepancy remains unresolved.
- WITHDRAWN: v1's endpoint interpretation (min=2*center-max) and resulting claims
  that its macro-corner checks established containment. V2 retains raw max/center
  values plus derived corners and source-log hash. Generator rejects v1; native
  MD corner checks now also use center +/- max. Collision/docking remain untested.
- IMPLEMENTED: freeze five passing racial candidate parameters, original offsets
  and cumulative geometry hashes. Corrected bounds and 50 m functional-AABB gaps
  still pass without changing any of their entries. Only Boron is refitted.
- MODELLED Boron level 10: 8580.25319 x 8399.99772 x 7373.74660 m, 77 entries
  (previously 73). Inner/dock/pier target lengths 400/800/1600 m, snap variant 1,
  five vertical connectors per deck and a level-6 storage drop. Functional module
  choices and milestones are unchanged; all levels retain cumulative entries.
  This is a predicted envelope, not a measured new station or docking pass.
- MOCKED/STATIC: regression reproduces the old Boron level-6 native dimensions,
  checks nonzero-center native corner logic, and preserves historical stage-range
  observations independently of the new plans. Numeric observations/constraints
  contain no copied game assets. Full restart and a fresh smoke run are required;
  existing experimental specimens must not expand using regenerated identities.
- VALIDATED: just validate and just schema pass with 319 tests; just spine-check
  verifies reproducible artifacts and 36 focused tests; just lua and just
  translations pass. All 55 non-Boron experimental plan XML nodes are byte-identical
  to the pre-fix snapshot, and production XML outside the experimental block is
  unchanged. Native acceptance of regenerated Boron remains pending.

## 2026-09-28 - all-six-races-native-smoke-passed

- MEASURED: token 1, game times 241728.39-241763.20, finished with smoke=6,
  checks=60, failures=0. All 60 preflight and 60 physical stage checks passed.
  All six races reached level 10. No experiment MD errors or repeat trade-NPC
  assertions were present. The log and corresponding manifest are preserved in
  .snapshots/spine-smoke-passed (ignored local evidence).
- MEASURED: refitted Boron level-10 native spans are 8580.254 x 8399.998 x
  7373.746 m, matching the model within 0.002 m. This verifies construction,
  expected operational modules, identity/transform preservation and the checked
  bounds for this smoke run; force completion does not validate deliveries.
- NOT RUN: bulk sites=0, docking=0, reviewed samples=0. Proceed to the full debug
  experiment only, not production integration. Finished smoke state must be
  returned to idle using Clean up experiment objects before Start spine experiment.
  Full start repeats its smoke gate, then bulk and physical/docking/visual gates.

## 2026-09-28 - bulk-pass-and-docking-monitor-repair

- MEASURED: full run token 3 completed 600 bulk sites and 6000 level checks
  with zero failures after six smoke passes. The first physical sample was Argon
  level 1. Its later in_sector_docking_interrupted result did not identify which
  prerequisite failed. Boron's S probe subsequently docked at 243234.09, then
  departure hit MoveWait's unsupported position parameter at 243251.57.
- MEASURED/READ: repeated dock.container errors occurred while ship.dock was
  null. Native move.gate guards dock presence; order.move.wait defines destination
  as [sector, position], not separate destination and position params. WITHDRAWN:
  null-dock errors entirely prevented approach; Boron's recorded docking disproves
  that. No complete docking cycles or reviewed physical samples passed this run.
- IMPLEMENTED: guard nullable dock before dereferencing; issue the documented
  MoveWait tuple once per departure; retain the undocked and >8 km exit gate.
  Distinct interruption reasons now identify sector/range/probe failures.
  Named map-visible probes, PROBE_START/PROBE_DEPART and status on observation,
  docking and review transitions expose progress without claiming completion.
- IMPLEMENTED: debug physical-samples-only start requires clean idle state,
  repeats smoke, skips bulk, then runs existing physical/docking/visual gates.
  Smoke-failed races remain blocked. Its summary reports sample/docking/failure
  counts and explicitly excludes bulk; no historical counters are synthesized.
- MOCKED: null and wrong-station docks, four ordered docking/departure cycles,
  native order parameter declarations, one departure order per cycle, precise
  interruption reasons, guarded rerun admission and distinct completion summary.
  New keys 398-401 translated across all 16 languages. Runtime docking and review
  still require native verification after a full restart; /reloadui is insufficient.
- VALIDATED: just validate and just schema pass (322 tests); just spine-tests
  passes 39 focused cases; just lua and just translations pass (268 keys in all
  16 languages). Merged native AI schemas report no introduced errors. Native
  repaired docking/departure and visual-review acceptance remain pending.

## 2026-09-28 - visible-observation-gate-and-bounded-retry

- MEASURED: the subsequent samples-only run passed all six smoke races. Argon
  and Boron level-1 probes failed the old attention.inzone gate while the station
  reported visible and the player remained in the test sector. Boron's S probe
  docked at 241895.14 and received a departure order at 241912.49 without the
  earlier nullable-dock or MoveWait parameter errors. No full docking cycle was
  established by these observations. Evidence: .snapshots/spine-observation-fix.
- WITHDRAWN interpretation: old observer_out_of_range meant the player had flown
  away. That gate measured attention, not distance; visible alone triggered it.
- READ: vanilla MD/AI use attention ge attention.visible for visible simulation;
  player.entity.distanceto.{object} supplies an explicit distance. The new helper
  separates wrong sector, measured range and insufficient attention diagnostics.
- DESIGN: 20 km, 30 game seconds to return and two retries per checkpoint are
  experimental limits, not measured engine thresholds. Recovery removes the old
  tracked probe before repeating its ship class; unseen activity earns no credit.
  Exhausted retries and expired recovery remain failures. Native acceptance is
  pending a full restart and another physical-samples-only run.
- MOCKED: visible attention admission, exact range boundary, low attention,
  wrong sector, recovery expiry, same-class restart without unseen credit,
  retry exhaustion and cancellation during recovery. All 42 focused cases pass.
- VALIDATED: just validate and just schema pass with 325 tests; just lua and
  just translations pass, with 270 keys in each of 16 languages. Native schema
  validation reports no introduced errors. Runtime acceptance remains pending.

## 2026-09-28 - visual-inspection-batch

- USER DECISION: skip docking tests and keep multiple completed stations available
  together for manual inspection of dock/pier access. This supersedes docking
  acceptance as a prerequisite for this inspection workflow, not as evidence of
  functional docking or production readiness.
- IMPLEMENTED: `visual` command/phase builds one station per race through all ten
  levels with one worker, preserving preflight and physical validation. Successful
  and failed specimens stay tracked and retained. No proximity gate, probe orders,
  intermediate review prompts or automatic visual acceptance. Summary reports
  completed/6 and failure counts; bulk, smoke and docking counters remain zero.
  Standard cancel, occupied cleanup, token guards and cleanup on reload remain.
- MOCKED: all 60 build-stage transitions advance without an observer; six completed
  stations coexist, failures remain incomplete and retained, clean-idle admission
  and cleanup cover the batch. All 44 focused checks pass. Native run pending.
- VALIDATED: just validate and just schema pass (327 tests), just lua passes,
  and just translations passes with 273 keys in all 16 languages. Merged native
  AI schemas report no introduced errors. Full restart required for the new mode.

## 2026-09-28 - six-race-visual-approval

- MEASURED: visual batch token 1, game times 241584.45-241617.82, completed all
  six racial stations through level 10 with 60 physical stage checks, 60 preflight
  passes and zero failures. Final counters: checks=60, samples=6, docking=0.
  Log and corresponding manifest preserved in .snapshots/spine-visual-approved.
  This supersedes the visual batch's earlier native-run-pending status.
- USER OBSERVED: all six finished layouts look good; all docks and piers look
  accessible. Record this as visual approval of the completed level-10 layouts.
  Actual docking/undocking remains untested by the user's decision. Force-completed
  construction does not establish resource delivery. Earlier 600-site/6000-check
  bulk evidence is separate from this visual run.
- SCOPE: prototype construction and visual review succeeded. Ordinary station
  construction, existing hubs and production profiles remain unchanged; integration
  is a separate implementation task, not performed by recording this approval.

## 2026-09-28 - production-spine-integration

- USER DECISION: replace ordinary construction with the visually approved racial
  spine layouts; remove all debug experiment code/options. The mod is unreleased:
  resetting all existing hubs is acceptable and no old-plan migration is required.
- IMPLEMENTED: six ce_hub_<race> bookmarked master plans replace the old static
  Argon catalogue and random runtime planner. Geometry and tier selections match
  the approved manifest. Production resolves required native macros and blocks
  unavailable layouts, then uses one retained finalsequence for stages 1-10.
  Active prefix counts, macro order and IDs are checked before processing.
- IMPLEMENTED: fixed 10 km plots; five-minute retry backoff without random direction,
  plot growth or relocation. Lost builds reuse master/stage; destroyed hubs get a
  new master at their earned replacement level. First-generation level-1 seeds and
  reset hubs complete their validated native first stage through a narrowly scoped
  Lua bridge; readiness revokes exact-object permission before upgrades.
- REMOVED: CE_Spine* MD scripts, probe orders, observation/review gates, experiment
  Lua/menu and translation keys, CE_LayoutTest tombstone, random forward planner
  and obsolete lifecycle tests. Numeric calibration, approved manifests and static
  geometry checks remain development evidence. Production reset targets registered
  CE hubs only; old standalone specimens need cleanup using the old running build,
  or a fresh test save. No new legacy cleanup/migration code is added.
- EVIDENCE LIMIT: earlier native geometry/bulk/visual results still apply to the
  unchanged layouts. Controller/reset integration is new and needs an in-game
  reset plus upgrade check after a full restart; mocked checks do not prove it.
- MEASURED OFFLINE: all ten levels and selections compare equal to the preserved
  visually approved manifest for every race. Plan reproducibility, static geometry,
  Lua authorization and 246 translation keys across all 16 languages pass.
- TOOLING: x4validate scans XML under ignored snapshot folders too. Historical
  snapshots with live .xml suffixes caused false missing-text references after
  experiment removal. Preserve backups as .xml.bak or ZIP files; all existing
  snapshot XML files were renamed without changing their contents.
- MOCKED: initial completion can arrive before native readiness. A one-second
  authorized-initial-build tick retries at most every two seconds, then revokes
  permission on readiness. Delayed completion and no replay after completion pass
  alongside the other 11 focused construction/profile cases.
- VALIDATED: final just validate passes 263 tests and XML/reference checks;
  just schema passes native MD/data schemas and merged AI patches with no
  introduced errors. just plans-check verifies reproducibility/geometry;
  just lua and just translations pass (248 keys in all 16 languages, including
  separate concurrent settings additions). README/docs remain untouched.
  Full restart and explicit Reset all CE hubs are required for old development
  saves. Production reset/upgrade verification remains pending in-game.

## 2026-09-28 - news-video-setting

- IMPLEMENTED: per-save NewsVideos defaults to true, including saves without the
  field. Ensure preserves explicit false; Read supplies true before initialization.
  The general-settings checkbox uses the existing validated boolean callback.
- IMPLEMENTED: the shared Broadcast handler reads the setting for each incident.
  Off retains the ticker and exactly one log entry, clears the local clip handle,
  and skips both playback and the replacement popup. On retains the native-playback
  failure popup. Critical warnings and already playing clips are unaffected.
- New localized label/tooltip IDs 157-158 are synchronized across all 16 languages.
  Native checkbox rendering and notification playback remain unverified in-game.
  Installation requires a full restart; subsequent setting changes apply live.
- MOCKED/VALIDATED: all 15 focused settings/news tests pass, including default-on,
  saved false, invalid values, checkbox callbacks, all three video routes, live
  re-enabling, playback failure fallback and independent critical warnings.
  just validate, just schema and just translations pass using the toolkit Python
  via CE_PYTHON. Native schema checks report no introduced errors; translation
  coverage is 248 keys in each of 16 locales in this working tree.

## 2026-09-28 - display-options-section

- IMPLEMENTED: CE_Options now groups controls under Debug, Gameplay and Display.
  NewsVideos is under Display. Gameplay retains its existing controls. Two
  unselectable space-text rows, fontsize 1 and height 8, separate the sections.
  This follows vanilla gameoptions.lua's explicit small-text spacer pattern;
  actual in-game spacing still requires visual confirmation.
- Display heading ID 159 is translated into all 16 locales. This supersedes the
  earlier placement of NewsVideos under Debug. MD menu changes require a full
  restart; /reloadui alone cannot load this edit.
- VALIDATED: just validate and just translations pass after moving the control;
  existing settings callback coverage follows the new control order. In-game
  visual confirmation remains pending.

## 2026-09-28 - validation runtime and isolation

- IMPLEMENTED: the test MD interpreter caches only normalized paths and compiled
  ordinary expressions, each with a process-local 8,192-entry LRU. Evaluation
  still reads the current Runner environment; mutable literals, XML trees and
  profile fixtures remain independent. Never cache evaluated profiles or XML
  library nodes: tests deliberately modify both state and shipped action trees.
- IMPLEMENTED: release fixtures copy a pristine working repository and bare
  remote per test, repointing origin. The seed is built once per process. Copies
  have independent Git objects, configuration, hooks and refs; real commits,
  pushes and rollback checks remain exercised.
- MEASURED on Windows, Python 3.14.2, lxml 6.1.3/libxml2 2.11.9: three baseline
  `just validate` runs at db293db took 146.536/190.449/176.656s; three optimized
  runs took 19.569/20.613/19.888s. Median controller time fell from 173.427s for
  263 tests to 15.711s for 277 tests. The 14 added tests cover caching, isolation,
  check selection and timing failures. The post-change tree also includes the
  separate settings-organization commit f361749; these are local suite timings,
  not an isolated hardware benchmark. No tests or statistical loops were removed.
- MEASURED: baseline release-suite runs took 78.997/76.681/73.470s; optimized
  runs took 58.054/54.747/53.818s, including two additional regression tests
  (64 total). Median improvement was 28.6%. Baseline native schema compilation
  alone took 88.4s for MD and 107.4s for AI; this work is not optimized or skipped.
- WORKFLOW: `check` keeps all controller tests and fast/static/UI checks, while
  `check-release` adds Git integration and remains the release tool's gate.
  `check-full` adds native schemas through `schema-only`, avoiding repeated
  controller tests. `schema` retains its original scope. `plans-verify` avoids
  the focused plan/construction tests already covered by normal discovery.
  `just validate --timings` reports stages, modules and slowest tests on success
  or failure. These tooling changes need neither restart nor /reloadui.
- VALIDATED: final `just check-full` passed in 299.880s, including 277 controller/
  tooling tests, 64 release-suite tests, translations, generated plans and Lua.
  Native MD/AI schemas compiled in 91.7/110.6s and merged AI patches introduced
  no errors. `just test-tooling` passed all 14 focused regression tests.

## 2026-09-28 - initial-hub-builder-exclusion

- READ: StartBuild calls AssignBuilder before InitialTick requests force
  completion; ReconcileSector also calls AssignBuilder while a build is pending.
  Excluding seed/reset hubs only at the first call would miss reconciliation.
- MOCKED: an available builder reproduced bookings on new-save and debug-reset
  initialization. The shared AssignBuilder guard now excludes the exact InitialHub
  at generation 1, level 1, target 0, including delayed completion and recovered
  tasks. Readiness revokes permission, allowing later upgrades to hire normally.
- VALIDATED: `just validate` passes 275 tests and XML/reference checks. Native
  in-game behavior remains unverified; this MD change requires a full restart.

## 2026-09-28 - construction-funding-only-for-active-builds

- READ: CE_Accounts keeps build-storage manager/account provisioning separate
  from transfers. Construction transfers now require queued/in-progress work and
  exclude exact-object InitialHub permission at generation 1, level 1, target 0.
  Station operating funds are unaffected. Idle storage, cargo and credits remain.
- MOCKED: tests reproduced seed/reset funding and idle top-ups from stale
  wantedmoney. Initial completion and recovery now receive no construction funds;
  upgrades, replacements and later discoveries retain funding. Idle leftovers
  survive reconciliation. The lifecycle funding fixture explicitly supplies an
  in-progress task rather than relying only on a positive wantedmoney value.
- VALIDATED: `just validate` passes 276 tests and XML/reference checks. No native
  game verification performed; a full restart is required for this MD change.

## 2026-09-29 - unowned-sector-race-fallback

- READ: an unowned start sector (e.g. Nopileos' Fortune VI, `Cluster_04_Sector002`,
  3.18B population, no vanilla `god.xml` station) resolved race `''`. No
  `ce_hub_` layout exists for it, so `$Construction.$Valid` stayed false and
  ReconcileSector reported `invalid_components` instead of creating a hub. A fresh
  game log had exactly one `race= plan=ce_hub_` block; that it is this sector is
  inferred (the message carries no sector name).
- IMPLEMENTED: `NearestOwnedRace` borrows the nearest reachable, non-hostile owned
  sector's race by `gatedistance` (-1 = unreachable); ties use `lookup.race.list`
  order. It logs `[CE] Unowned sector ... uses race ...`. The result is frozen in
  the sector profile like any owned race and does not change on later conquest.
- MOCKED: tests cover nearest pick, order-independent tie-breaks, hostile,
  unreachable and ownerless exclusion, and the isolated neutral fallback.
  Not measured in game: which race each unowned sector gets, and the startup
  cost of one galaxy scan with per-sector `gatedistance` per unowned sector.

## 2026-09-30 - nexus-create-file-returns-version-id

- MEASURED (live API, first CE upload): `POST /v3/mod-files` returned an `id`
  (`11420318055444`) that is the new file's first VERSION id, not the file id.
  `GET /v3/mod-files/{that id}/versions` returns 404; `GET
  /v3/mod-file-versions/{that id}` returns the version with the real file id
  under `file.id` (`8056605`). The published OpenAPI spec
  (`CreateModFileSuccess` -> `UploadModFile`) describes it as a file, so do not
  trust the spec here. `nexus_publish.py` resolves the file through the version.
- READ (spec): `POST /v3/mod-files/{id}/versions` returns `{file, version:{id}}`;
  not yet exercised live by CE.

## 2026-09-30 - release-zip-membership

- MEASURED: the game's `extensions/civilian_economy` is a Windows junction to
  this dev checkout, so in-game tests see the whole working tree, never the
  release ZIP. A file missing from the ZIP cannot show up in local testing.
  SUPERSEDED 2026-10-02: the mod moved to `src/`, the junction targets `src/`
  and the release is all of `src/`, so local tests and the ZIP see the same files.
- MEASURED (v0.1.0): the ZIP held 81 of 178 tracked files; all 97 exclusions
  were docs, tools, tests, scripts, images and repo metadata. Every `ui.xml`
  Lua file, cutscene video and icon texture resolved inside the ZIP.
- SOURCE: `MIT-LICENSE` ships from v0.1.1 on. Reconstructing the v0.1.0 ZIP
  with `publish-nexus v0.1.0` now fails membership verification, because the
  published v0.1.0 ZIP lacks the licence. That release is complete, so this only
  matters if it is ever re-published.

## 2026-10-01 - swi-sectors-have-no-population

- READ (SW Interworlds 0.9.1 HF, packed `ext_01`/`ext_02`): the `swi_galaxy_macro`
  galaxy has 220 single-sector clusters. Its `mapdefaults.xml` defines no
  `<system>`/`<planets>` and no sector `<worlds>`, and `maxpopulation` appears in
  no SWI file. `parameters.xml` does not patch `<workforce>`.
- INFERRED (same derivation as `vanilla-sector-populations.md`, not measured in a
  save): `GetSectorPopulation` is 0 in every SWI sector, so no SWI sector reaches
  CE's 100M hub threshold and the workforce growth bonus is +0%. Unless a running
  save shows otherwise, CE spawns no hubs under SWI without its own population
  source. List: `swi-sector-populations.md`.
- READ: SWI sets `<area>` economy/security/sunlight on cluster datasets only;
  economy is 1 in 184 of 220 sectors; 28 clusters set `factionlogic="false"`.

## 2026-10-01 - steam-workshop-publishing

- A Workshop item needs `content.xml` id `ws_<publishedfileid>` (Egosoft;
  confirmed by Chem O`Dun). CE keeps `civilian_economy` in the repo for Nexus and
  rewrites only the staged Workshop copy. Saves record the extension id, so Nexus
  and Workshop saves are not interchangeable.
- Only Egosoft's WorkshopTool (X Tools, appid 282160) can upload X4 items. There
  is no Web API upload, and SteamCMD `workshop_build_item` fails with "no
  workshop depot found" (X4 items are file-based). A SteamCMD login with the
  same account also logs the Steam client off ("Session Replaced").
- WorkshopTool 1.15 rules: the Steam client must be running and online
  ("No connection to Steam servers" otherwise); the folder must contain a
  catalog (`-buildcat` packs one); only `.cat .dat .cur .mkv .txt .pdf` plus the
  manifest upload, and `.mkv` only from the folder root (a `videos/` folder is
  rejected); `-batchmode` skips the prompt; `-minor` is required when the
  version is unchanged; `update` keeps the Steam title/description unless
  `-namedesc` is given; it rewrites the uploaded `content.xml` (`lastupdate`).
- The engine plays videos from the extension root (tested in game), so CE ships
  its MKVs there for both platforms. `ui.xml` and Lua inside `ext_01.cat` work
  (Mod Support APIs ships that way).
- Workshop dependency twins: UI Extensions is `ws_3477279743` (Valador's
  authorised upload); Verbose Transaction Log has no Workshop copy.
- Open: whether the Workshop installs the item as `extensions/civilian_economy`
  (WorkshopTool's default folder name). The video paths depend on it.

## 2026-10-02 - population-overrides

- IMPLEMENTED: per-save population overrides, used in place of native population
  wherever CE uses population. Layers: native < preset (shipped config, empty for
  now) < player < debug fixed 5B. Resolution happens only in
  `CE_PopulationOverrides.Effective`, called from `ReconcileSector` with the
  NATIVE value as input. Callers must never pass an already-resolved value:
  resolving twice adds anchored growth twice. The debug fixed value skips the
  resolver, so it is never recorded as a native baseline.
- Keys are `'$' + sector.macro.id`. A shipped config can name macros but not
  components. MD string table keys need the `$` prefix (see profile-key entry).
  A preset counts, and its options row is shown, only when its macro is in the
  macro -> sector map rebuilt by every `Reconcile`, so a TC preset is inert in a
  vanilla galaxy.
- Anchoring: effective = override + max(0, native - baseline). The baseline is
  the native reading when the value was saved or the preset first applied, and
  is filled from the first reading if none existed yet. Reason (READ, vanilla
  sweep 2026-10-01): vanilla population only grows (terraforming housing
  projects, two Cradle of Humanity story planets) and never decreases, so
  terraforming still counts on overridden sectors and lowering still works.
- A zero override is valid. Test override existence with `?`, never `@`, which
  treats 0 as absent.
- Hub creation needs no extra path: `Reconcile` already sends every galaxy
  sector to the Lua bridge, and an override of at least 100M passes the existing
  threshold in `ReconcileSector`.
- READ (Mod Support APIs v195, packed; loose copy in
  `.validation/settings-research-cache/`): `Update_Widget` never updates sliders.
  Its Lua checks `cell.type == "slider"` while native Helper tags them
  `"slidercell"`. CE previously relied on it to show rounded typed values; it now
  signals `Refresh_Menu`, which re-runs `onOpen`. Per-menu limits
  (widget_fullscreen.lua): 15 edit boxes, 40 dropdowns, 50 sliders, 170 rows;
  about 45 overrides fit in the slider budget. Dropdown options are tables; the
  confirm callback returns `$option_index` and the original `$option`, custom
  fields included. MD cannot parse text into numbers, so numeric input uses
  typed sliders, not edit boxes.
- READ (installed mods): `sort_list sortbyvalue="loop.element.idcode"` sorts by
  a string, so sector name sorting via `knownname` is expected to work. Not yet
  seen in game for `knownname`.
- MEASURED (debug.txt, 2026-10-05): a row holding a slider cannot hold any other
  interactive cell. The engine rejects the whole frame with `Invalid cell content
  [row: 16, col: 4]. Button defined although excluded by other row content. E.g.
  slidercell.` and the options page fails to open. Column numbers include the
  options page's extra back-arrow column. The rule is in engine C++, not the
  reference Lua, so a schema or Lua read cannot find it. Each slider row now has
  only a label beside it; its buttons go on the next row. `tests/mod` checks
  this for every built row.
- MEASURED (debug.txt + reported values, 2026-10-05): MD `(x)i` casts and plain
  integer literals are 32-bit and multiplication WRAPS silently, with no error.
  `((6182 + 0.5f)i) * 1000000` stored 1,887,032,704 (shown as 1.8B), and 38518 M
  wrapped to -136,705,664. Use largeint, as vanilla does: `(x)L * 1000000L`. The
  test runtime now models this: an `i` cast yields `Int32`, whose arithmetic with
  another 32-bit value wraps and with a larger int promotes. It reproduced both
  in-game values exactly before the fix.
- MEASURED (same log): a slider whose start is outside its min/max makes the engine
  reject the whole frame (`Start value is smaller than min select value`). Slider
  starts are now clamped, and `CE_PopulationOverrides.Repair` (start and load)
  drops saved player entries that are non-numeric, negative or above 100,000 M.
- MEASURED symptom, mechanism strongly INFERRED (debug.txt, 2026-10-05): MD null
  compares equal to 0. Through one code path guarded by `$Population != null`,
  `set 100000` applied immediately while `set 0` twice and a reset to a native 0
  were skipped (the reset applied 39 s later via the normal reconcile). The value
  was the only difference. No Egosoft documentation was found. Since MD booleans
  are 0/1, null presumably also equals `false`. Rule: to separate "unknown" from a
  real zero, use `typeof $x` then `.isnumeric`, never `!= null`. `CE_Settings`
  boolean validation is now typed for the same reason. The test runtime models
  `null == 0` (and booleans as integers). Swept 2026-10-05: the remaining six
  `!= null`/`== null` checks in `src/` compare objects (hubs, sequences), not
  numbers.
- Not yet tested in game: the population section's rendering after that fix,
  typed input up to 100000 in a slider, and hub creation from an override.

## 2026-10-06 - swi-lore-population-estimates

- `swi-sector-populations.md` now carries an ESTIMATED population per SWI sector
  (engine value stays 0): 36 Wookieepedia canon, 96 Legends, 82 tiers read from
  SWI's own sector descriptions, 1 placeholder (Andalia, no data, 1M), 5 SWI lore
  overrides; 101 of 220 reach CE's 100M hub threshold. Rule:
  canon infobox if numeric, else Legends; value nearest 4 ABY (SWI faction texts
  say "as of 4 ABY"); ranges by geometric mean. Judgement-based, not measured.
- READ: SWI economy is NOT a population signal. Economy 0 is set on populous
  worlds (Kuat, Baros, Rothana, Renatasia) as well as empty ones; SWI's 283
  `god.xml` economy filters (min 0.2/0.22/0.23) gate generic station placement.
- Wookieepedia gotchas (MEASURED over 220 names): a plain title can be a Legends
  article, marked `{{Top|leg}}` or `{{Top|canon=X}}` (11 of 220); names hit
  characters, stars, species or system pages without population, and planets
  often live under numbered titles (Telos IV, Garos IV, Rorak 4, Brentaal IV).
  Use the MediaWiki API (`starwars.fandom.com/api.php`, `prop=revisions`) with a
  User-Agent; infobox field is `|population=`, sub-bullets `**` are species splits.
- Plausibility check (2026-10-06, all 220): SWI's own 4 ABY text overrides
  Wookieepedia in 5 sectors (Kamino 1B, Anoat 100M, Quellor 10M, Jedha 100k,
  Gerrenthum 10k), since SWI's galaxy is the one played. A keyword scan of the
  descriptions is mostly noise: most hits were historical sentences ("remained
  uncolonized for millennia") or stray words, so read each matched sentence. 31 values are Essential Atlas c. 25 ABY figures, the
  only ones published. Sectors with SWI god.xml stations but <=10k people (22) are
  bases on empty worlds and agree with SWI's text.

## 2026-10-06 - x4-8.0-compatibility-diff

- MEASURED against an 8.00 text unpack (`$X4_TOOLKIT/reference-other/x4-v8.0`,
  Steam build 21408220) vs the 9.00 `reference/`. Recheck after any change.
- Blocker: native construction stages are 9.00-only. 8.00 `common.xsd` gives
  `add_build_to_expand_station` no `<stage>` child and an optional
  `constructionplan`. 8.00 `scriptproperties.xml` lacks
  `constructionsequence.hasstages/finalsequence/stage.*`. Vanilla 8.00 plans
  use no `bookmark` attribute (9.00: 165). `CE_ConstructionStages` and the
  bookmarked `ce_hub_<race>` master plans depend on all of these. Vanilla 8.00
  grows stations by passing a script-built sequence as `constructionplan`
  (`finalisestations.xml:333`).
- x4validate reports those `<stage>` lines on 8.00 only as INFO `xsd-strict`
  ("content type is empty"). On an older reference that is a missing feature,
  not schema over-strictness.
- Unchanged in 8.00: all `sel=` in the 11 patch files resolve, and all 7 merged
  AI/diplomacy patches are schema-clean. The 20 diplomacy
  `ActionN_SuccessCalculation[_v2]` names are identical. All 15 Lua FFI
  signatures, the 4 borrowed structs (TransactionLogEntry, WorkforceInfluence*)
  and the 6 wrapped menu functions are identical.
- Script versions in 8.00/9.00: move.generic 23/23, order.plunder 6/6,
  order.fight.attack.object 25/27. CE sets 28. A save made on 8.00 with CE
  would skip vanilla 9.00's sinceversion 26/27 patches when the game updates.
  v27 sets `$readmadscore`/`$incrementmadscore` on running attack orders.

## 2026-10-10 - map-sidebar-panel-needs-uix

- READ: vanilla `ui/addons/ego_detailmonitor/menu_map.lua` defines the left
  sidebar in a file-local `config.leftBar`; `createInfoFrame` handles only
  hardcoded `infoTableMode` values and otherwise draws an empty frame. A mod
  cannot add a sidebar panel without UI Extensions.
- READ: installed kuertee UI Extensions `menu_map.xpl` calls
  `createSideBar_on_start(config)` at the start of `createSideBar` with that local
  config, and `createInfoFrame_on_menu_infoTableMode(menu.infoFrame)` for unknown
  modes. galaxy_trader's `gt_info_menu.lua` uses the same two callbacks.
  `menu.registerCallback(name, fn, id)` ignores a second registration of an id.
- READ: `menu.viewCreated` binds info-frame tables positionally
  (`menu.infoTable, menu.infoTable2, menu.infoTable3`); vanilla `menu.onUpdate`
  calls `menu.infoFrame:update()` every frame, so function-valued cells stay live
  without rebuilds. `refreshInfoFrame` stores `menu.settoprow`; list builders
  consume it and reset it to nil.
- Icon `stationbuildst_habitation` (house in a ring) matches the ring frame of the
  `mapst_*` sidebar icons; `terraforming_population` and `gamestart_custom_people`
  have no ring. Textures live in `01.cat`.
- MEASURED in game (debug.txt): a text cell narrower than twice its x offset
  (`Helper.standardTextOffsetx` = 5) logs "Invalid fontstring descriptor:
  Invalid size.width-value", then "Content element is missing (nil)" for that
  cell, and the engine aborts the WHOLE frame ("Frame content of type 'table'
  was not created successfully"). Even an empty `createText('')` in a 3px
  column does this. Use a transparent `createIcon('solid', ...)` with an
  explicit width there; its `cellBGColor` still fills the full row height.
- READ (`menu_map.lua` `createPropertyRow`): vanilla's two-line list items are
  ONE selectable row. A transparent `createIcon('solid', {height=two lines})`
  spans the columns; `icon:setText("line1\nline2")` is the left text,
  `icon:setText2(..., {halign='right'})` the right text, names are shortened with
  `TruncateText(text, font, size, icon:getColSpanWidth() - offsets)` and the full
  name goes into the tooltip. Status bars accept a `y` offset, so a bar can sit on
  the second line.
- READ (`helper.lua` `addRow`, `initTableCell`): a row's `bgColor` is copied into
  every cell's `cellBGColor`, and `createText`/`createIcon` MERGE their properties
  onto that, so a row-level background reaches every cell unless one overrides it.
- MEASURED in game 2026-10-10: `cell:setBackgroundColSpan(n)` with the color on
  the first cell rendered SOME content cells inside the span black (a right-aligned
  number cell after a 2-column name, a right-aligned heading cell after a
  3-column title) while identical-looking rows rendered correctly. Root cause not
  determined (the engine side is not visible). Row-level `bgColor` is the reliable
  way to give a multi-column row one background.
- MEASURED in game 2026-10-10 (8,159 debug.txt lines in one session), cause READ
  in `helper.lua` (table `createDescriptor`, around line 5043): with
  `reserveScrollBar=false`, a table that ends up scrolling has its LAST column
  narrowed by `Helper.scrollbarWidth` at descriptor time, after cell content was
  sized from the un-narrowed widths. A `solid` icon spanning that column then logs
  "Widget system error. The given icon width for icon 'solid' exceeds the maximum
  available width (W) of the parent (W-12)" on every frame. Text cells do not log.
  Fix: `reserveScrollBar=true` (vanilla default), or keep icons out of the last
  column. Latent in the selected-hub bottom panel (`ce_map_status.lua`): its level
  overlay icon spans the last column with `reserveScrollBar=false`; not observed in
  that log, it needs the panel to scroll.
- Inline status icons used by vanilla lists: `\27[workshop_error]` (orange "!"
  alert), `\27[lso_error]`, `\27[lso_warning]`, `\27[lso_pause]`,
  `\27[menu_hourglass]`, `\27[menu_locked]`; they take the text color.
