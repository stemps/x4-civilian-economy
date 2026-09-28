"""Execute shipped map adapters with LuaJIT and strict table/engine stand-ins."""
from pathlib import Path
import os
from xml.etree import ElementTree as E
from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
lua = LuaRuntime()
lua.globals().translations = lua.table_from({
    int(e.get('id')): ''.join(e.itertext()).replace(r'\n', '\n').replace(r'\(', '(').replace(r'\)', ')')
    for e in E.parse(ROOT / 't/0001-l044.xml').iter('t')
})
setup = r'''
now, reads, known, valid = 0, 0, true, true
hubs = {42, 43}
function snapshot(id, count)
    local s = {id, 1, 0, true, 3600, 7200, false, true, {}, false, 8524100000, nil, 3, false, false, {'Energy Cells'}}
    for i=1,count do s[9][i] = {'Ware '..i, 500.5, 4000, 300, 200, 1000, 13000, 900.9+i, 2000, 'ware'..i} end
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
ConvertIntegerString=function(n,sep,precision,compact)
 assert(sep and precision==2 and compact)
 if n>=1000000 then return string.format('%.2f M',n/1000000) end
 if n>=10000 then return string.format('%.2f k',n/1000) end
 local result=tostring(math.floor(n));return result:reverse():gsub('(%d%d%d)','%1,'):reverse():gsub('^,','')
end
ConvertStringTo64Bit=tonumber
ConvertStringToLuaID=tonumber
GetNPCBlackboard=function(id,key)
 assert(id==1);reads=reads+1
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
GetTopRow=function(id) assert(id==21);if missingTable then return nil end;return liveTopRow or 7 end
DebugError=function() end
callbacks={}
RegisterEvent=function(event,fn) callbacks[event]=fn end
refreshRequests={}
AddUITriggeredEvent=function(screen,control,id)
 assert(screen=='CEHubStatus' and control=='refresh')
 refreshRequests[#refreshRequests+1]={id=id,time=now}
end
Register_OnLoad_Init=function(fn) loadCallback=fn end
Color={text_normal={},rowgroup_background_default={},row_title_background={},row_background={},text_negative={},text_warning={},text_positive={},frame_background_semitransparent={},statusbar_value_default={},statusbar_marker_hidden={},icon_transparent={}}
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
Helper={viewWidth=1920,viewHeight=1080,borderSize=2,standardContainerOffset=4,scrollbarWidth=16,
 headerRow1Font='bold',scaleX=function(x) return x end,
 getMenu=function(name) assert(name=='MapMenu');return menu end}
function newFrame()
 local f={tables={}}
 function f:addFrameBorder(name,p) assert(name=='selectedships');return {id=1} end
 function f:addTable(cols,p)
  local t={properties=p,rows={},columns=cols,widths={}}
  self.tables[#self.tables+1]=t
  function t:setColWidth(col,w) assert(col<=cols and w>0);self.widths[col]=w end
  function t:setDefaultBackgroundColSpan(a,b) assert(a==1 and b==5) end
  function t:setDefaultCellProperties() end
  function t:setDefaultComplexCellProperties() end
  function t:getRowHeight(index)
   local r=self.rows[index]
    local rowHeight=20
    for _,cell in ipairs(r) do
     -- Explicit wrapped-cell measurements, not a native font-layout emulator.
     if cell.properties.wordwrap then rowHeight=math.max(rowHeight,(wrappedRowHeights or {})[index] or 20) end
    end
   return rowHeight
  end
  function t:getFullHeight()
   local height=0
   for index in ipairs(self.rows) do height=height+self:getRowHeight(index) end
   return height + (self.columns==2 and (leftExtraHeight or 0) or 0)
  end
  function t:getVisibleHeight() return math.min(self:getFullHeight(),self.properties.maxVisibleHeight or math.huge) end
  function t:setTopRow(row) self.topRow=row end
  function t:addRow(data,props)
   assert(data==nil or data==true); local r={rowdata=data,properties=props}
   for i=1,cols do
    local cell={handlers={},properties={}}
    function cell:setColSpan(n) assert(i+n-1<=cols);return self end
    function cell:setBackgroundColSpan(n) assert(i+n-1<=cols);return self end
    function cell:createText(text,p) self.text=text;self.properties=p;self.kind="text";return self end
    function cell:createButton(p) self.properties=p;self.kind="button";return self end
    function cell:createIcon(icon,p) assert(icon=='solid');self.properties=p;self.kind='icon';return self end
    function cell:createStatusBar(p) assert(type(p.valueColor)=='table');self.properties=p;self.kind='bar';return self end
    function cell:getWidth()
     if t.widths[i] then return t.widths[i] end
     local used=2*(cols-1)+(t.properties.reserveScrollBar and Helper.scrollbarWidth or 0);for _,w in pairs(t.widths) do used=used+w end
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
 local f=newFrame();menu.createSelectedShips(f)
 assert(#f.tables==1, 'MapMenu.viewCreated requires exactly one selected table')
 -- Model the native frame validator, including disabled buttons on plain rows.
 for _,t in ipairs(f.tables) do
  if t.columns==5 then assertNativeTableFits(t) end
  for rowIndex,r in ipairs(t.rows) do
   for colIndex=1,t.columns do
    local cell=r[colIndex]
    if cell.kind=='button' and cell.properties.active~=false then
     assert(r.rowdata, 'Button defined in an unselectable row: '..rowIndex..':'..colIndex)
    end
   end
  end
 end
 -- Native callback positions: inserting tables here shifts the render-target ID.
 local function bind(...) local player,search,sidebar,rightbar,selected,top,map=...;return map end
 assert(bind(1,2,3,4,f.tables[1],6,7)==7)
 return f.tables[1]
end
function value(cell) return type(cell.text)=='function' and cell.text() or cell.text end
'''
# Execute the actual vanilla sizing functions so the mock cannot silently permit
# unselectable row groups which X4 refuses to scroll. No game files are modified.
reference = Path(os.environ.get('X4_REFERENCE', ROOT.parent.parent / 'reference'))
widget_source = (reference / 'ui/widget/lua/widget_fullscreen.lua').read_text(encoding='utf-8')
setup += '''
widgetSystem={}
local private={scaledSizes={table_borderSize=2,tableRowGroups_borderSize=4}}
GetTableNumRows=function(t) return #t.rows end
GetTableRowHeight=function(t,index) return t:getRowHeight(index) end
'''
for native_function in ('calculateFixedRowHeight', 'calculateMinRowHeight'):
    start = widget_source.index('function widgetSystem.' + native_function + '(')
    end = widget_source.index('\nfunction ', start + 1)
    setup += widget_source[start:end] + '\n'
