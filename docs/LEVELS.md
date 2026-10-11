# Civilian hub level progression

Every civilian hub starts at level 1 and can grow to level 10. To level up, a
hub must have all of its demanded goods in stock for a number of game hours.
Each level adds new goods to the shopping list and unlocks or improves the
sector bonuses.

| Level | New goods demanded (budget per ware) | Workforce immigration | Trade prices | Diplomacy / espionage | Civilian sensor network | Discover lockboxes | Supplied time to next level |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Local food staple(s) (150k), water (75k) | - | - | - | - | - | 2 h |
| 2 | Energy cells (150k) | 10 | - | - | - | - | 3 h |
| 3 | Local medicine, medical supplies in vanilla (150k) | 20 | 2% | - | - | - | 4 h |
| 4 | Refined metals, silicon wafers (250k each); Terran: metallic microlattice | 30 | 4% | - | - | - | 5 h |
| 5 | Microchips (250k); Terran: silicon carbide. Unrest can now occur | 40 | 6% | +2% | - | - | 6 h |
| 6 | Scanning arrays, advanced composites (250k each); Terran: no new goods | 50 | 8% | +4% | - | - | 7 h |
| 7 | Advanced electronics (250k); Terran: computronic substrate | 60 | 10% | +6% | On | - | 8 h |
| 8 | Foreign staples, the staple foods of every other race (75k each) | 70 | 12% | +8% | On | - | 9 h |
| 9 | Spacefuel, spaceweed, maja dust (100k each); Terran: stimulants | 80 | 14% | +10% | On | On | 10 h |
| 10 | No new goods, existing demand keeps increasing | 90 | 16% | +12% | On | On | Maximum level |

## Reading the table

- **Goods** stay on the shopping list once unlocked. Their consumption grows by
  25% for every level gained after the unlock, so a ware unlocked at level 1 is
  consumed about 7.5 times faster at level 10.
- **Budgets** are credits per ware per game hour at the unlock level, for a
  sector with Argon Prime's population. Cheap goods are demanded in larger
  quantities than expensive ones. Demand scales with the sector's population
  and the global demand setting.
- **Local food and medicine** come from the race that owned the sector when the
  game started, for example food rations for Argon, soja husk for Paranid,
  nostrop oil for Teladi, chelt meat and scruffin fruits for Split, BoFu for
  Boron and Terran MRE for Terrans.
- **Supplied time** counts only game hours with all demanded goods in stock and
  is scaled by the time multiplier in the mod settings. Shortages pause
  progress but never reset it. Afterwards the hub expands; the new level, its
  goods and its bonuses activate once construction is complete.

## Bonuses

Bonuses only apply in the hub's own sector and only while all demanded goods
are in stock.

- **Workforce immigration:** extra workers per game hour per 1,000 habitat
  capacity at your stations in the sector. Only applies while native workforce
  is growing and never exceeds native limits.
- **Trade prices:** purchase discounts and sales commissions at docking-friendly
  NPC stations in the sector. The percentage applies to the ware's price range,
  not its current price. Ships and upgrades are excluded.
- **Diplomacy / espionage:** added to the success chance of station-targeted
  diplomacy operations in the sector, including against hostile stations. Still
  capped at 99%.
- **Civilian sensor network:** shares the radar of docking-friendly NPC stations
  throughout the sector. Undiscovered stations may become visible.
- **Discover lockboxes:** reveals lockbox locations in the sector, checked every
  5 minutes. Discovered locations stay visible when the bonus is inactive.
