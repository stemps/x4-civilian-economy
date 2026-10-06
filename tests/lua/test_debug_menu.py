"""LuaJIT menu tests with a mocked engine. Run: uv run --with lupa python tools/test_debug_menu.py"""
from pathlib import Path
from xml.etree import ElementTree as E
from lupa.luajit21 import LuaRuntime
root=Path(__file__).resolve().parents[2]/'src'
lua=LuaRuntime()
strings={int(e.get('id')):''.join(e.itertext()) for e in E.parse(str(root/'t/0001-l044.xml')).iter('t')}
lua.globals().translations=lua.table_from(strings)
lua.execute('''
local nativeffi = require('ffi')
marked, valid, progress, waiting = true, true, 0, false
debugEnabled = nil
occupied, owner = {}, 'civilian'
calls, closes = 0, 0
entries, commands = {}, {}
status = {42, 1, 0, true, 60, 120, false, true,
    {{"Food Rations",500.5,4000,300,200,1000,13000,900.9,2000,"foodrations"}}, false, nil, nil, 3}
local C = {
 GetPlayerID=function() return nativeffi.new('uint64_t', 1) end,
 IsValidComponent=function() return valid end,
 IsObjectKnown=function() return true end,
 IsComponentClass=function(id, class) return id==80 and class=='sector' end,
 GetCurrentBuildProgress=function() return progress end,
 IsBuildWaitingForSecondaryComponentResources=function() return waiting end,
 ForceBuildCompletion=function(id) assert(id==42);calls=calls+1 end,
}
package.loaded.ffi={C=C,cdef=function() end}
menu={componentSlot={component=42},Add_Custom_Actions_Group=function() end,
 prepareActions=function() menu.actions={actions_ce_debug={}};entries=menu.actions.actions_ce_debug;callback();return nativeMenuResult end,
 registerCallback=function(_,fn) callback=fn end,
 insertInteractionGroup=function(parent,id,label) groups[id]={parent=parent,text=label} end,
 insertInteractionContent=function(section,e) e.section=section;entries[#entries+1]=e end,
 onCloseElement=function() closes=closes+1 end}
Helper={getMenu=function() return menu end}
GetNPCBlackboard=function(id,key)
 assert(type(id)=='number' and id==1, 'GetNPCBlackboard requires a converted Lua component ID')
 if key=="$ce_debug_enabled" then return debugEnabled end
 if key=="$ce_reset" then return resetState end
 if key=="$ce_hubs" then return marked and {42, 43} or {} end
 if key=="$ce_hub_sectors" then return occupied end
 if key=="$ce_hub_statuses" then return {status, {43, 5, 0, true, 0, 21600, false, true, {}, false, nil, nil, 3}} end
 error(key)
end
getElapsedTime=function() return 0 end
GetComponentData=function(id, key) assert(key=='owner');return owner end
ConvertStringToLuaID=function(value)
 if value=='1ULL' then return 1 end
 return tonumber(value)
end
ConvertStringTo64Bit=tonumber
ReadText=function(_,id) assert(translations[id]);return translations[id] end
DebugError=function() end
events={}
RegisterEvent=function(name, fn) events[name]=fn end
AddUITriggeredEvent=function(screen,command,id)
 assert(((screen=="CELevelTesting" or screen=="CEUnrestTesting" or screen=="CEWareTesting" or screen=="CEProgressTesting" or screen=="CEEventTesting") and id==42) or (screen=="CESectorTesting" and id==80) or (screen=='CEResetTesting' and (id==42 or id==80)));commands[#commands+1]=command
end
groups={}
function open() entries={};groups={};callback() end
function action(id)
 for _,e in ipairs(entries) do if e.text==translations[id] then return e end end
 error("missing action "..id)
end
''')
lua.execute((root/'ui/ce_hub_status.lua').read_text(encoding='utf-8-sig'))
lua.execute((root/'ui/ce_debug_reset.lua').read_text(encoding='utf-8-sig'))
source=(root/'ui/ce_debug_tools.lua').read_text(encoding='utf-8-sig')
lua.execute('assert(loadstring(...))',source)
lua.execute(source)
lua.execute('''
assert(callback)
-- Default-off covers hubs, sector creation and the placeholder fallback.
open();assert(#entries==0)
nativeMenuResult=false;assert(not menu.prepareActions())
menu.componentSlot.component=80;open();assert(#entries==0)
debugEnabled=1;open();assert(#entries==1)
local hiddenAction=entries[1];debugEnabled=false;hiddenAction.script();assert(#commands==0)
menu.componentSlot.component=42;debugEnabled=true;open()
hiddenAction=action(11);debugEnabled=0;hiddenAction.script();assert(calls==0)
open();assert(#entries==0)
debugEnabled=true
nativeMenuResult=false;assert(menu.prepareActions()==true)
marked=false;assert(menu.prepareActions()==false)
marked=true;nativeMenuResult=true;assert(menu.prepareActions()==true)
marked=false;open();assert(#entries==0)
marked=true;valid=false;open();assert(#entries==0)
valid=true;open();assert(#entries==17)
assert(entries[4].text == "Food Rations")
assert(entries[4].mouseOverText:find("Consumption:",1,true))
assert(entries[4].mouseOverText:find("500.5",1,true))
assert(entries[4].mouseOverText:find("Incoming: 200",1,true))
for _,e in ipairs(entries) do assert(#e.text <= 34 and not e.text:find("—",1,true)) end
assert(action(40).active)
local a=action(40);a.script();a.script();assert(#commands==1 and commands[1]=="queue_upgrade")
open();status[3]=2;action(40).script();assert(#commands==1)
open();assert(not action(40).active)
status[3]=0;status[2]=10;open();assert(not action(40).active)
status[2]=1;status[8]=false;open();assert(not action(40).active)
status[8]=true;status[4]=false;open();assert(not action(40).active)
status[4]=true;open();assert(action(41).active);action(41).script()
assert(commands[2]=="pause_offers")
status[7]=true;open();assert(action(42).active)
progress=-1;waiting=false;open();assert(not action(11).active)
waiting=true;open();assert(action(11).active)
a=action(11);valid=false;a.script();assert(calls==0)
valid=true;a.script();a.script();assert(calls==1)
-- Engine booleans may arrive as numbers.
status[4]=0;status[7]=0;open();assert(not action(40).active and action(41))
status[4]=1;status[8]=1;open();assert(action(40).active)
status[2]=nil;open();assert(not action(40).active)
status[2]=1
status[1]=99;open();assert(#entries==14 and not action(40).active and not action(41).active)
menu.componentSlot.component=43;open();assert(action(40).active)
assert(entries[1].text:find("Level 5",1,true))
menu.componentSlot.component=77;open();assert(#entries==0)
menu.componentSlot.component=42;status[1]=42;status[11]=18000000000;open()
assert(entries[4].text==translations[44])
assert(entries[4].mouseOverText:find('18000000000',1,true))

-- Display caching must never authorize a command after the underlying state changes.
CEHubStatus.reset()
status[3]=0;status[4]=true;status[8]=true
local cached=CEHubStatus.get(42)
assert(cached.available and cached.target==0)
open();local queued=action(40);local count=#commands
local previous=status;status={};for key,value in pairs(previous) do status[key]=value end
status[3]=2
assert(CEHubStatus.get(42).target==0)
queued.script();assert(#commands==count)
status[3]=0;open();queued=action(40)
status[13]=2;queued.script();assert(#commands==count)
status[13]=3;open();queued=action(40)
marked=false;queued.script();assert(#commands==count)
marked=true;status[13]=3
-- Fresh and cached consumers share named decoding, including test-only fields.
CEHubStatus.reset();status[10]=true
local display,fresh=CEHubStatus.get(42),CEHubStatus.getFresh(42)
assert(display.testUpgrade and fresh.testUpgrade)
assert(display.wares[1].reserve==fresh.wares[1].reserve)
assert(display.wares[1].key==fresh.wares[1].key)
''')
lua.execute('''
local function advance(level)
 for _,e in ipairs(entries) do if e.text==string.format(translations[124],level) then return e end end
 error('missing advance target')
end
status[2]=4;status[3]=0;status[4]=true;status[8]=false;status[10]=false
open();assert(not advance(4).active and advance(5).active and advance(10).active)
local a=advance(10);local count=#commands;a.script();a.script()
assert(#commands==count+1 and commands[#commands]=='advance_level_10')
open();a=advance(6);status[3]=5;a.script();assert(#commands==count+1)
local before=calls;events.CEAdvanceBuildReady(nil,42);assert(calls==before)
status[3]=10;status[10]=true;progress=0;waiting=false
events.CEAdvanceBuildReady(nil,42);assert(calls==before+1 and commands[#commands]=='advance_complete')
progress=-1;events.CEAdvanceBuildReady(nil,42);assert(calls==before+1)
progress=0;valid=false;events.CEAdvanceBuildReady(nil,42);assert(calls==before+1)
valid=true;status[2]=10;status[3]=0;events.CEAdvanceBuildReady(nil,42);assert(calls==before+1)
''')
lua.execute('''
-- Sector creation: native sector context, fresh occupancy, and one-shot callback.
menu.componentSlot.component=80;occupied={};nativeMenuResult=false
assert(menu.prepareActions()==true and #entries==1)
local create=action(138);local count=#commands
create.script();create.script();assert(#commands==count+1 and commands[#commands]=='create_hub_5b')
open();create=action(138);occupied={80};create.script();assert(#commands==count+1)
assert(menu.prepareActions()==false and #entries==0)
occupied={};open();create=action(138);valid=false;create.script();assert(#commands==count+1)
assert(menu.prepareActions()==false)
valid=true;occupied=nil;open();assert(#entries==0) -- backend not published yet
occupied={};menu.componentSlot.component=77;assert(menu.prepareActions()==false)
-- No initial-completion authorization in older snapshots, stale rows, or other hubs.
menu.componentSlot.component=42;status[2]=1;status[3]=0;status[10]=false;status[15]=false
local before=calls;progress=0;waiting=false
events.CEInitialBuildReady(nil,42);assert(calls==before)
status[17]=5000000000;status[18]=true;status[19]=true
open();assert(action(140) and action(141))
events.CEInitialBuildReady(nil,77);assert(calls==before)
owner='player';events.CEInitialBuildReady(nil,42);assert(calls==before)
owner='civilian';status[15]=true;events.CEInitialBuildReady(nil,42);assert(calls==before)
status[15]=false;status[3]=2;events.CEInitialBuildReady(nil,42);assert(calls==before)
status[3]=0;progress=-1;events.CEInitialBuildReady(nil,42);assert(calls==before)
waiting=true;events.CEInitialBuildReady(nil,42);assert(calls==before+1 and commands[#commands]=='initial_complete')
status[19]=false;events.CEInitialBuildReady(nil,42);assert(calls==before+1)
''')
lua.execute('''
status[20]={80,3,1,-1,{'Food Rations'},7};status[15]=false;debugEnabled=true;valid=true;marked=true
local expected={'stage_1','stage_2','stage_3','stage_4','clear','warning','raid_1','raid_2','raid_3',
 'production','turrets','cargo','shields','destroy','cooldowns'}
for i,command in ipairs(expected) do
 open();local entry=action(210+i);assert(entry.active)
 local count=#commands;entry.script();entry.script()
 assert(#commands==count+1 and commands[#commands]==command..':7')
end
open();local stale=action(224);status[20][6]=8;local count=#commands;stale.script();assert(#commands==count)
open();local disabled=action(217);debugEnabled=false;disabled.script();assert(#commands==count)
debugEnabled=true;status[15]=true;open();assert(not action(217).active)
status[15]=false
''')
lua.execute('''
status[2]=1;status[3]=0;status[4]=true;status[5]=60;status[6]=120
open()
assert(groups.actions_ce_debug_station.parent=='actions_ce_debug')
assert(groups.actions_ce_debug_wares.parent=='actions_ce_debug')
assert(groups.actions_ce_debug_unrest.parent=='actions_ce_debug')
assert(groups.actions_ce_debug_ware_foodrations.parent=='actions_ce_debug_wares')
assert(entries[1].section=='actions_ce_debug' and entries[4].section=='actions_ce_debug')
assert(action(11).section=='actions_ce_debug_station' and action(308).section=='actions_ce_debug_station')
assert(action(41).section=='actions_ce_debug_wares' and action(211).section=='actions_ce_debug_unrest')
assert(action(304).section=='actions_ce_debug_ware_foodrations')
local count=#commands;local add=action(304);add.script();add.script()
assert(#commands==count+1 and commands[#commands]=='random:foodrations:8')
open();action(305).script();assert(commands[#commands]=='zero:foodrations:8')
open();action(308).script();assert(commands[#commands]=='hour:8')
open();local zero=action(305);count=#commands;status[20][6]=9;zero.script();assert(#commands==count)
open();add=action(304);status[9][1][9]=0;add.script();assert(#commands==count)
open();assert(not groups.actions_ce_debug_ware_foodrations)
status[9][1][9]=2000;status[15]=true;open();assert(not action(308).active)
status[15]=false;status[5]=120;open();assert(not action(308).active)
status[5]=60;open();local progressAction=action(308);status[3]=2
progressAction.script();assert(#commands==count)
''')
lua.execute('''
status[3]=0;status[4]=true;status[14]=false;status[15]=false
status[21]={2,{{1,50,7200,'Food'},{3,25,6000,'Water'}},{5,6,7},12}
open();assert(groups.actions_ce_debug_events.text==translations[338])
local function eventAction(template,id)
 local label=string.format(translations[template],translations[320+id])
 for _,e in ipairs(entries) do if e.text==label then return e end end
 error('missing event '..id)
end
local function trigger(id) return eventAction(339,id) end
assert(action(340).active and eventAction(344,1).active and eventAction(344,3).active)
for i=1,11 do assert(trigger(i).active==(i>=5 and i<=7)) end
local count=#commands
trigger(1).script();assert(#commands==count)
local old=trigger(5);status[21][4]=13;old.script();assert(#commands==count)
open();local chosen=trigger(5);chosen.script();chosen.script()
assert(#commands==count+1 and commands[#commands]=='start:5:13')
open();eventAction(344,3).script();assert(commands[#commands]=='end:3:13')
open();action(340).script();assert(commands[#commands]=='end:0:13')
status[21][2]={};open();assert(not action(340).active)
status[15]=true;open();assert(not trigger(5).active)
status[15]=false;status[4]=false;open();assert(not trigger(5).active)
status[4]=true;open();old=trigger(5);debugEnabled=false;count=#commands
old.script();assert(#commands==count);debugEnabled=true
-- Obsolete single-event payloads provide no event data or commands.
status[21]={1,50,7200,'Food',{1,2},13};open();assert(not groups.actions_ce_debug_events)
assert(CEHubStatus.getFresh(42).demandEvents == nil)
status[21]=nil
''')
lua.execute('''
-- Layout planning is presentation only; it never grants force-finish permission.
status[2]=5;status[3]=10;status[4]=true;status[8]=false;status[15]=false
progress=-1;waiting=false;status[22]='layout_retry'
open();assert(action(346) and not action(11).active)
assert(action(11).mouseOverText==translations[348])
local s=CEHubStatus.getFresh(42)
assert(CEHubStatus.state(s)==translations[346])
assert(CEHubStatus.progress(s)==translations[346])
assert(CEHubStatus.action(s)==translations[346])
local sig=CEHubStatus.signature(s)
status[22]='planning';s=CEHubStatus.getFresh(42)
assert(CEHubStatus.state(s)==translations[345] and CEHubStatus.signature(s)~=sig)
status[22]='build_retry';assert(CEHubStatus.state(CEHubStatus.getFresh(42))==translations[347])
status[15]=true;assert(CEHubStatus.state(CEHubStatus.getFresh(42))==translations[88])
status[15]=false;status[22]=nil
assert(CEHubStatus.state(CEHubStatus.getFresh(42))==string.format(translations[99],10))
''')
lua.execute('''
resetState={1,false,'idle',0,0,false};debugEnabled=true
menu.componentSlot.component=80;occupied={80};nativeMenuResult=false
assert(menu.prepareActions()==true)
local count=#commands;local start=action(361)
start.script();start.script();assert(#commands==count+1 and commands[#commands]=='arm:1')
open();start=action(361);resetState[1]=2;start.script();assert(#commands==count+1)
resetState={2,false,'confirm',0,0,false};open()
local confirm=action(363);confirm.script();assert(commands[#commands]=='confirm:2')
open();confirm=action(363);count=#commands;debugEnabled=false;confirm.script();assert(#commands==count)
debugEnabled=true;menu.componentSlot.component=42;open();local old=action(11)
resetState={3,true,'removing',4,10,true};open();assert(#entries==2 and action(368))
local before=calls;old.script();assert(calls==before)
resetState[3]='initializing';open();assert(action(367))
debugEnabled=false;open();assert(#entries==0)
resetState=nil;debugEnabled=true

-- Designated (external) hubs: never force another mod's builds or queue CE plans;
-- level shortcuts stop at the registered maximum.
local function advance(level)
 local label=CEHubStatus.text(124, level)
 for _,e in ipairs(entries) do if e.text==label then return e end end
 error('missing advance '..level)
end
menu.componentSlot.component=42;status[1]=42;status[2]=3;status[3]=0;status[4]=true;status[8]=true;status[15]=false
progress=0;waiting=false
open();assert(action(11).active and action(40).active and advance(10).active)
status[24]={1,5};open()
assert(not action(11).active and not action(40).active)
assert(advance(4).active and advance(5).active and not advance(6).active and not advance(10).active)
local before=calls;action(11).script();assert(calls==before)
events.CEAdvanceBuildReady(nil,42);assert(calls==before)
status[2]=5;open();assert(not advance(6).active)
local s5=CEHubStatus.getFresh(42);assert(s5.external and s5.maxLevel==5 and CEHubStatus.classify(s5).maximum)
status[24]=nil;status[2]=1
''')
print('LuaJIT diagnostics, reset controls, debug events, nested actions, stale-token guards and build completion passed')
lua.execute('''
pauseEvents, nativePauses = {}, {}
productionMenu={buttonPauseProductionModules=function(modules,pause)
 nativePauses[#nativePauses+1]={modules,pause};return 'native result'
end}
Helper.getMenu=function(name) if name=='StationOverviewMenu' then return productionMenu end end
AddUITriggeredEvent=function(screen,command,id)
 assert(screen=='CEProductionPause' and command=='player');pauseEvents[#pauseEvents+1]=id
end
''')
lua.execute((root/'ui/ce_unrest.lua').read_text(encoding='utf-8'))
lua.execute('''
local wrapped=productionMenu.buttonPauseProductionModules
events.CEPopulationRequest();assert(wrapped==productionMenu.buttonPauseProductionModules)
assert(wrapped({101,102},true)=='native result')
assert(#pauseEvents==2 and pauseEvents[1]==101 and pauseEvents[2]==102 and #nativePauses==1)
wrapped({101},false);assert(#pauseEvents==3 and not nativePauses[2][2])
''')
print('Unrest production pause hook preserves native behavior and relinquishes CE ownership')
