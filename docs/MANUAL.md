# Manual: Civilian Economy mod. People have desires too!

## Community

Join the [discord](https://discord.gg/TjyxU4TKGn) for feedback, feature
requests, bug reports and for coordinating contributions.


## The core idea is
- the mod adds civilian trade hub stations in each sector with a sizeable
  population
- these hubs represent the demand of the local population and generate buy
  orders for civilian goods. Prices are low, but demand is steady and
  independent of wars
- demand is proportional to the population size of the sector (which is a
  relatively hidden metric which otherwise controls workforce growth)
- if the sector is owned by the player, you gain an additional 15% on top of the
  transaction in sales tax


## Civilian hub level progression
- demand for goods starts simple (local food staple and water), but as demand is
  fulfilled, the station levels up, grows bigger and starts asking for more and
  different goods
- at higher levels, people demand higher level goods, first energy cells and
  meds and later high tech good like microchips or advanced electronics.
  Eventually, people will want exotic foods from other races across the galaxy
  and illicit goods for their decadent parties


## Bonuses from civilian relationships
- your good vibes with the local population give you bonuses depending on the
  local civilian hub level, as long as you keep their demands fulfilled.
- your connections can get you radar visibility of local NPC stations, increased
  odds for diplomatic missions, better prices, faster workforce growth or
  revealed lockbox locations in the sector of the hub


## Random events
- civilian demand gets influenced by random events:
  - a lost harvest can cause a temporary surge in food demand
  - a draught can cause sudden demand for water
  - industrial booms or slowdowns affect demand for refined metals or silicone
    wafers
  - and many more...


## Unrest
- Once a hub reaches level 5, the population gets dependent on you. If their
  demands are unsatisfied for too long, local unrest will rise.
- If unrest becomes too high, you start losing your tax income. Pirates will
  appear and start plundering or attacking stations.
- If unrest grows higher, they might start sabotaging your stations. First they
  might shut down production modules or eject cargo. Eventually they will start
  blowing up your station modules.


## Design Goals
The main purpose is to give the player another goal for trade, apart from your
own shipyard, for which there isn't really a good reason to have more than one
or to have it spread out. Now there's a reason to set up a galaxy wide logistics
network, warehouses, distribution, etc... to spread wares around and to buffer
the fluctuations from random events.

It also adds another purpose to owning sectors, particularly because the
population rich sectors are core sectors of other races like Argon Prime or
Earth. Suddenly these become tempting sectors to own. One of the largest
populations (Rhy's Defiance) needs to first be clawed back from Xenon control.

The mod relies on the in-game lore for population size and the race's local
foods. I hope this makes it work out of the box with mods that add sectors or
total conversions.


## Numbers
For those interested in numbers: The Argon Prime population, which is about
middle-ish, generates hourly demand worth about 150k Cr at level 1 and just over
6M Cr at level 10. And there's about 36 times the population of Argon Prime on
the whole galaxy. If you feel that's not enough, you can adjust global civilian
demand in the mod's settings.


## How to Trade with Civilian Hubs

Because civilians don't pay as high prices as the military complex, civilian
hubs tend to be neglected by profit-based autotraders (vanilla or mods). It's
therefore recommended to set up dedicated traders to serve the civilian hubs.

If you use vanilla-traders, the best way to do this is with repeat orders,
albeit setting this up is a bit cumbersome and wasteful because they don't take
demand into account.

If you allow trader mods, the far easier setup is to use the
[GalaxyTrader](https://www.nexusmods.com/x4foundations/mods/1857) mod, namely
their Mk2 Distribution trader with the following settings:
- Source Stations: your factories or trade hub
- Destination Stations: the civilian trade hub(s) you want to serve from these
  sources
- Min Storage: max
- Static Storage: 0
- Max Storage: 0
- Auto Wares: no (for some reason the ware discovery didn't work for me)
- Ware Filter: add your wares here
- Allow Illegal Wares: yes (to allow water trade)
- Allow Low Volume: yes
- Low Volume Floor: min

Beware that GalaxyTrader changes how trader experience works. But that can be
changed back to vanilla in the settings.

## Mod-Dependencies

1. SirNukes Mod support APIs -
   [Nexus page](https://www.nexusmods.com/x4foundations/mods/503) (required)

2. Kuertees UI Extensions and HUD -
   [Nexus page](https://www.nexusmods.com/x4foundations/mods/552) and Verbose
   transaction log -
   [Nexus page](https://www.nexusmods.com/x4foundations/mods/1317) (optional) -
   shows better transaction descriptions for civilian hib deliveries in the
   transaction log

## Links

- [Source Code on GitHub](https://github.com/stemps/x4-civilian-economy)

## Declaration of AI usage

Development of this mod makes use of AI for coding and in-game assets. I know
not everybody likes AI usage. That's totally fine. If that is that case, you
probably want to give this a pass.
