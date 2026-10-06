# Client mods: designated civilian hubs

Your mod can place its own station and tell Civilian Economy (CE) to use it as the
civilian hub of its sector. CE then runs its full hub logic on that station: demand,
reserves, trade offers, growth, levels, sector events, unrest and bonuses.

CE never builds on, renames, repairs or replaces your station. Levels go up without
construction. If you want the station to grow visibly, react to the `level` event and
build it yourself.

## Requirements

- The station must exist and be owned by the `civilian` faction.
- One hub per sector. A sector that already has a CE hub refuses the registration.
- Give the station at least one free M dock so traders can deliver. Raids launch only
  from free external docks (tier 1: 1 M; tier 2: 2 M + 2 S; tier 3: also 1 L and
  4 S). Raids use the largest tier the docks allow and are skipped without an M dock.

## 1. Place the station (god.xml)

```xml
<!-- libraries/god.xml -->
<diff>
  <add sel="/god/stations">
    <station id="mymod_hub" race="teladi" owner="civilian" type="factory">
      <quotas><quota galaxy="1" zone="1" /></quotas>
      <location class="sector" macro="cluster_01_sector001_macro" />
      <position x="-60000" y="0" z="-120000" pitch="0" roll="0" yaw="0" />
      <station constructionplan="mymod_hub_plan" />
    </station>
  </add>
</diff>
```

## 2. Register it (MD)

Signal CE once. `check="false"` makes the call harmless when CE is not installed, so
CE can stay an optional dependency in your `content.xml`. CE stores the registration in
the save. Signalling again updates it.

```xml
<cue name="RegisterCivilianHub">
  <delay exact="1s"/>
  <actions>
    <signal_cue_instantly cue="md.CE_ExternalHubs.Register" check="false"
      param="table[$version=1, $godentry='mymod_hub', $population=1000000000,
                   $listener=md.MyMod.CivilianHubEvents]"/>
  </actions>
</cue>
```

| Field | Required | Meaning |
| --- | --- | --- |
| `$version` | yes | Always `1`. |
| `$godentry` or `$station` | one of them | The god.xml station id, or a station object for stations you create at runtime. |
| `$population` | no | Accessible population CE uses for this sector (0 to 100 billion). Many modded sectors have none, which pauses the hub. A player override in CE's options still wins. |
| `$race` | no | Race id for the demand basket (e.g. `'argon'`). The default is the sector owner's race, or the nearest owned sector's race. Only applies before the hub's basket is first fixed. |
| `$maxlevel` | no | Highest level the hub may reach (1-10, default 10). |
| `$listener` | no | A cue CE signals with events. |

## 3. Receive events (optional)

```xml
<cue name="CivilianHubEvents" instantiate="true">
  <conditions><event_cue_signalled/></conditions>
  <actions>
    <set_value name="$Event" exact="event.param"/>
    <do_if value="$Event.$event == 'level'">
      <!-- e.g. queue your own expansion for $Event.$newlevel on $Event.$station -->
    </do_if>
  </actions>
</cue>
```

Every event is `table[$version=1, $event, $godentry, $station, $sector, ...]`:

| `$event` | Extra fields | When |
| --- | --- | --- |
| `adopted` | `$level` | CE took over the station. |
| `rejected` | `$reason` | Before the first adoption: `invalid`, `not_found`, `owner` or `sector_has_hub`. CE keeps retrying every five minutes, except for `invalid`. |
| `level` | `$oldlevel`, `$newlevel` | The hub reached a new level. |
| `status` | `$operational`, `$reason` | The hub started or stopped operating. `$reason` is CE's pause reason, such as `active`, `damaged_modules`, `no_population` or `owner_changed`. |
| `lost` | `$level` | The station was destroyed. The sector keeps its level and waits. CE adopts the station again if the same god entry reappears. No `status` events are sent until then. |

## Notes

- CE checks the modules the station had when it was adopted. Modules you add later
  are ignored; if one of the original modules is destroyed, the hub pauses. Register
  again after rebuilding the station to capture its new layout.
- CE never builds its own hub in a designated sector, even after your station is gone.
- A CE debug reset restarts designated hubs at level 1, like every other hub. Your
  station is kept.
- Install your mod into a new game. When the sample was added to an existing save,
  god had not placed its station at load time, so CE reported `not_found` (it keeps
  retrying every five minutes).

## Sample mod

`samples/client-mod/` in the Civilian Economy repository is a complete minimal client.
It places a one-dock civilian station in Grand Exchange I, registers it with 1 billion
population and writes every event to the debug log as `[CE Sample] ...`. Developers can
link it into the game with `just sample-link` and validate it with
`just sample-validate`.
