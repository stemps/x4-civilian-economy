"""LuaJIT menu tests with a mocked engine. Run: uv run --with lupa python tools/test_debug_menu.py"""
from pathlib import Path
from xml.etree import ElementTree as E
from lupa.luajit21 import LuaRuntime
root=Path(__file__).resolve().parents[1]
lua=LuaRuntime()
strings={int(e.get('id')):''.join(e.itertext()) for e in E.parse(str(root/'t/0001-l044.xml')).iter('t')}
lua.globals().translations=lua.table_from(strings)
lua.execute('''
marked, valid, legacy, progress, waiting = true, true, false, 0, false
calls, closes = 0, 0
entries, commands = {}, {}
status = {42, 1, 0, true, 60, 120, false, true,
    {{"Food Rations",500.5,4000,300,200,1000,13000,95,99,2,2000}}, false}
local C = {
 GetPlayerID=function() return 1 end,
 IsValidComponent=function() return valid end,
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
 if key=="$ce_hub" then return marked and 42 or nil end
 if key=="$ce_legacy_blocked" then return legacy end
 if key=="$ce_level_status" then return status end
 error(key)
end
ConvertStringToLuaID=tonumber
ConvertStringTo64Bit=tonumber
ReadText=function(_,id) assert(translations[id]);return translations[id] end
DebugError=function() end
AddUITriggeredEvent=function(screen,command,id)
 assert(screen=="CELevelTesting" and id==42);commands[#commands+1]=command
end
function open() entries={};callback() end
function action(id)
 for _,e in ipairs(entries) do if e.text==translations[id] then return e end end
 error("missing action "..id)
end
''')
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
valid=true;legacy=true;open();assert(#entries==0)
legacy=false;open();assert(#entries==7)
assert(entries[4].text == "Food Rations")
assert(entries[4].mouseOverText:find("95.0%",1,true))
assert(entries[4].mouseOverText:find("500.5",1,true))
assert(entries[4].mouseOverText:find("Reserved: 200",1,true))
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
status[1]=99;open();assert(#entries==3 and not action(40).active and not action(41).active)
''')
print('LuaJIT syntax, localized diagnostics, stale-object guards and testing commands passed')
