"""Execute shipped map adapters with LuaJIT and strict table/engine stand-ins."""
from pathlib import Path
import os
from xml.etree import ElementTree as E
from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / 'src'
UI_FILES = ('ce_hub_status.lua', 'ce_reward_status.lua', 'ce_hub_sections.lua', 'ce_map_status.lua')
lua = LuaRuntime()
lua.globals().translations = lua.table_from({
    int(e.get('id')): ''.join(e.itertext()).replace(r'\n', '\n').replace(r'\(', '(').replace(r'\)', ')')
    for e in E.parse(MOD / 't/0001.xml').iter('t')
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
 GetTextHeight=function(text,font,size,width) assert(text==' \n ' and width==0);return 38 end,
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
local componentData={name=function(id) return 'Hub '..id end,icon=function() return 'mapob_station' end,
 idcode=function(id) return 'ABC-'..id end}
GetComponentData=function(id,...)
 local result={}
 for i,key in ipairs({...}) do assert(componentData[key], key);result[i]=componentData[key](id) end
 return unpack(result)
end
-- Character budget stand-in for native text measurement.
TruncateText=function(text,font,size,width)
 local budget=math.floor(width/7)
 if #text<=budget then return text end
 return text:sub(1,budget-3)..'...'
end
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
Color=setmetatable({}, {__index=function(t,key)
 for _,known in ipairs({'text_inactive','text_normal','text_lowlight','text_negative','text_warning','text_positive',
  'rowgroup_background_default','row_title_background','row_background','row_background_blue',
  'frame_background_semitransparent','statusbar_marker_hidden','icon_transparent'}) do
  if key==known then rawset(t,key,{name=key});return rawget(t,key) end
 end
 error('unknown color '..tostring(key))
end})
nativeDraws, nativeUpdates, nativeCleanups = 0, 0, 0
menu={selectedcomponents={['42']=true},
 infoTableOffsetX=10,infoTableWidth=250,borderOffset=2,map=7,holomap=9,
 createSelectedShips=function(frame) nativeDraws=nativeDraws+1; frame:addTable(1, {});return 'native' end,
 onUpdate=function()
  nativeUpdates=nativeUpdates+1
  if changeMode then menu.mode='diplomaticactionparam_object';changeMode=false end
  if menu.mode=='diplomaticactionparam_object' then override='native tooltip' end
  return 73
 end,
 cleanup=function() nativeCleanups=nativeCleanups+1;return 74 end,
 getObjectColor=function(id) return {name='objectcolor'..id} end}
Helper={viewWidth=1920,viewHeight=1080,borderSize=2,standardContainerOffset=4,scrollbarWidth=16,
 standardFont='std',standardFontBold='bold',standardFontSize=9,standardTextHeight=20,standardTextOffsetx=5,
 headerRow1Font='header',headerRow1FontSize=12,headerRow1Height=30,
 scaleFont=function(font,size) return size end,scaleX=function(x) return x end,scaleY=function(y) return y end,
 convertColorToText=function(c) return '<'..c.name..'>' end,
 getMenu=function(name) assert(name=='MapMenu');return menu end}
function newFrame()
 local f={tables={}}
 function f:addFrameBorder(name,p) assert(name=='selectedships');return {id=1} end
 function f:addTable(cols,p)
  local t={properties=p,rows={},columns=cols,widths={}}
  self.tables[#self.tables+1]=t
  function t:setColWidth(col,w) assert(col<=cols and w>0);self.widths[col]=w end
  function t:setDefaultCellProperties() end
  function t:setDefaultComplexCellProperties() end
  -- Measured row heights: text minRowHeight (else 20), explicit icon/button heights,
  -- and explicit wrapped-cell measurements. Not a native font-layout emulator.
  function t:getRowHeight(index)
   local r=self.rows[index]
   local rowHeight=0
   for _,cell in ipairs(r) do
    local p=cell.properties
    if cell.kind=='text' then
     local h=p.minRowHeight or 20
     if p.wordwrap and (wrappedRowHeights or {})[index] then h=math.max(h,wrappedRowHeights[index]) end
     rowHeight=math.max(rowHeight,h)
    elseif cell.kind=='icon' or cell.kind=='button' then rowHeight=math.max(rowHeight,p.height or 20) end
   end
   return rowHeight>0 and rowHeight or 20
  end
  function t:getFullHeight()
   local height=0
   for index in ipairs(self.rows) do height=height+self:getRowHeight(index) end
   return height
  end
  function t:getVisibleHeight() return math.min(self:getFullHeight(),self.properties.maxVisibleHeight or math.huge) end
  function t:setTopRow(row) self.topRow=row end
  function t:addRow(data,props)
   assert(data==nil or data==true); local r={rowdata=data,properties=props}
   local rowIndex=#self.rows+1
   function r:getHeight() return t:getRowHeight(rowIndex) end
   for i=1,cols do
    -- Vanilla addRow copies the row bgColor into each cell; create* merges properties.
    local cell={handlers={},properties={cellBGColor=props and props.bgColor}}
    local function apply(self,p) for k,v in pairs(p or {}) do self.properties[k]=v end end
    function cell:setColSpan(n) assert(i+n-1<=cols);self.span=n;return self end
    function cell:setBackgroundColSpan(n) assert(i+n-1<=cols);self.bgSpan=n;return self end
    function cell:getColSpanWidth()
     local width=2*((self.span or 1)-1)
     for c=i,i+(self.span or 1)-1 do width=width+r[c]:getWidth() end
     return width
    end
    function cell:createText(text,p)
     -- Native text cells subtract their x offset on both sides; a narrower cell
     -- makes an invalid fontstring and the engine aborts the whole frame.
     assert(self:getColSpanWidth()>2*Helper.standardTextOffsetx, 'text cell too narrow at column '..i)
     self.text=text;apply(self,p);self.kind="text";return self
    end
    function cell:createButton(p) apply(self,p);self.kind="button";return self end
    function cell:createIcon(icon,p) assert(icon=='solid' and p.height>0);apply(self,p);self.kind='icon';return self end
    function cell:createStatusBar(p) assert(type(p.valueColor)=='table');apply(self,p);self.kind='bar';return self end
    function cell:getWidth()
     if t.widths[i] then return t.widths[i] end
     local used=2*(cols-1)+(t.properties.reserveScrollBar and Helper.scrollbarWidth or 0);for _,w in pairs(t.widths) do used=used+w end
     return t.properties.width-used
    end
    function cell:setText(text,p) self.text=text;self.textProps=p or {};return self end
    function cell:setText2(text,p) self.text2=text;self.text2Props=p or {};return self end
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
  if t.columns==7 then assertNativeTableFits(t) end
  for rowIndex,r in ipairs(t.rows) do
   -- widget_fullscreen.lua: every cell paints its own color, and its background only
   -- widens over the 2px gap to the next cell inside a background colspan. A colored
   -- row therefore needs one span from its first colored cell to the last column,
   -- with the same color in every covered cell, or the gaps show.
   if r.properties.bgColor and r.properties.bgColor~=Color.row_background then
    local first
    for c=1,t.columns do if r[c].properties.cellBGColor==r.properties.bgColor then first=c;break end end
    if first then
     assert(r[first].bgSpan and first+r[first].bgSpan-1==t.columns, 'visible cell gaps: no background span in row '..rowIndex)
     for c=first,t.columns do assert(r[c].properties.cellBGColor==r.properties.bgColor, 'mixed backgrounds in span: row '..rowIndex..':'..c) end
    end
   end
   for colIndex=1,t.columns do
    local cell=r[colIndex]
    if cell.kind=='button' and cell.properties.active~=false then
     assert(r.rowdata, 'Button defined in an unselectable row: '..rowIndex..':'..colIndex)
    end
    -- Native helper.lua: without reserveScrollBar a scrolling table narrows its last
    -- column after content was sized; an icon reaching it logs an error every frame.
    if cell.kind=='icon' and colIndex+(cell.span or 1)-1==t.columns then
     assert(t.properties.reserveScrollBar, 'icon spans the last column without reserveScrollBar: row '..rowIndex)
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
function color(cell) local c=cell.properties.color;return type(c)=='function' and c() or c end
-- Row index whose label column (3) shows the given text.
function rowOf(t,label) for i,r in ipairs(t.rows) do if r[3].kind=='text' and value(r[3])==label then return i end end end
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
-- Whole scrolling rows drawn under the cap, as the widget system does.
function expectedRendered(t)
 local cap,height=t.properties.maxVisibleHeight,0
 if t:getFullHeight()<=cap then return t:getFullHeight() end
 for i,r in ipairs(t.rows) do
  local h=t:getRowHeight(i)
  if not r.properties.fixed and height+h>cap then break end
  height=height+h
 end
 return height
end
'''
lua.execute(setup)
addon_files = [e.get('name') for e in E.parse(MOD / 'ui.xml').iter('file')]
assert [addon_files.index('ui/' + name) for name in UI_FILES] == sorted(addon_files.index('ui/' + name) for name in UI_FILES)
english_ids = set(lua.globals().translations.keys())
for translation in (MOD / 't').glob('*.xml'):
    assert {int(e.get('id')) for e in E.parse(translation).iter('t')} == english_ids
for name in UI_FILES:
    lua.execute((MOD / 'ui' / name).read_text(encoding='utf-8'))

# Layout: one fixed two-line hub header, then the shared titled sections.
lua.execute(r'''
local M=CEHubStatus
local s=M.get('42');assert(s and #s.wares==14 and s.population==8524100000)
assert(not M.get(77) and not M.get('invalid') and not M.get(0))
local before=reads;M.get(42);assert(reads==before)
now=1;M.get(42);assert(reads==before+2)
known=false;assert(not M.get(42));known=true
valid=false;assert(not M.get(42));valid=true
now=3
local t=draw()
-- Vanilla title, growth row, gap, Overview (title, population, next level), gap,
-- Supplies (title, 14 wares), gap, Bonuses (title, 5 rows).
assert(t.columns==7 and t.properties.tabOrder==21 and #t.rows==29, #t.rows)
assert(t.properties.maxVisibleHeight==432 and t.properties.reserveScrollBar==false)
for i,r in ipairs(t.rows) do assert(r.properties.fixed==(i<=2 or nil), 'title and growth row are fixed') end
-- Bottom anchoring: whole rows under the 432 cap (30+20+6+60+6+300+6 = 428).
assert(t.ceRenderedHeight==428 and t.ceRenderedHeight==expectedRendered(t))
assert(t.properties.y==1080-428-2-2-4-2)
assert(t.topRow==3)
-- Vanilla single-object title: icon, name and ID centred, object colour, no background.
local title=t.rows[1]
assert(title.rowdata==nil and title.properties.bgColor==nil and title[1].span==7)
assert(value(title[1])=='\27[mapob_station] Hub 42 (ABC-42)' and title[1].properties.halign=='center')
assert(title[1].properties.font=='header' and title[1].properties.fontsize==12 and title[1].properties.minRowHeight==30)
assert(title[1].properties.color.name=='objectcolor42')
-- Growth row: progress label over the bar, compact status as text in the last columns.
local growth=t.rows[2]
assert(growth.properties.bgColor==nil and growth[1].kind=='bar' and growth[1].properties.current()==50)
assert(growth[1].properties.x==growth[1]:getWidth()+growth[2]:getWidth()+4)
assert(growth[1].properties.width==growth[3]:getWidth()+growth[4]:getWidth()+growth[5]:getWidth()+4)
assert(value(growth[3])=='To level 2: 50%' and growth[3].span==3)
assert(value(growth[6])=='\27[menu_hourglass] 16m' and color(growth[6])==Color.text_normal)
assert(growth[3].properties.mouseOverText():find('^Supplied, 16m left\n\nProgress toward level 2'))
-- Overview.
assert(t.rows[3][1].properties.minRowHeight==6 and t.rows[4].properties.bgColor==Color.row_title_background)
assert(value(t.rows[4][3])=='Overview')
assert(value(t.rows[5][3])=='Population' and value(t.rows[5][4])=='8.52 billion')
assert(t.rows[5].properties.bgColor==Color.rowgroup_background_default)
assert(t.rows[5][1].properties.cellBGColor==Color.row_background and t.rows[5][4].properties.cellBGColor==Color.rowgroup_background_default)
assert(value(t.rows[6][3])=='Next level' and value(t.rows[6][4])=='+25% demand, unlocks Energy Cells')
-- Supplies, with an Incoming column in the wide panel.
assert(value(t.rows[8][3])=='Supplies' and value(t.rows[8][6])=='Buying' and value(t.rows[8][7])=='Incoming')
local ware=t.rows[9]
assert(value(ware[3])=='Ware 1' and value(ware[5])=='16m' and value(ware[6])=='300' and value(ware[7])=='200')
assert(color(ware[5])==Color.text_normal and ware[7].properties.color==Color.text_lowlight)
assert(ware[1].kind=='bar' and ware[1].properties.width==ware[3]:getWidth()+ware[4]:getWidth()+ware[5]:getWidth()+4)
assert(ware[1].properties.start()==500.5/4000*100 and ware[1].properties.current()==700.5/4000*100)
assert(ware[1].properties.valueColor.b==140 and ware[1].properties.posChangeColor.g==85)
assert(ware[5].properties.mouseOverText():find('^Supplied\nWare 1') and ware[5].properties.mouseOverText():find('Incoming: 200',1,true))
assert(value(t.rows[13][3])=='Ware 5' and value(t.rows[22][3])=='Ware 14')
-- Bonuses: no payload, so the title says unavailable and every row is grey.
assert(value(t.rows[24][3])=='Bonuses' and value(t.rows[24][6])==translations[68] and color(t.rows[24][6])==Color.text_inactive)
for i=25,29 do assert(t.rows[i][3].properties.color==Color.text_inactive and t.rows[i][3].span==5) end
-- A new shortage rebuilds; the frozen order keeps Ware 5 in place with its icon.
status[9][5][2]=0;status[9][5][8]=0;now=4
menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame)
t=draw();assert(value(t.rows[9][3])=='Ware 1' and value(t.rows[13][3])=='Ware 5')
assert(value(t.rows[13][5])=='\27[lso_error] '..translations[98] and color(t.rows[13][5])==Color.text_negative)
assert(value(t.rows[2][6])=='\27[lso_error] 1' and color(t.rows[2][6])==Color.text_negative)
assert(t.rows[2][3].properties.mouseOverText():find('Paused: missing supplies\n- Ware 5',1,true))
status[9][1][8]=899;now=5;t=draw()
assert(value(t.rows[9][5])=='\27[lso_warning] 15m' and color(t.rows[9][5])==Color.text_warning)
status[9][1][8]=900;now=6;t=draw();assert(value(t.rows[9][5])=='15m')
status[9][1][2]=9000;status[9][1][8]=16200;now=7
assert(value(t.rows[9][5])=='4h 30m' and t.rows[9][1].properties.current()==100)
-- Map hover keeps its compact tooltip.
assert(menu.onUpdate()==73 and override=='Level: 1\nPopulation served: 8.52 billion')
picked=77;menu.onUpdate();assert(override==nil)
override='native hover';menu.onUpdate();assert(override=='native hover')
picked=42;menu.onUpdate();mouse=false;menu.onUpdate();assert(override==nil);mouse=true
picked=43;menu.onUpdate();assert(override=='Level: 1\nPopulation served: 8.52 billion');picked=42
-- Scroll position survives updates for the same hub; another hub starts at the top.
menu.selectedShipsTable=21;liveTopRow=10;menu.onUpdate();t=draw();assert(t.topRow==10)
menu.selectedcomponents={['43']=true};t=draw();assert(value(t.rows[9][3])=='Ware 1' and t.topRow==3)
menu.selectedcomponents={['42']=true};t=draw();assert(value(t.rows[9][3])=='Ware 5')
status[9][15]={'New ware',0,1,1,0,0,0,0,1,'newware'};now=8
menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame)
-- New wares append after the frozen order (Ware 1 has the most time left and sorts last).
t=draw();assert(value(t.rows[23][3])=='New ware' and value(t.rows[22][3])=='Ware 1')
menu.selectedcomponents={['42']=true,['43']=true};assert(draw().columns==1)
menu.selectedcomponents={['77']=true};assert(draw().columns==1)
menu.selectedcomponents={};assert(draw().columns==1)
menu.selectedcomponents={['42']=true}
-- Unavailable and stale snapshots show the state as an Overview warning.
statuses={second};now=10;menu.onUpdate();t=draw()
assert(value(t.rows[2][3])==translations[68])
local warning=rowOf(t,translations[78]);assert(warning and value(t.rows[warning][4])==translations[68])
assert(color(t.rows[warning][4])==Color.text_warning)
statuses={status,second};now=11;menu.onUpdate();t=draw()
status[9][1][8]=nil;now=12;assert(M.get(42).stale and #M.get(42).wares==15)
assert(M.state(M.get(42))==M.text(88))
t=draw();assert(value(t.rows[rowOf(t,translations[78])][4])==M.text(88))
status[9][1][8]=900;now=13
-- Special map modes keep the native table and tooltip.
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
Helper.viewWidth=1920
print('Map status layout: vanilla title, growth row, shared sections, incoming column, frozen order, hover, modes and anchoring passed')
''')

# Formatters shared by both panels: states, codes, signatures and progress hints.
lua.execute(r'''
local M=CEHubStatus
status[4]=0;status[7]=1;now=14
assert(M.levelLabel(M.get(42))=='Level 1 (stagnating)' and M.get(42).pausedOffers)
for reason,label in pairs({constructing='constructing',damaged_modules='damaged modules',
 no_population='no population',owner_changed='ownership changed',hub_unavailable='hub unavailable',
 modules_unavailable='modules unavailable'}) do
 status[12]=reason;now=now+1
 local expected=reason=='constructing' and M.text(372) or 'Paused: '..label
 assert(M.progressHint(M.get(42)):find(expected,1,true))
end
status[4]=true;status[14]=true;now=now+1;assert(M.state(M.get(42))==M.text(89))
status[14]=false;status[15]=true;now=now+1;assert(M.state(M.get(42))==M.text(88))
status[15]=false;status[13]=2;now=now+1;assert(not M.get(42).available)
status[13]=3;status[3]=2;now=now+1
assert(M.levelLabel(M.get(42))=='Level 1 (expanding)')
assert(M.progressHint(M.get(42))==M.text(99,2)..'\n\n'..M.text(372))
assert(M.progressShort(M.get(42))==M.text(99,2))
status[3]=0;status[2]=10;now=now+1;assert(M.levelLabel(M.get(42))=='Level 10 (maximum)')
assert(M.progressShort(M.get(42))==M.text(100))
status[9][1][4]=1485;now=now+1;assert(M.columns(M.get(42),M.get(42).wares[1])[4]=='1,485')
status[9][1][4]=57000;now=now+1;assert(M.columns(M.get(42),M.get(42).wares[1])[4]=='57.00 k')
status[9][1][4]=1500000;now=now+1;assert(M.columns(M.get(42),M.get(42).wares[1])[4]=='1.50 M')
status[9]={};now=now+1;local t=draw()
assert(value(t.rows[rowOf(t,'Supplies')+1][3])==M.text(71))
-- State codes drive labels, sort groups, colors and rebuilds independently of text.
local wareCases = {
 {0,0,0,'paused',57,'text_normal','\27[lso_pause] '..translations[69]},
 {1,0,0,'needed',94,'text_negative','\27[lso_error] '..translations[98]},
 {1,1,899,'low',95,'text_warning','\27[lso_warning] 15m'},
 {1,1,900,'supplied',96,'text_normal','15m'},
 {1,10,36000,'full',97,'text_normal','10h 0m'},
}
for _,case in ipairs(wareCases) do
 local w={rate=case[1],reserve=case[2],remaining=case[3],capacity=10,key='test',name='Test'}
 assert(M.wareCode(w)==case[4] and M.wareState(w)==M.text(case[5]))
 assert(M.wareColor(w)==case[6] and M.wareTime(w)==case[7], M.wareTime(w))
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
print('Hub formatters: states, ware codes and icons, signatures and progress hints passed')
''')

# Verify the deferred-load path independently of the already-registered menu.
deferred = LuaRuntime()
deferred.globals().translations = deferred.table_from({
    int(e.get('id')): ''.join(e.itertext()).replace(r'\n', '\n').replace(r'\(', '(').replace(r'\)', ')')
    for e in E.parse(MOD / 't/0001.xml').iter('t')
})
deferred.execute(setup)
deferred.execute("savedMenu=menu;menu=nil")
for name in UI_FILES:
    deferred.execute((MOD / 'ui' / name).read_text(encoding='utf-8'))
deferred.execute('''
assert(loadCallback);loadCallback();menu=savedMenu
callbacks.CEPopulationRequest();local wrapper=menu.onUpdate
loadCallback();callbacks.CEPopulationRequest();assert(menu.onUpdate==wrapper)
assert(draw().columns==7)
''')

# Native scrolling constraints: one fixed header, every row present, bounded geometry.
deferred.execute('''
status[2]=3;status[9]=snapshot(42,40)[9];now=now+1
-- Wrapped next-level text (row 5) and a wrapped ware name (row 8).
wrappedRowHeights={[6]=41.25,[9]=60.5}
for _,height in ipairs({720,1080,1081,1432,1440,1513,1513.5}) do
 Helper.viewHeight=height
 local t=draw()
 assert(#t.rows==55 and t.properties.maxVisibleHeight==math.floor(height*0.4))
 assert(t.properties.y%1==0)
 for i,r in ipairs(t.rows) do assert(r.properties.fixed==(i<=2 or nil)) end
 -- The widget system draws whole scrolling rows only and keeps that height.
 assert(t.ceRenderedHeight==expectedRendered(t) and t.ceRenderedHeight<=t:getVisibleHeight())
 assert(t:getVisibleHeight()-t.ceRenderedHeight<61, 'at most one row short of the cap')
 local available=math.floor(height-8-t.properties.y)
 assert(available>=math.ceil(t.ceRenderedHeight)+2 and available<=math.ceil(t.ceRenderedHeight)+3)
end
menu.selectedShipsTable=21;liveTopRow=35;menu.onUpdate()
local t=draw();assert(t.topRow==35)
missingTable=true;menu.onUpdate();t=draw();assert(t.topRow==35)
missingTable=false;liveTopRow=20;menu.onUpdate();t=draw();assert(t.topRow==20)
missingTable=true
menu.selectedcomponents={['43']=true};t=draw();menu.onUpdate();assert(draw().topRow==3)
menu.selectedcomponents={['42']=true};t=draw();menu.onUpdate();assert(draw().topRow==3)
missingTable=false;liveTopRow=50;menu.onUpdate()
-- A shrinking basket clamps the restored position to the last row.
status[9]=snapshot(42,6)[9];now=now+1;t=draw()
assert(#t.rows==21 and t.topRow==21)
wrappedRowHeights=nil
Helper.viewHeight=1080;t=draw()
-- Content that fits is drawn in full and anchored to its full height.
assert(t:getFullHeight()<=432 and t.ceRenderedHeight==t:getFullHeight())
assert(math.floor(1080-8-t.properties.y)>=math.ceil(t.ceRenderedHeight)+2)
status[9]={};now=now+1;t=draw();assert(#t.rows==16 and t.topRow==16)
menu.cleanup();t=draw();assert(t.topRow==3)
''')
print('Map status geometry: fixed header, whole-row anchoring, scroll retention and clamping passed')

# Sector bonuses: state in the Bonuses title, unlocked benefits, locked levels, fallbacks.
deferred.execute('''
Helper.viewHeight=1080;wrappedRowHeights=nil;status[9]=snapshot(42,6)[9]
status[2]=10;status[23]={1,true,'active',{},90,16,12,true,true,2,3,3,300,600,4,360,{2,3,5,7,9}}
now=now+1
local t=draw()
local b=rowOf(t,'Bonuses')
assert(value(t.rows[b][6])=='Active' and color(t.rows[b][6])==Color.text_positive)
assert(t.rows[b][6].properties.mouseOverText()==translations[420])
local lowlight='\\n<text_lowlight>   '
assert(value(t.rows[b+1][3])=='Workforce immigration'..lowlight..'90 / hour per 1,000 capacity\\27X')
assert(t.rows[b+1][3].properties.mouseOverText():find('Registered stations: 2',1,true))
assert(value(t.rows[b+2][3])=='Trade prices'..lowlight..'16% of price range\\27X')
assert(t.rows[b+2][3].properties.mouseOverText():find('3 participating stations',1,true))
assert(value(t.rows[b+3][3]):find('+12% success chance',1,true))
assert(value(t.rows[b+4][3])=='Civilian sensor network'..lowlight..'3 station radars\\27X')
assert(value(t.rows[b+5][3])=='Discover lockboxes'..lowlight..'Enabled\\27X')
assert(t.rows[b+5][3].properties.mouseOverText():find('Discover lockbox locations',1,true))
status[23][2]=false;status[23][3]='shortage';status[23][4]={'Water'};now=now+1
assert(value(t.rows[b][6])=='Suspended' and color(t.rows[b][6])==Color.text_negative)
assert(value(t.rows[b+5][3]):find('Disabled',1,true))
assert(CERewardStatus.reason(CEHubStatus.get(42))==translations[411])
-- Locked bonuses are one grey line with the unlock level; a level change rebuilds.
status[2]=3;now=now+1;menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame);t=draw()
-- Below the maximum level the Overview gains a next-level row.
assert(rowOf(t,'Bonuses')==b+1);b=b+1
for i,level in ipairs({5,7,9}) do
 local r=t.rows[b+2+i]
 assert(r[3].properties.color==Color.text_inactive and value(r[6])=='\\27[menu_locked] Level '..level)
 assert(r[6].properties.mouseOverText():find('\\n',1,true))
end
status[15]=true;now=now+1
assert(value(t.rows[b][6])==translations[68] and color(t.rows[b][6])==Color.text_inactive)
status[15]=false
status[23][5]=0/0;now=now+1;assert(value(t.rows[b][6])==translations[68])
status[23][5]=20;now=now+1
-- A missing payload keeps the panel usable and rebuilds into grey rows.
status[23]=nil;now=now+1;menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame);t=draw()
assert(value(t.rows[b][6])==translations[68] and t.rows[b+1][3].properties.color==Color.text_inactive)
''')
print('Sector bonuses: title state, unlocked benefits, locked levels, suspension and fallbacks passed')

# Civil unrest in the Overview section.
deferred.execute('''
status[20]={96,4,1,900,{'Food','Water'},3};now=now+1
local u=CEHubStatus.getFresh(42)
local text=CEHubStatus.unrest(u)
assert(text:find('Critical',1,true) and text:find('Food, Water',1,true) and text:find('15 min',1,true))
menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame)
local t=draw();local i=rowOf(t,translations[453])
assert(value(t.rows[i][4]):find('Critical',1,true) and value(t.rows[i+1][4])=='Shortages: Food, Water')
assert(value(t.rows[i+2][4])==string.format(translations[253],15))
status[20][3]=-1;now=now+1
assert(CEHubStatus.unrest(CEHubStatus.getFresh(42)):find('recovering',1,true))
-- Unrest switched off in the settings: an empty payload hides every unrest surface.
local unrestPayload=status[20];status[20]={};now=now+1
local off=CEHubStatus.getFresh(42)
assert(off.unrest==nil and CEHubStatus.unrest(off)=='' and not CEHubStatus.tooltip(off):find('Critical',1,true))
t=draw();assert(not rowOf(t,translations[453]))
status[20]=unrestPayload;now=now+1
''')
print('Civil unrest: overview value, detail lines and switched-off payload passed')

# Demand events: their own scrolling section, one line per event.
deferred.execute('''
status[9]=snapshot(42,40)[9]
status[21]={2,{{8,75,7200,string.rep('Long material name, ',12)}},{1,2,8,9},7};now=now+1
for _,height in ipairs({720,1080,1440}) do
 Helper.viewHeight=height
 local t=draw()
 local e=rowOf(t,'Demand events')
 assert(e and t.rows[e].properties.bgColor==Color.row_title_background and t.rows[e-1][1].properties.minRowHeight==6)
 assert(value(t.rows[e+1][3])=='Industrial Boom' and value(t.rows[e+1][5])=='+75%' and value(t.rows[e+1][6])=='2h 0m')
 assert(color(t.rows[e+1][5])==Color.text_warning and t.rows[e+1][6].properties.color==Color.text_lowlight)
 assert(t.rows[e+1][3].properties.mouseOverText():find('Long material name',1,true))
 assert(rowOf(t,'Supplies')==e+3)
 for i,r in ipairs(t.rows) do assert(r.properties.fixed==(i<=2 or nil)) end
 assert(t:getVisibleHeight()==math.floor(height*0.4))
end
status[21][2][1][2]=-50;status[21][2][1][1]=9;now=now+1
assert(CEHubStatus.eventText(CEHubStatus.getFresh(42)):find('-50%',1,true))
menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame)
local t=draw();local e=rowOf(t,'Demand events')
assert(value(t.rows[e+1][3])=='Industrial Slowdown' and value(t.rows[e+1][5])=='-50%' and color(t.rows[e+1][5])==Color.text_normal)
-- Events changing resets the scroll position; removing them rebuilds.
menu.selectedShipsTable=21;liveTopRow=35;menu.onUpdate();t=draw();assert(t.topRow==35)
status[21]={2,{},{},8};now=now+1
menu.refreshMainFrame=nil;menu.onUpdate();assert(menu.refreshMainFrame)
t=draw();assert(not rowOf(t,'Demand events') and t.topRow==3)
status[21]={99,50,100,'bad',{},9};now=now+1
assert(not CEHubStatus.getFresh(42).demandEvents)
status[21]=nil;now=now+1;assert(draw().columns==7)
''')
print('Demand events: own section, one-line rows, live values, rebuilds and invalid payloads passed')

# Versioned multi-event payloads: stable ID order and independently live cells.
deferred.execute('''
Helper.viewHeight=1080
status[21]={2,{{8,75,7200,'Metals'},{3,50,5400,'Water'},{1,-25,3600,'Food'}},{5},10}
now=now+1
local t=draw();local e=rowOf(t,'Demand events')
assert(value(t.rows[e+1][3])=='Lost Harvest' and value(t.rows[e+2][3])=='Drought' and value(t.rows[e+3][3])=='Industrial Boom')
assert(rowOf(t,'Supplies')==e+5)
status[21][2][2][3]=4800;now=now+1
assert(value(t.rows[e+2][6])=='1h 20m')
status[21][2]={};for _,id in ipairs({1,3,4,5,6,7,8}) do
 status[21][2][#status[21][2]+1]={id,50,3600,string.rep('Long affected goods ',20)}
end
for _,height in ipairs({720,1080,1440}) do
 Helper.viewHeight=height;now=now+1;t=draw()
 e=rowOf(t,'Demand events')
 -- Seven events scroll with the rest; only the header is fixed.
 assert(value(t.rows[e+7][3])=='Industrial Boom' and rowOf(t,'Supplies')==e+9)
 for i,r in ipairs(t.rows) do assert(r.properties.fixed==(i<=2 or nil)) end
 assert(t:getVisibleHeight()==math.floor(height*0.4))
end
status[21][2]={{3,50,600,'Water'},{3,50,600,'Water'}};now=now+1
assert(not CEHubStatus.getFresh(42).demandEvents)
status[21]={2,{},{},12};now=now+1;t=draw();assert(not rowOf(t,'Demand events'))
''')
print('Concurrent events: ID ordering, individual timers and seven scrollable events passed')

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
now=1001.5
assert(t.rows[9][1].properties.start()==0 and t.rows[9][1].properties.current()==25)
replacement=snapshot(42,14);replacement[9][1][2]=0;replacement[9][1][5]=0
statuses={replacement,second};callbacks.CEHubStatusUpdated('CEHubStatusUpdated',42);now=1001.6
assert(t.rows[9][1].properties.current()==0)
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
