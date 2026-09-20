"""Execute shipped map adapters with LuaJIT and strict table/engine stand-ins."""
from pathlib import Path
from xml.etree import ElementTree as E
from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
lua = LuaRuntime()
lua.globals().translations = lua.table_from({
    int(e.get('id')): ''.join(e.itertext()).replace(r'\n', '\n')
    for e in E.parse(ROOT / 't/0001-l044.xml').iter('t')
})
setup = r'''
now, reads, known, valid, legacy = 0, 0, true, true, false
hubs = {42, 43}
function snapshot(id, count)
    local s = {id, 1, 0, true, 60, 120, false, true, {}, false, 8524100000}
    for i=1,count do s[9][i] = {'Ware '..i, 500.5, 4000, 300, 200, 1000, 13000, 95, 99, 2, 2000} end
    return s
end
status, second = snapshot(42, 14), snapshot(43, 2)
statuses = {status, second}
picked, mouse = 42, true
local C = {
 GetPlayerID=function() return 1 end,
 IsValidComponent=function(id) return valid and id ~= 99 end,
 IsObjectKnown=function() return known end,
 GetPickedMapComponent=function(id) assert(id==9);return picked end,
}
package.loaded.ffi={C=C,cdef=function() end}
ConvertStringTo64Bit=tonumber
ConvertStringToLuaID=tonumber
GetNPCBlackboard=function(id,key)
 assert(id==1);reads=reads+1
 if key=='$ce_legacy_blocked' then return legacy end
 if key=='$ce_hubs' then return hubs end
 if key=='$ce_hub_statuses' then return statuses end
 error(key)
end
ReadText=function(page,id) assert(page==974201 and translations[id], tostring(id));return translations[id] end
getElapsedTime=function() return now end
GetComponentData=function(id,key) assert(key=='name');return 'Hub '..id end
GetRenderTargetMousePosition=function(id) assert(id==7);if mouse then return 10,10 end end
override, overrideCalls = nil, 0
SetMouseOverOverride=function(id,text) assert(id==7);override=text;overrideCalls=overrideCalls+1 end
DebugError=function() end
callbacks={}
RegisterEvent=function(event,fn) callbacks[event]=fn end
Register_OnLoad_Init=function(fn) loadCallback=fn end
Color={frame_background_semitransparent={},statusbar_value_default={},statusbar_marker_hidden={},icon_transparent={}}
nativeDraws, nativeUpdates, nativeCleanups = 0, 0, 0
menu={selectedcomponents={['42']=true}, selectedShipsTableData={fontsize=12,textHeight=20},
 infoTableOffsetX=10,infoTableWidth=250,borderOffset=2,map=7,holomap=9,
 createSelectedShips=function(frame) nativeDraws=nativeDraws+1; frame:addTable(1, {});return 'native' end,
 onUpdate=function()
  nativeUpdates=nativeUpdates+1
  if changeMode then menu.mode='diplomaticactionparam_object';changeMode=false end
  if menu.mode=='diplomaticactionparam_object' then override='native tooltip' end
  return 73
 end,
 cleanup=function() nativeCleanups=nativeCleanups+1;return 74 end}
Helper={viewWidth=1920,viewHeight=1080,borderSize=2,standardContainerOffset=4,
 headerRow1Font='bold',scaleX=function(x) return x end,
 getMenu=function(name) assert(name=='MapMenu');return menu end}
function newFrame()
 local f={tables={}}
 function f:addFrameBorder(name,p) assert(name=='selectedships');return {id=1} end
 function f:addTable(cols,p)
  local t={properties=p,rows={},columns=cols,widths={}}
  self.tables[#self.tables+1]=t
  function t:setColWidth(col,w) assert(col<=cols and w>0);self.widths[col]=w end
  function t:setDefaultBackgroundColSpan(a,b) assert(a==1 and b==cols) end
  function t:setDefaultCellProperties() end
  function t:setDefaultComplexCellProperties() end
  function t:getFullHeight() return #self.rows*20 end
  function t:addRow(data,props)
   assert(data==nil); local r={}
   for i=1,cols do
    local cell={handlers={}}
    function cell:setColSpan(n) assert(i+n-1<=cols);return self end
    function cell:createText(text,p) self.text=text;self.properties=p;return self end
    function cell:createButton(p) self.properties=p;return self end
    function cell:createIcon(icon,p) assert(icon=='solid');self.properties=p;self.kind='icon';return self end
    function cell:createStatusBar(p) self.properties=p;self.kind='bar';return self end
    function cell:getWidth()
     if t.widths[i] then return t.widths[i] end
     local used=2*(cols-1);for _,w in pairs(t.widths) do used=used+w end
     return t.properties.width-used
    end
    function cell:setText(text) self.text=text;return self end
    r[i]=cell
   end
   self.rows[#self.rows+1]=r;return r
  end
  return t
 end
 return f
end
function draw()
 local f=newFrame();menu.createSelectedShips(f);assert(#f.tables==1);return f.tables[1]
end
function value(cell) return type(cell.text)=='function' and cell.text() or cell.text end
'''
lua.execute(setup)
addon_files = [e.get('name') for e in E.parse(ROOT / 'ui.xml').iter('file')]
assert addon_files.index('ui/ce_hub_status.lua') < addon_files.index('ui/ce_map_status.lua')
english_ids = set(lua.globals().translations.keys())
for translation in (ROOT / 't').glob('*.xml'):
    assert {int(e.get('id')) for e in E.parse(translation).iter('t')} == english_ids