setup += '''
function assertNativeTableFits(t)
 local element={numFixedRows=0,unselectableRows={},borderbelowrows={},paddingrows={},rowGroups={}}
 for i,r in ipairs(t.rows) do
  if r.properties.fixed then element.numFixedRows=i end
  if not r.rowdata then element.unselectableRows[i]=true end
  element.borderbelowrows[i]=r.properties.borderBelow
  element.paddingrows[i]={top=0,bottom=0}
 end
 local fixed=widgetSystem.calculateFixedRowHeight(t,element)
 local normal=widgetSystem.calculateMinRowHeight(t,element)
 local minimum=math.max(normal,35)+fixed -- native config.table.minScrollBarHeight
 local full=t:getFullHeight()
 local available=t:getVisibleHeight()
 local scrollbar=available<full and full>minimum
 local required=scrollbar and minimum or full
 assert(available>=required, 'Native table minimum height exceeds cap: '..available..' < '..required)
end
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
now=1;M.get(42);assert(reads==before+2)
known=false;assert(not M.get(42));known=true
valid=false;assert(not M.get(42));valid=true
now=3
local t=draw();assert(t.columns==5 and t.properties.tabOrder==21 and #t.rows==20)
assert(t.properties.y==1080-400-2-2-4-2)
assert(value(t.rows[2][1])=='Population 8.52 billion')
assert(value(t.rows[3][2])=='Level 1 (growing)' and t.rows[3][1].properties.current()==50)
assert(t.rows[3][2].properties.width==t.rows[3][2]:getWidth())
assert(value(t.rows[7][2])=='Ware 1' and value(t.rows[11][2])=='Ware 5')
assert(value(t.rows[7][3])=='16m' and value(t.rows[7][4])=='Supplied')
assert(value(t.rows[7][5])=='300')
for _,col in ipairs({2,3,4,5}) do assert(t.rows[7][col].kind=='text') end
assert(value(t.rows[6][5])=='Buying')
assert(t.rows[7][1].properties.width==t.rows[7][2]:getWidth()+Helper.borderSize+t.rows[7][3]:getWidth())
assert(t.rows[7][1].properties.start()==500.5/4000*100 and t.rows[7][1].properties.current()==700.5/4000*100)
assert(t.rows[7][1].properties.valueColor.b==140 and t.rows[7][1].properties.valueColor.glow==0)
assert(t.rows[7][1].properties.posChangeColor.g==85)
for _,col in ipairs({1,4,5}) do
 assert(t.rows[7][col].properties.cellBGColor==Color.rowgroup_background_default)
 assert(t.rows[6][col].properties.cellBGColor==Color.row_title_background)
end
assert(value(t.rows[4][1]):find('Energy Cells',1,true))
assert(t.properties.maxVisibleHeight==432 and t.properties.reserveScrollBar)
for i,r in ipairs(t.rows) do assert(r.properties.fixed==(i<=6)) end
assert(t.rows[7][2].properties.mouseOverText():find('Incoming: 200',1,true))
status[9][5][2]=0;status[9][5][8]=0;now=4
menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame)
t=draw();assert(value(t.rows[7][2])=='Ware 1' and value(t.rows[11][2])=='Ware 5')
assert(value(t.rows[11][3])=='Empty' and value(t.rows[11][4])=='Needed')
assert(t.rows[11][4].properties.color==Color.text_negative)
assert(value(t.rows[3][2])=='Level 1 (stagnating)')
assert(t.rows[3][2].properties.mouseOverText():find('Paused: missing supplies\n- Ware 5',1,true))
status[9][1][8]=899;now=5;t=draw()
assert(value(t.rows[7][4])=='Low' and t.rows[7][4].properties.color==Color.text_warning)
status[9][1][8]=900;now=6;t=draw();assert(value(t.rows[7][4])=='Supplied')
status[9][1][2]=9000;status[9][1][8]=16200;now=7
assert(value(t.rows[7][3])=='4h 30m' and t.rows[7][1].properties.current()==100)
assert(menu.onUpdate()==73 and override=='Level: 1\nPopulation served: 8.52 billion')
picked=77;menu.onUpdate();assert(override==nil)
override='native hover';menu.onUpdate();assert(override=='native hover')
picked=42;menu.onUpdate();mouse=false;menu.onUpdate();assert(override==nil);mouse=true
picked=43;menu.onUpdate();assert(override=='Level: 1\nPopulation served: 8.52 billion');picked=42
assert(value(t.rows[12][2])=='Ware 6' and value(t.rows[20][2])=='Ware 14')
menu.selectedShipsTable=21;liveTopRow=10;menu.onUpdate();t=draw();assert(t.topRow==10)
menu.selectedcomponents={['43']=true};t=draw();assert(value(t.rows[7][2])=='Ware 1' and t.topRow==7)
menu.selectedcomponents={['42']=true};t=draw();assert(value(t.rows[7][2])=='Ware 5')
status[9][15]={'New ware',0,1,1,0,0,0,0,1,'newware'};now=8
menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame)
menu.selectedcomponents={['42']=true,['43']=true};assert(draw().columns==1)
menu.selectedcomponents={['77']=true};assert(draw().columns==1)
menu.selectedcomponents={};assert(draw().columns==1)
menu.selectedcomponents={['42']=true}
status[4]=false;now=9;t=draw();assert(value(t.rows[3][2])=='Level 1 (stagnating)')
statuses={second};now=10;menu.onUpdate();t=draw();assert(value(t.rows[3][2])==translations[68])
statuses={status,second};now=11;menu.onUpdate();t=draw()
status[9][1][8]=nil;now=12;assert(M.get(42).stale and #M.get(42).wares==15)
assert(M.state(M.get(42))==M.text(88))
status[9][1][8]=900;now=13
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
before=reads;draw();assert(reads==before+2)
Helper.viewWidth=1280;t=draw();assert(t.properties.width==752 and t.properties.x==264)
for _,w in pairs(t.widths) do assert(w>0) end
assert(t.rows[7][5]:getWidth()>40)
status[4]=0;status[7]=1;now=14
assert(value(t.rows[3][2])=='Level 1 (stagnating)' and M.get(42).pausedOffers)
for reason,label in pairs({constructing='constructing',damaged_modules='damaged modules',
 no_population='no population',owner_changed='ownership changed',hub_unavailable='hub unavailable',
 modules_unavailable='modules unavailable'}) do
 status[12]=reason;now=now+1
 local expected=reason=='constructing' and M.text(372) or 'Paused: '..label
 assert(t.rows[3][2].properties.mouseOverText():find(expected,1,true))
end
status[4]=true;status[14]=true;now=now+1;assert(M.state(M.get(42))==M.text(89))
status[14]=false;status[15]=true;now=now+1;assert(M.state(M.get(42))==M.text(88))
status[15]=false;status[13]=2;now=now+1;assert(not M.get(42).available)
status[13]=3;status[3]=2;now=now+1;t=draw()
assert(value(t.rows[3][2])=='Level 1 (expanding)')
assert(t.rows[3][2].properties.mouseOverText()==M.text(99,2)..'\n\n'..M.text(372))
status[3]=0;status[2]=10;now=now+1;t=draw();assert(value(t.rows[3][2])=='Level 10 (maximum)')
status[9][1][4]=1485;now=now+1;assert(M.columns(M.get(42),M.get(42).wares[1])[4]=='1,485')
status[9][1][4]=57000;now=now+1;assert(M.columns(M.get(42),M.get(42).wares[1])[4]=='57.00 k')
status[9][1][4]=1500000;now=now+1;assert(M.columns(M.get(42),M.get(42).wares[1])[4]=='1.50 M')
status[9]={};now=now+1;t=draw();assert(value(t.rows[7][1])==M.text(71))
-- State codes drive labels, sort groups, colors and rebuilds independently of text.
local wareCases = {
 {0,0,0,'paused',57,'text_normal'},
 {1,0,0,'needed',94,'text_negative'},
 {1,1,899,'low',95,'text_warning'},
 {1,1,900,'supplied',96,'text_normal'},
 {1,10,36000,'full',97,'text_normal'},
}
for _,case in ipairs(wareCases) do
 local w={rate=case[1],reserve=case[2],remaining=case[3],capacity=10,key='test',name='Test'}
 assert(M.wareCode(w)==case[4] and M.wareState(w)==M.text(case[5]))
 assert(M.wareColor(w)==case[6])
end
local sample={id=42,available=true,level=1,target=0,active=true,growth=1,required=7200,
 plotReady=true,wares={{rate=1,reserve=0,remaining=0,capacity=10,key='test',name='Test'}}}
local neededSignature=M.signature(sample)
local oldNeeded,oldLow=translations[94],translations[95]
translations[94],translations[95]='same text','same text'
assert(M.signature(sample)==neededSignature)
sample.wares[1].reserve=1;sample.wares[1].remaining=899
assert(M.signature(sample)~=neededSignature)
translations[94],translations[95]=oldNeeded,oldLow
assert(M.classify(sample).growing and M.state(sample)==M.text(104))
sample.stale=true;sample.profileError=true;sample.target=2
assert(M.state(sample)==M.text(88) and M.progress(sample)==M.text(105))
assert(M.levelLabel(sample)==M.text(121,1,M.text(119)))
sample.stale=false;assert(M.state(sample)==M.text(89))
sample.profileError=false;sample.target=0;sample.growth=sample.required
sample.wares[1].reserve=0
assert(M.state(sample)==M.text(101)) -- ready takes precedence over shortage
sample.plotReady=false;assert(M.state(sample)==M.text(102))
sample.level=10;assert(M.state(sample)==M.text(100) and M.action(sample)==M.text(114))
-- Progress tooltips keep one status and never repeat instructions or missing goods.
assert(M.progressHint(nil)==M.text(68))
assert(M.progressHint(sample)==M.text(100))
sample.level=1;sample.growth=3600;sample.wares[1].reserve=1
assert(M.progressHint(sample)=='Progress toward level 2\nSupplied time: 1h 0m / 2h 0m\n\nStatus: Growing')
sample.wares[1].reserve=0
sample.wares[2]={rate=1,reserve=0,remaining=0,capacity=10,key='second',name='Second'}
assert(M.progressHint(sample)=='Progress toward level 2\nSupplied time: 1h 0m / 2h 0m\n\nPaused: missing supplies\n- Test\n- Second')
sample.active=false;sample.pauseReason='damaged_modules'
assert(M.progressHint(sample):find(M.text(83),1,true))
assert(not M.progressHint(sample):find('- Test',1,true))
sample.target=2;sample.pauseReason='constructing'
assert(M.progressHint(sample)==M.text(99,2)..'\n\n'..M.text(372))
for phase,id in pairs({planning=345,layout_retry=346,build_retry=347}) do
 sample.layoutPhase=phase
 assert(M.progressHint(sample)==M.text(99,2)..'\n\n'..M.text(id))
end
sample.layoutPhase=nil;sample.target=0;sample.pauseReason=nil;sample.active=true
sample.growth=sample.required
assert(M.progressHint(sample)==M.text(115,2)..'\n\n'..M.text(102))
sample.plotReady=true
assert(M.progressHint(sample)==M.text(115,2)..'\n\n'..M.text(101))
sample.stale=true
assert(M.progressHint(sample)==M.text(88))
sample.stale=false;sample.profileError=true
assert(M.progressHint(sample)==M.text(89))
''')
# Verify the deferred-load path independently of the already-registered menu.
deferred = LuaRuntime()
deferred.globals().translations = deferred.table_from({
    int(e.get('id')): ''.join(e.itertext()).replace(r'\n', '\n').replace(r'\(', '(').replace(r'\)', ')')
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
assert(draw().columns==5)
''')
# Native scrolling constraints: fixed headers, all wares present, bounded geometry.
deferred.execute('''
-- Exact reported budget with synthetic row measurements: 573 content / 572 cap.
status[2]=10;status[9]=snapshot(42,14)[9];now=now+1
Helper.viewHeight=1430;wrappedRowHeights={[1]=193}
local boundary=draw()
assert(boundary:getFullHeight()==573 and boundary:getVisibleHeight()==572)
status[2]=10;status[9]=snapshot(42,40)[9];now=now+1
wrappedRowHeights={[1]=41.25,[8]=60.5}
for _,height in ipairs({720,1080,1081,1432,1440,1513,1513.5}) do
 Helper.viewHeight=height
 local t=draw()
 assert(#t.rows==46 and t.properties.maxVisibleHeight==math.floor(height*0.4))
 assert(t:getFullHeight()==981.75 and t:getVisibleHeight()==math.floor(height*0.4))
 assert(t.properties.y%1==0)
 -- Conservative pixel budget: round space down and required content up.
 local available=math.floor(height-8-t.properties.y)
 assert(available>=math.ceil(t:getVisibleHeight())+2)
 for i,r in ipairs(t.rows) do
  assert(r.properties.fixed==(i<=6))
  assert(r.rowdata==(i>6 and true or nil) and r.properties.interactive==false)
  for col=1,5 do assert(r[col].kind~='button') end
 end
end
menu.selectedShipsTable=21;liveTopRow=35;menu.onUpdate()
local t=draw();assert(t.topRow==35)
missingTable=true;menu.onUpdate();t=draw();assert(t.topRow==35)
missingTable=false;liveTopRow=20;menu.onUpdate();t=draw();assert(t.topRow==20)
missingTable=true
menu.selectedcomponents={['43']=true};t=draw();menu.onUpdate();assert(draw().topRow==7)
menu.selectedcomponents={['42']=true};t=draw();menu.onUpdate();assert(draw().topRow==7)
missingTable=false;liveTopRow=35;menu.onUpdate()
status[9]=snapshot(42,6)[9];now=now+1;t=draw()
assert(#t.rows==12 and t.topRow==12 and value(t.rows[12][2])=='Ware 6')
assert(t:getVisibleHeight()==301.75)
assert(math.floor(Helper.viewHeight-8-t.properties.y)>=math.ceil(t:getVisibleHeight())+2)
wrappedRowHeights=nil
status[9]={};now=now+1;t=draw();assert(#t.rows==7 and t.topRow==7)
menu.cleanup();t=draw();assert(t.topRow==7)
''')
print('Map status: metrics, identity, cache, scrolling, refresh, reserve/growth bars and native fallbacks passed')

deferred.execute('''
status[20]={96,4,1,900,{'Food','Water'},3};now=now+1
local u=CEHubStatus.getFresh(42)
local text=CEHubStatus.unrest(u)
assert(text:find('Critical',1,true) and text:find('Food, Water',1,true) and text:find('15 min',1,true))
local t=draw();assert(value(t.rows[5][1]):find('Critical',1,true))
status[20][3]=-1;now=now+1
assert(CEHubStatus.unrest(CEHubStatus.getFresh(42)):find('recovering',1,true))
''')

deferred.execute('''
status[9]=snapshot(42,40)[9]
status[21]={2,{{8,75,7200,string.rep('Long material name, ',12)}},{1,2,8,9},7};now=now+1
for _,height in ipairs({720,1080,1440}) do
 Helper.viewHeight=height
 local t=draw()
 assert(#t.rows==47 and value(t.rows[7][5])=='Buying')
 assert(value(t.rows[6][1]):find('Industrial Boom',1,true))
 assert(value(t.rows[6][1]):find('+75%',1,true))
 assert(t.rows[6][1].properties.wordwrap)
 assert(t.rows[6][1].properties.mouseOverText():find('Long material name',1,true))
 assert(value(t.rows[5][1]):find('Critical',1,true))
 for i,r in ipairs(t.rows) do assert(r.properties.fixed==(i<=5)) end
 assert(t:getVisibleHeight()==height*0.4)
end
status[21][2][1][2]=-50;status[21][2][1][1]=9;now=now+1
assert(CEHubStatus.eventText(CEHubStatus.getFresh(42)):find('-50%',1,true))
status[15]=true;now=now+1
local t=draw();assert(value(t.rows[6][1]):find('Industrial Slowdown',1,true))
assert(value(t.rows[5][1])~='')
status[15]=false
menu.selectedShipsTable=21;liveTopRow=35;menu.onUpdate();t=draw();assert(t.topRow==35)
status[21]={2,{},{},8};now=now+1
menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame)
t=draw();assert(#t.rows==46 and value(t.rows[6][5])=='Buying')
status[21]={99,50,100,'bad',{},9};now=now+1
assert(not CEHubStatus.getFresh(42).demandEvents)
status[21]=nil;now=now+1;assert(draw().columns==5)
''')
print('Demand events: optional snapshots, summary row, warnings, long text and scrolling passed')

# Versioned multi-event payloads: stable ID order, independently live cells and scrollable rows.
deferred.execute('''
status[21]={2,{{8,75,7200,'Metals'},{3,50,5400,'Water'},{1,-25,3600,'Food'}},{5},10}
now=now+1
local t=draw()
assert(#t.rows==49 and t.topRow==6)
assert(value(t.rows[6][1]):find('Lost Harvest',1,true))
assert(value(t.rows[7][1]):find('Drought',1,true))
assert(value(t.rows[8][1]):find('Industrial Boom',1,true))
assert(value(t.rows[9][5])=='Buying' and value(t.rows[10][2])=='Ware 1')
for i,r in ipairs(t.rows) do assert(r.properties.fixed==(i<=5)) end
status[21][2][2][3]=4800;now=now+1
assert(value(t.rows[7][1]):find('1h 20m',1,true))
menu.selectedShipsTable=21;liveTopRow=25;menu.onUpdate();t=draw();assert(t.topRow==25)
status[21][2]={};for _,id in ipairs({1,3,4,5,6,7,8}) do
 status[21][2][#status[21][2]+1]={id,50,3600,string.rep('Long affected goods ',20)}
end
for _,height in ipairs({720,1080,1440}) do
 Helper.viewHeight=height;now=now+1;t=draw()
 assert(#t.rows==53 and t:getVisibleHeight()==height*0.4)
 for i,r in ipairs(t.rows) do assert(r.properties.fixed==(i<=5)) end
 assert(value(t.rows[13][5])=='Buying')
end
status[21][2]={{3,50,600,'Water'}};now=now+1
menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame)
t=draw();assert(#t.rows==47 and t.topRow==6)
status[21][2]={{3,50,600,'Water'},{3,50,600,'Water'}};now=now+1
assert(not CEHubStatus.getFresh(42).demandEvents)
status[21]={2,{}, {},12};now=now+1;t=draw();assert(#t.rows==46 and t.topRow==7)
''')
print('Concurrent events: current decoding, ID ordering, individual timers, seven scrollable events and debug actions passed')
lua.execute(r'''
menu.cleanup();refreshRequests={};now=1000
status,second=snapshot(42,14),snapshot(43,2);statuses={status,second}
menu.mode=nil;menu.selectedcomponents={['42']=true};known=true;valid=true
local t=draw()
assert(#refreshRequests==1 and refreshRequests[1].id==42)
menu.onUpdate();draw();assert(#refreshRequests==1)
now=1000.99;menu.onUpdate();assert(#refreshRequests==1)
now=1001;menu.onUpdate();assert(#refreshRequests==2)
-- Cache contains the old row set until the MD publication notification arrives.
local replacement=snapshot(42,14);replacement[9][1][2]=0;replacement[9][1][5]=15000
replacement[9][1][3]=60000;statuses={replacement,second}
assert(CEHubStatus.get(42).wares[1].incoming==200)
callbacks.CEHubStatusUpdated('CEHubStatusUpdated',42)
assert(CEHubStatus.get(42).wares[1].incoming==15000)
assert(t.rows[7][1].properties.start()==0 and t.rows[7][1].properties.current()==25)
replacement=snapshot(42,14);replacement[9][1][2]=0;replacement[9][1][5]=0
statuses={replacement,second};callbacks.CEHubStatusUpdated('CEHubStatusUpdated',42)
assert(t.rows[7][1].properties.current()==0)
menu.selectedcomponents={['43']=true};menu.onUpdate()
assert(#refreshRequests==3 and refreshRequests[3].id==43)
menu.selectedcomponents={};now=1003;menu.onUpdate();assert(#refreshRequests==3)
-- Hover alone never requests a snapshot.
picked=42;menu.onUpdate();assert(#refreshRequests==3)
menu.selectedcomponents={['43']=true};draw();assert(#refreshRequests==4)
changeMode=true;now=1005;menu.onUpdate();assert(#refreshRequests==4)
menu.mode=nil;draw();assert(#refreshRequests==5)
menu.cleanup();draw();assert(#refreshRequests==6)
valid=false;now=1007;menu.onUpdate();assert(#refreshRequests==6)
valid=true;draw();assert(#refreshRequests==7)
''')
print('Selected hub refresh: immediate requests, throttling, lifecycle and reservation cache invalidation passed')
