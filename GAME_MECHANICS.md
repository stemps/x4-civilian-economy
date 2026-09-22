# Game mechanics

This describes the current implementation, as inspected on 2026-09-22. It is a
source-based reference, not a record of in-game acceptance testing.

## Levels, demand and construction

The table lists **new demand unlocked at each completed level**, not the full
cumulative shopping list. Previously unlocked wares remain in demand and their
rates increase. Numbers in parentheses are units per game hour at the unlock
level, for a reference population of **8,524,100,000**. Each number applies to
the named ware individually.

All six races additionally unlock **water (2,000) at level 1**, **energy cells
(10,000) at level 2**, and **medical supplies (500) at level 3**. Those shared
unlocks are labelled "Shared" below. Boron workforce water is deduplicated with
the shared water requirement; it is not demanded twice.

Modules are the same Argon designs for every population race. Module totals
include structural connectors. The qualification column is the required rolling
supply-history window **at that level to qualify for the next level**; construction
time is additional.

| Level | Argon: new demand | Paranid: new demand | Teladi: new demand | Split: new demand | Boron: new demand | Terran: new demand | Modules added at this level (total) | Qualification for next level |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Food rations (2,000) + shared water | Soja husk (2,000) + shared water | Nostrop oil (2,000) + shared water | Chelt meat (2,000), scruffin fruits (2,000) + shared water | BoFu (2,000) + shared water | Terran MRE (2,000) + shared water | 1 dock, 1 base connector, 1 S container storage, 1 pier (**4**) | 2 game hours |
| 2 | Shared: energy cells | Shared: energy cells | Shared: energy cells | Shared: energy cells | Shared: energy cells | Shared: energy cells | 1 cross connector, 1 S container storage (**6**) | 3 game hours |
| 3 | Shared: medical supplies | Shared: medical supplies | Shared: medical supplies | Shared: medical supplies | Shared: medical supplies | Shared: medical supplies | 1 cross connector, 1 S container storage (**8**) | 4 game hours |
| 4 | Refined metals (300), silicon wafers (200) | Refined metals (300), silicon wafers (200) | Refined metals (300), silicon wafers (200) | Refined metals (300), silicon wafers (200) | Refined metals (300), silicon wafers (200) | Metallic microlattice (300) | 1 cross connector, 1 S container storage, 1 dock (**11**) | 5 game hours |
| 5 | Microchips (100) | Microchips (100) | Microchips (100) | Microchips (100) | Microchips (100) | Silicon carbide (200) | 1 cross connector, 1 S container storage (**13**) | 6 game hours |
| 6 | Scanning arrays (40), advanced composites (200) | Scanning arrays (40), advanced composites (200) | Scanning arrays (40), advanced composites (200) | Scanning arrays (40), advanced composites (200) | Scanning arrays (40), advanced composites (200) | No new ware | 1 cross connector, 1 S container storage, 1 pier (**16**) | 7 game hours |
| 7 | Advanced electronics (40) | Advanced electronics (40) | Advanced electronics (40) | Advanced electronics (40) | Advanced electronics (40) | Computronic substrate (40) | 1 cross connector, 1 S container storage, 1 dock (**19**) | 8 game hours |
| 8 | Foreign staples (500 each) | Foreign staples (500 each) | Foreign staples (500 each) | Foreign staples (500 each) | Foreign staples (500 each) | Foreign staples (500 each) | 1 cross connector, 1 S container storage (**21**) | 9 game hours |
| 9 | Spacefuel (100), spaceweed (100), maja dust (100) | Spacefuel (100), spaceweed (100), maja dust (100) | Spacefuel (100), spaceweed (100), maja dust (100) | Spacefuel (100), spaceweed (100), maja dust (100) | Spacefuel (100), spaceweed (100), maja dust (100) | Stimulants (100) | 1 cross connector, 1 S container storage (**23**) | 10 game hours |
| 10 | No new ware | No new ware | No new ware | No new ware | No new ware | No new ware | 1 cross connector, 1 S container storage, 1 dock, 1 pier (**27**) | Maximum level; no further upgrade |

At level 10 the plan contains 4 docks, 3 piers, 10 S container storage modules,
1 base connector and 9 cross connectors. It has no production or habitation
modules. "Dock" and "pier" refer to these exact module macros:

- Dock: `dockarea_arg_m_station_01_lowtech_macro`.
- Pier: `pier_arg_harbor_01_macro`.
- S container storage: `storage_arg_s_container_01_macro`.
- Base/cross connectors: `struct_arg_base_01_macro` / `struct_arg_cross_01_macro`.