for name in ('ce_hub_status.lua', 'ce_map_status.lua'):
    lua.execute((ROOT / 'ui' / name).read_text(encoding='utf-8'))
lua.execute(r'''
local M=CEHubStatus
local s=M.get('42');assert(s and #s.wares==14 and s.population==8524100000)
assert(not M.get(77) and not M.get('invalid') and not M.get(0))
local before=reads;M.get(42);assert(reads==before)
now=1;M.get(42);assert(reads==before+3)
known=false;assert(not M.get(42));known=true
valid=false;assert(not M.get(42));valid=true
legacy=true;now=2;assert(not M.get(42));legacy=false;now=3
assert(M.population(8524100096)=='8.52 billion')
assert(M.population(1234567)=='1.23 million')
assert(M.population(1200000000000)=='1.20 trillion')
assert(M.population(999)=='999' and M.population(0)=='0' and M.population(nil)=='N/A')
local t=draw();assert(t.columns==6 and t.properties.tabOrder==21 and #t.rows==11)
assert(t.properties.y==1080-220-2-2-4)
assert(value(t.rows[2][2])=='1' and value(t.rows[2][5])=='8.52 billion')
assert(value(t.rows[6][1])=='Ware 1' and value(t.rows[10][1])=='Ware 5')
assert(value(t.rows[6][2])=='500.5 / 4000.0')
assert(value(t.rows[6][4])=='95.0%' and value(t.rows[6][6])=='99.0%')
assert(t.rows[6][3].kind=='bar' and t.rows[6][3].properties.current()==95)
assert(t.rows[6][5].properties.current()==99 and t.rows[6][5].properties.max==100)
assert(t.rows[6][3].properties.width==t.rows[6][4]:getWidth())
assert(value(t.rows[4][5])=='Collecting history')
assert(not t.rows[11][1].properties.active and t.rows[11][5].properties.active)
local hint=t.rows[6][1].properties.mouseOverText()
assert(hint:find('Consumption:',1,true) and not hint:find('Reliability',1,true))
assert(t.rows[6][4].properties.mouseOverText():find('90%',1,true))
assert(t.rows[6][6].properties.mouseOverText():find('15 minutes',1,true))
-- All rendered CE strings use printable ASCII, without pipe separators.
for _,r in ipairs(t.rows) do
 for _,cell in ipairs(r) do
  local v=value(cell)
  if v then assert(not v:find('[^ -~]') and not v:find('|',1,true),v) end
  local h=cell.properties and cell.properties.mouseOverText
  h=type(h)=='function' and h() or h
  if h then assert(#h<200 and not h:find('|',1,true),h) end
 end
end
-- Bar and number update together, without deriving history from the cleared backlog.
status[9][1][2]=0;status[9][1][8]=66.7;status[9][1][9]=25
now=4;menu.refreshMainFrame=nil;menu.onUpdate()
assert(not menu.refreshMainFrame)
assert(value(t.rows[6][2])=='0.0 / 4000.0' and value(t.rows[6][4])=='66.7%')
assert(value(t.rows[6][6])=='25.0%' and t.rows[6][5].properties.current()==25)
status[5]=0;now=5;assert(value(t.rows[6][4])=='N/A' and t.rows[6][3].properties.current()==0)
status[5]=120;status[9][1][8]=0;now=6
assert(value(t.rows[6][4])=='0.0%' and value(t.rows[4][5])=='Full window')
assert(menu.onUpdate()==73 and override=='Level: 1\nPopulation served: 8.52 billion')
picked=77;menu.onUpdate();assert(override==nil)
override='native hover';menu.onUpdate();assert(override=='native hover')
picked=42;menu.onUpdate();mouse=false;menu.onUpdate();assert(override==nil);mouse=true
picked=43;menu.onUpdate();assert(override=='Level: 1\nPopulation served: 8.52 billion');picked=42
t.rows[11][5].handlers.onClick();assert(menu.refreshMainFrame)
t=draw();assert(value(t.rows[6][1])=='Ware 6')
t.rows[11][5].handlers.onClick();t=draw();assert(value(t.rows[6][1])=='Ware 11')
assert(#t.rows==10 and not t.rows[10][5].properties.active)
t.rows[10][1].handlers.onClick();t=draw();assert(value(t.rows[6][1])=='Ware 6')
menu.selectedcomponents={['43']=true};t=draw();assert(value(t.rows[6][1])=='Ware 1')
menu.selectedcomponents={['42']=true};t=draw();assert(value(t.rows[6][1])=='Ware 1')
status[9][15]={'New ware',0,1,0,0,0,0,90,90,0,1};now=7
menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame)
menu.selectedcomponents={['42']=true,['43']=true};assert(draw().columns==1)
menu.selectedcomponents={['77']=true};assert(draw().columns==1)
menu.selectedcomponents={};assert(draw().columns==1)
menu.selectedcomponents={['42']=true}
status[4]=false;status[5]=0;now=8;t=draw()
assert(value(t.rows[3][2])=='Consumption paused')
statuses={second};now=9;menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame)
t=draw();assert(value(t.rows[3][2])==translations[68] and #t.rows==6)
assert(override=='Level: N/A\nPopulation served: N/A')
statuses={status,second};now=10;menu.onUpdate();t=draw()
status[5]=120;status[9][1][8]=nil;now=11;assert(value(t.rows[6][4])=='N/A')
menu.mode='diplomaticactionparam_object';menu.onUpdate()
assert(override=='native tooltip' and draw().columns==1)
menu.mode=nil;changeMode=true;menu.onUpdate();assert(override=='native tooltip');menu.mode=nil
menu.plotData={active=true};menu.onUpdate();assert(draw().columns==1)
menu.plotData=nil;menu.showMultiverse=true;assert(draw().columns==1);menu.showMultiverse=false
menu.onUpdate();known=false;menu.onUpdate();assert(draw().columns==1 and override==nil);known=true
menu.onUpdate();valid=false;menu.onUpdate();assert(draw().columns==1 and override==nil);valid=true
local wrapper=menu.onUpdate;callbacks.CEPopulationRequest();assert(menu.onUpdate==wrapper)
menu.onUpdate();assert(override)
assert(menu.cleanup()==74 and nativeCleanups==1 and override==nil)
before=reads;draw();assert(reads==before+3)
Helper.viewWidth=1280;t=draw();assert(t.properties.width==752 and t.properties.x==264)
status[4]=0;status[7]=1;now=12
assert(value(t.rows[3][2])=='Consumption paused' and value(t.rows[3][5])=='New offers paused')
for reason,label in pairs({constructing='constructing',damaged_modules='damaged modules',
 no_population='no population',owner_changed='ownership changed',hub_unavailable='hub unavailable',
 modules_unavailable='modules unavailable'}) do
 status[12]=reason;now=now+1
 assert(value(t.rows[3][2])=='Paused: '..label)
end
status[12]='future_reason';now=now+1;assert(value(t.rows[3][2])=='Consumption paused')
status[12]='constructing';status[4]=true;now=now+1
assert(value(t.rows[3][2])=='Consumption active')
''')
# Verify the deferred-load path independently of the already-registered menu.
deferred = LuaRuntime()
deferred.globals().translations = deferred.table_from({
    int(e.get('id')): ''.join(e.itertext()).replace(r'\n', '\n')
    for e in E.parse(ROOT / 't/0001-l044.xml').iter('t')
})
deferred.execute(setup)
deferred.execute("savedMenu=menu;menu=nil")
for name in ('ce_hub_status.lua', 'ce_map_status.lua'):
    deferred.execute((ROOT / 'ui' / name).read_text(encoding='utf-8'))
deferred.execute('''
assert(loadCallback);loadCallback();menu=savedMenu
callbacks.CEPopulationRequest();local wrapper=menu.onUpdate
loadCallback();callbacks.CEPopulationRequest();assert(menu.onUpdate==wrapper)
assert(draw().columns==6)
''')
print('Map status: metrics, identity, cache, pagination, refresh, percentage bars and native fallbacks passed')
