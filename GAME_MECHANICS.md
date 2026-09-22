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

Modules use the population race captured at startup. Totals below count functional
modules only; the native layout generator adds racial connectors as needed.
Growth time means cumulative time with every required ware supplied; construction
time is additional. Shortages pause growth without erasing progress.

| Level | Argon: new demand | Paranid: new demand | Teladi: new demand | Split: new demand | Boron: new demand | Terran: new demand | Modules added at this level (total) | Supplied time for next level |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Food rations (2,000) + shared water | Soja husk (2,000) + shared water | Nostrop oil (2,000) + shared water | Chelt meat (2,000), scruffin fruits (2,000) + shared water | BoFu (2,000) + shared water | Terran MRE (2,000) + shared water | 1 dock, 1 container storage, 1 pier (**3**) | 2 game hours |
| 2 | Shared: energy cells | Shared: energy cells | Shared: energy cells | Shared: energy cells | Shared: energy cells | Shared: energy cells | 1 container storage (**4**) | 3 game hours |
| 3 | Shared: medical supplies | Shared: medical supplies | Shared: medical supplies | Shared: medical supplies | Shared: medical supplies | Shared: medical supplies | 1 container storage (**5**) | 4 game hours |
| 4 | Refined metals (300), silicon wafers (200) | Refined metals (300), silicon wafers (200) | Refined metals (300), silicon wafers (200) | Refined metals (300), silicon wafers (200) | Refined metals (300), silicon wafers (200) | Metallic microlattice (300) | 1 container storage, 1 dock (**7**) | 5 game hours |
| 5 | Microchips (100) | Microchips (100) | Microchips (100) | Microchips (100) | Microchips (100) | Silicon carbide (200) | 1 container storage (**8**) | 6 game hours |
| 6 | Scanning arrays (40), advanced composites (200) | Scanning arrays (40), advanced composites (200) | Scanning arrays (40), advanced composites (200) | Scanning arrays (40), advanced composites (200) | Scanning arrays (40), advanced composites (200) | No new ware | 1 container storage, 1 pier (**10**) | 7 game hours |
| 7 | Advanced electronics (40) | Advanced electronics (40) | Advanced electronics (40) | Advanced electronics (40) | Advanced electronics (40) | Computronic substrate (40) | 1 container storage, 1 dock (**12**) | 8 game hours |
| 8 | Foreign staples (500 each) | Foreign staples (500 each) | Foreign staples (500 each) | Foreign staples (500 each) | Foreign staples (500 each) | Foreign staples (500 each) | 1 container storage (**13**) | 9 game hours |
| 9 | Spacefuel (100), spaceweed (100), maja dust (100) | Spacefuel (100), spaceweed (100), maja dust (100) | Spacefuel (100), spaceweed (100), maja dust (100) | Spacefuel (100), spaceweed (100), maja dust (100) | Spacefuel (100), spaceweed (100), maja dust (100) | Stimulants (100) | 1 container storage (**14**) | 10 game hours |
| 10 | No new ware | No new ware | No new ware | No new ware | No new ware | No new ware | 1 container storage, 1 dock, 1 pier (**17**) | Maximum level; no further upgrade |

At level 10 a hub has 4 docks, 3 piers and 10 container storage modules, plus
connectors. It has no production or habitation modules. The smallest available
racial S/M dock, container storage and capital pier are selected through native
module definitions; connector choices also come from that race. Thus Terran hubs
use Terran components and their construction recipes. Native geometry determines
layout and connector counts, so total capacity and material costs vary by race.

Layouts are generated asynchronously: X4 prepares the layout in the background,
then CE validates it and queues normal construction. Expansion preserves the
completed layout. Missing components or failed layouts block construction with a
logbook diagnostic; they do not substitute another race's modules.

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

Every existing sector's owner primary race is captured at new-game initialization,
before checking population eligibility. Food, ware preferences and construction
components are saved once. Conquest, save/load, later population eligibility and
hub replacement do not change them. Sectors introduced later are captured when
first discovered. There are no sector-race overrides. An unknown race can have
common demand but cannot build without a valid racial component set.
This is a civilian culture proxy, not a measured racial population breakdown.
Race-level adapters remain available for mods and total conversions; see
[ARCHITECTURE.md](ARCHITECTURE.md). Changes to those definitions require a new game.
Existing hubs from older versions are not converted.

## Other level-dependent rules

| Mechanic | Current rule |
| --- | --- |
| Demand growth | Every ware's rate grows by **25% for each completed level after its unlock**, including levels with no new ware. |
| Population scaling | Rate is also multiplied by accessible sector population / 8,524,100,000. Population itself is not increased by leveling. |
| Reserve target | Each ware targets **two hours of its current rate**, rounded up. Buy offers replenish the shortfall; surplus deliveries are retained. |
| Growth time | `(current level + 1)` cumulatively supplied game hours: 2 hours at level 1 through 10 hours at level 9. No further growth at level 10. |
| Operating funds | The target civilian account balance is twice the total value of all reserve targets, equivalent to **four hours of current demand** at the offered prices. This grows with rates and unlocked wares. |
| Construction costs and capacity | Each level generates an extension of its completed layout. Added modules require native construction resources and add their native storage/docking capacity. Construction funding follows the build storage's requested budget. |
| Operational readiness | Every module required by the **completed** level must be operational. Damage or unavailability pauses consumption and growth without losing progress. Unfinished expansion modules do not pause the still-operational completed level. |
| Upgrade activation | New rates and wares activate only after all target-level modules are operational. Queuing an expansion does not unlock them. Completing the upgrade resets growth; reserves are retained and newly unlocked wares start empty. |
| Recovery and presentation | Replacement hubs rebuild the retained earned level using the saved racial components; reserves are lost, growth is retained. Hub names and status displays show the completed level. |

For a ware unlocked at level `U`, with baseline rate `B`, at completed level `L`
and population `P`:

```text
Hourly demand = B * (P / 8,524,100,000) * 1.25^(L - U)
Reserve target = ceil(2 * hourly demand)
```

For example, Argon food rations at the reference population rise from 2,000/hour
at level 1 to 2,500/hour at level 2 and approximately 14,901.16/hour at level 10.
An imported staple rises from 500/hour at level 8 to 781.25/hour at level 10.

The following rules stay fixed across levels:

- Growth advances only for time when all active required wares have reserves.
  Deliveries replenish reserves after elapsed consumption is settled; reservations
  alone supply nothing. A profile without active demand cannot qualify.
- Qualification requires an operational hub, no pending upgrade and a ready
  growth plot. The testing command can bypass the supplied-time requirement, but still
  queues normal construction.
- Offers use the ware's minimum price plus **10% of its min-to-max price range**,
  rounded up to a whole credit. There is no level-based price premium.
- Demand is virtual consumption; physical civilian cargo storage does not set
  the reserve target. Construction materials use native build storage separately.
- Hub creation/replacement requires **100 million accessible population**.
  Existing hubs below that threshold remain; zero population pauses them.
- The reserved growth envelope is fixed from the outset: at least 6 km in each
  X direction, 4 km in each Y direction and 16 km in each Z direction about the
  hub origin. Larger/off-center existing plots are preserved and extended as needed.
- Economy updates run every game minute; population reconciliation runs every
  five game minutes. These intervals do not shorten at higher levels.

Source files: `md/ce_population_profiles.xml`, `md/ce_ownerless_hub.xml`,
`md/ce_construction.xml`, and `md/ce_reserves.xml`.
