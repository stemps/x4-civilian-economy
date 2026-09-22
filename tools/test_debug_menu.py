"""LuaJIT menu tests with a mocked engine. Run: uv run --with lupa python tools/test_debug_menu.py"""
from pathlib import Path
from xml.etree import ElementTree as E
from lupa.luajit21 import LuaRuntime
root=Path(__file__).resolve().parents[1]
lua=LuaRuntime()
strings={int(e.get('id')):''.join(e.itertext()) for e in E.parse(str(root/'t/0001-l044.xml')).iter('t')}
lua.globals().translations=lua.table_from(strings)
lua.execute('''
marked, valid, progress, waiting = true, true, 0, false
calls, closes = 0, 0
entries, commands = {}, {}
status = {42, 1, 0, true, 60, 120, false, true,
    {{"Food Rations",500.5,4000,300,200,1000,13000,900.9,2000,"foodrations"}}, false, nil, nil, 3}
local C = {
 GetPlayerID=function() return 1 end,
 IsValidComponent=function() return valid end,
 IsObjectKnown=function() return true end,
 GetCurrentBuildProgress=function() return progress end,
 IsBuildWaitingForSecondaryComponentResources=function() return waiting end,
 ForceBuildCompletion=function(id) assert(id==42);calls=calls+1 end,
}
package.loaded.ffi={C=C,cdef=function() end}
menu={componentSlot={component=42},Add_Custom_Actions_Group=function() end,
 prepareActions=function() menu.actions={actions_ce_debug={}};entries=menu.actions.actions_ce_debug;callback();return nativeMenuResult end,
 registerCallback=function(_,fn) callback=fn end,
 insertInteractionContent=function(_,e) entries[#entries+1]=e end,
 onCloseElement=function() closes=closes+1 end}
Helper={getMenu=function() return menu end}
GetNPCBlackboard=function(id,key)
 assert(id==1)
 if key=="$ce_hubs" then return marked and {42, 43} or {} end
 if key=="$ce_hub_statuses" then return {status, {43, 5, 0, true, 0, 21600, false, true, {}, false, nil, nil, 3}} end
 error(key)
end
getElapsedTime=function() return 0 end
ConvertStringToLuaID=tonumber
ConvertStringTo64Bit=tonumber
ReadText=function(_,id) assert(translations[id]);return translations[id] end
DebugError=function() end
RegisterEvent=function() end
AddUITriggeredEvent=function(screen,command,id)
 assert(screen=="CELevelTesting" and id==42);commands[#commands+1]=command
end
function open() entries={};callback() end
function action(id)
 for _,e in ipairs(entries) do if e.text==translations[id] then return e end end
 error("missing action "..id)
end
''')
lua.execute((root/'ui/ce_hub_status.lua').read_text(encoding='utf-8-sig'))
source=(root/'ui/ce_debug_tools.lua').read_text(encoding='utf-8-sig')
lua.execute('assert(loadstring(...))',source)
lua.execute(source)
lua.execute('''
assert(callback)
nativeMenuResult=false;assert(menu.prepareActions()==true)
marked=false;assert(menu.prepareActions()==false)
marked=true;nativeMenuResult=true;assert(menu.prepareActions()==true)
marked=false;open();assert(#entries==0)
marked=true;valid=false;open();assert(#entries==0)
valid=true;open();assert(#entries==7)
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
status[1]=99;open();assert(#entries==4 and not action(40).active and not action(41).active)
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
print('LuaJIT syntax, localized diagnostics, stale-object guards and testing commands passed')