## Foreign food and population profiles

"Foreign staples" means unique staple wares from other loaded races, excluding
water and medicines and any ware already in the local demand list. With the
relevant DLC installed, the vanilla staple pool is food rations, soja husk,
nostrop oil, chelt meat, scruffin fruits, BoFu and Terran MRE. Each profile omits
its own staples from the imports. For example, Split imports the five other
staples; Argon imports the six other staples. Each imported ware starts at
500 units/hour at level 8, before population scaling.

Local staples and medicines come from the game's currently loaded
`race.workforce.resources` definitions. This reads race requirements, not actual
station worker counts. The table shows vanilla defaults; mods can add or replace
them, introduce new races, and override the industrial/luxury lists. Missing
wares and non-container cargo are skipped. The non-Terran industrial/luxury list
and Terran alternative are explicit CE defaults, not native workforce requirements.

The sector owner's primary race is captured when its profile is first created
(or migrated from an older save) and retained after conquest or hub replacement.
It is a proxy for civilian culture, not a measured racial population breakdown.
Sector overrides can specify another race. An unknown race gets the default
common demands and available foreign staples, without an invented local staple.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the conversion adapter contract.

## Other level-dependent rules

| Mechanic | Current rule |
| --- | --- |
| Demand growth | Every ware's rate grows by **25% for each completed level after its unlock**, including levels with no new ware. |
| Population scaling | Rate is also multiplied by accessible sector population / 8,524,100,000. Population itself is not increased by leveling. |
| Backlog cap | Each ware's outstanding demand is capped at **two hours of its current rate**; the unit cap therefore rises with level. |
| Service threshold | A ware is considered well served while its backlog is at most **half an hour of its current rate**. The unit threshold rises with level. |
| Qualification/history window | `(current level + 1)` game hours: 2 hours at level 1 through 10 hours at level 9. At level 10, diagnostics/history still use 11 hours, but upgrades are disabled. |
| Operating funds | The target civilian account balance is twice the total value of all demand caps, equivalent to **four hours of current demand** at the offered prices. This grows with rates and unlocked wares. |
| Construction costs and capacity | Each level selects its cumulative construction plan. Added modules require native construction resources and add their native storage/docking capacity. Construction funding follows the build storage's requested budget. |
| Operational readiness | Every module required by the **completed** level must be operational. Damage or unavailability pauses demand and resets qualification. Unfinished expansion modules do not pause the still-operational completed level. |
| Upgrade activation | New rates and wares activate only after all target-level modules are operational. Queuing an expansion does not unlock them. Completing the upgrade resets qualification history. |
| Recovery and presentation | Replacement hubs use the retained earned level's construction plan. Hub names and status displays show the completed level. |

For a ware unlocked at level `U`, with baseline rate `B`, at completed level `L`
and population `P`:

```text
Hourly demand = B * (P / 8,524,100,000) * 1.25^(L - U)
Backlog cap  = 2 * hourly demand
```

For example, Argon food rations at the reference population rise from 2,000/hour
at level 1 to 2,500/hour at level 2 and approximately 14,901.16/hour at level 10.
An imported staple rises from 500/hour at level 8 to 781.25/hour at level 10.

The following rules stay fixed across levels:

- Each active ware must achieve at least **90% fulfillment** and **90% service
  reliability**, with no continuous shortage longer than **15 game minutes**,
  across the complete qualification window. Retired wares do not block upgrades;
  a profile with no active demand cannot qualify.
- Qualification requires an operational hub, no pending upgrade and a ready
  growth plot. The testing command can bypass supply qualification, but still
  queues normal construction.
- Offers use the ware's minimum price plus **10% of its min-to-max price range**,
  rounded up to a whole credit. There is no level-based price premium.
- Demand is virtual consumption; physical civilian cargo storage does not set
  the demand cap. Construction materials use native build storage separately.
- Hub creation/replacement requires **100 million accessible population**.
  Existing hubs below that threshold remain; zero population pauses them.
- The reserved growth envelope is fixed from the outset: at least 6 km in each
  X direction, 4 km in each Y direction and 16 km in each Z direction about the
  hub origin. Larger/off-center existing plots are preserved and extended as needed.
- Economy updates run every game minute; population reconciliation runs every
  five game minutes. These intervals do not shorten at higher levels.

Source files: `md/ce_population_profiles.xml`, `md/ce_ownerless_hub.xml`,
`libraries/constructionplans.xml`, and `tools/generate_plans.py`.
