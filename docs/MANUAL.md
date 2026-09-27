# Manual: Civilian Economy mod. People have desires too!

It always bummed me out a bit that the only economy in X4 is essentially
shipbuilding fueled by war. This always led my playthroughs to strive for
maximum galactic turmoil with one giant shipyard feeding all warring factions
which then fight it out right outside my docks. I'm not complaining... it's fun!
But I wanted more and different incentives for my galactic empire.

## How it Works
- At game start, or when you add the mod to an existing game, neutral plots for
  civilian trade hub stations appear in each sector with a sizeable population
- These civilian trade hubs represent the demand of the local population and
  generate buy orders for civilian goods. Prices are low, but demand is steady,
  proportional to the population size and independent of wars
- If the sector is owned by the player, you gain an additional 15% on top of the
  transaction in sales tax
- Demand for goods starts simple (local food staple and water), but as demand is
  fulfilled, the station levels up, starts a construction phase to grow bigger
  and then asks for more and different goods
- As it levels up, it adds demand for energy cells and meds and eventually high
  tech good like microchips or advanced electronics and exotic foods from other
  races and eventually illicit goods for their luxurious parties
- Your good relationship with the local population give you bonuses depending on
  the local civilian hub level. Your connections can get you radar visibility of
  local NPC stations, increased odds for diplomatic missions, better prices,
  faster workforce growth, revealed lockbox locations, ...
- once a hub reaches level 5, the population gets dependent. If their demands
  are unsatisfied for too long, local unrest will arise resulting in lost tax
  income, pirate raids or eventually sabotage against your stations. First they
  will shut down production modules or eject cargo and eventually they will
  start blowing up your station modules.


The main purpose is to give the player another goal for trade, apart from your
own shipyard, for which there isn't really a good reason to have more than one
or to have it spread out. Now there's a reason to set up a galaxy wide logistics
network, warehouses, distribution, ...

It also adds another porpose to owning sectors, particularly because the
population rich sectors are core sectors of other races like Argon Prime or
Earth. Suddenly these become tempting sectors to own. One of the largest
populations (Rhy's Defiance) needs to first be clawed back from Xenon control.

## Mechanics
The mod relies on the in-game lore for population size and the race's local
foods. I hope this makes it work out of the box with mods that add sectors or
total conversions.

This mod adds additional mechanics and more economic demand, which likely causes
notable changes to the game balance. I tried to design it responsibly, but you
have been warned.

## Numbers

For those interested in numbers: The Argon Prime population, which is about
middle-ish, generates per hour about 150k Cr worth of demand at level 1 and just
over 6M Cr at level 10. And there's about 36 times the population of Argon Prime
on the whole galaxy.

## Mod-Dependencies

1.
[SirNukes Mod support APIs](https://www.nexusmods.com/x4foundations/mods/503)
(optional) - if you want to use the debug menu for mod-testing

2. [Verbose transaction log](https://www.nexusmods.com/x4foundations/mods/1317)
   (optional) - shows better transaction descriptions for civilian hib
   deliveries in the transaction log

## Q&A
Q: Why should the player get sector bonuses for demand fulfilled by NPCs?


## Links

- [Source Code on GitHub](https://github.com/stemps/x4-civilian-economy)

## Declaration of AI usage

Development of this mod makes use of AI, based on the excellent
[X4 Claude Modding Tool](https://www.nexusmods.com/x4foundations/mods/2186) by
[ttyyygggg](https://www.nexusmods.com/profile/ttyyygggg). I simply wouldn't have
had the time to build this otherwise. Not everybody likes AI usage. That's
totally fine. If that is that case, you probably want to give this a pass.
