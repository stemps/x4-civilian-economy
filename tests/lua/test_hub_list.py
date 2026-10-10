"""Execute the map sidebar hub list with LuaJIT and UI Extensions stand-ins."""
from pathlib import Path
from xml.etree import ElementTree as E
from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / 'src'
lua = LuaRuntime()
lua.globals().translations = lua.table_from({
    int(e.get('id')): ''.join(e.itertext()).replace(r'\n', '\n').replace(r'\(', '(').replace(r'\)', ')')
    for e in E.parse(MOD / 't/0001.xml').iter('t')
})
setup = r'''
now, known = 0, true
function snapshot(id, count, active)
    local s = {id, 1, 0, active ~= false, 3600, 7200, false, true, {}, false, 8524100000, nil, 3, false, false, {'Energy Cells'}}
    for i=1,count do s[9][i] = {'Ware '..i, 500.5, 4000, 300, 200, 1000, 13000, 900.9+i, 2000, 'ware'..i} end
    return s
end
supplied, shortage, paused = snapshot(42, 2), snapshot(43, 2), snapshot(44, 1, false)
shortage[9][2][2], shortage[9][2][8] = 0, 0
hubs = {42, 43, 44}
statuses = {supplied, shortage, paused}
local C = {
 GetPlayerID=function() return 1 end,
 IsValidComponent=function(id) return id ~= 99 end,
 IsObjectKnown=function() return known end,
 GetTextHeight=function(text,font,size,width) assert(text==' \n ' and width==0);return 34 end,
 SetFocusMapComponent=function(map,id,reset) assert(map==9 and reset==true);focused[#focused+1]=id end,
}
package.loaded.ffi={C=C,cdef=function() end}
ConvertIntegerString=function(n) return tostring(math.floor(n)) end
ConvertStringTo64Bit=tonumber
ConvertStringToLuaID=tonumber
GetNPCBlackboard=function(id,key)
 if key=='$ce_hubs' then return hubs end
 if key=='$ce_hub_statuses' then return statuses end
 error(key)
end
ReadText=function(page,id) assert(page==974201 and translations[id], tostring(id));return translations[id] end
getElapsedTime=function() return now end
longNames={}
hubIcons={}
GetComponentData=function(id,key)
 assert(type(id)=='number')
 if key=='icon' then return hubIcons[id]==nil and 'mapob_station' or hubIcons[id] end
 assert(key=='name');return longNames[id] or 'Hub '..id
end
-- Character budget stand-in for native text measurement.
TruncateText=function(text,font,size,width)
 local budget=math.floor(width/7)
 if #text<=budget then return text end
 return text:sub(1,budget-3)..'...'
end
DebugError=function() end
events={}
RegisterEvent=function(event,fn) events[event]=fn end
refreshRequests={}
AddUITriggeredEvent=function(screen,control,id)
 assert(screen=='CEHubStatus' and control=='refresh')
 refreshRequests[#refreshRequests+1]=id
end
Color=setmetatable({}, {__index=function(t,key)
 for _,known in ipairs({'container_subsection_background','container_panel_header','row_title_background',
  'statusbar_marker_hidden','icon_transparent','rowgroup_background_default','text_normal','text_negative',
  'text_warning','text_inactive','text_positive','frame_background_semitransparent','text_lowlight',
  'row_background_container2','row_separator','container_subsection_header','row_background',
  'row_background_blue'}) do
  if key==known then rawset(t,key,{name=key});return rawget(t,key) end
 end
 error('unknown color '..tostring(key))
end})
callbacks, nativeUpdates, nativeCleanups, refreshes = {}, 0, 0, 0
focused, nativeSelects, selectionSyncs, currentRowData = {}, 0, 0, nil
menu={infoTableMode=nil, sideBarWidth=40, panelState={leftmenu=true}, panelPins={},
 infoTable=21, holomap=9, selectedcomponents={},
 onSelectElement=function(uitable,modified,row,isdblclick,input) nativeSelects=nativeSelects+1;return 75 end,
 addSelectedComponent=function(id,clear) assert(clear==nil);menu.selectedcomponents={[tostring(id)]={}} end,
 setSelectedMapComponents=function() selectionSyncs=selectionSyncs+1 end,
 registerCallback=function(name,fn,id) assert(id=='civilian_economy_hubs');callbacks[name]=fn end,
 refreshInfoFrame=function() refreshes=refreshes+1 end,
 onUpdate=function() nativeUpdates=nativeUpdates+1;return 73 end,
 cleanup=function() nativeCleanups=nativeCleanups+1;return 74 end}
Helper={viewWidth=1920,viewHeight=1080,borderSize=2,standardContainerOffset=4,frameBorder=6,
 standardFont='std',standardFontBold='bold',standardFontSize=9,standardTextHeight=16,standardTextOffsetx=5,
 titleFont='title',titleFontSize=12,largeRowHeight=30,
 scaleFont=function(font,size) return size end,scaleY=function(y) return y end,scaleX=function(x) return x end,
 getFrameBorderColor=function() return {} end,getFrameBorderLineWidth=function() return 1 end,
 setFrameBorderIcon=function(m,border,side) assert(m==menu and side=='left') end,
 convertColorToText=function(c) return '<'..c.name..'>' end,
 getCurrentRowData=function(m,uitable) assert(m==menu and uitable==21);return currentRowData end,
 getMenu=function(name) assert(name=='MapMenu');return menu end}
function newFrame()
 local f={tables={},properties={width=500,y=100}}
 function f:addFrameBorder(name) assert(name=='ce_hubs');return {id=1} end
 function f:addTable(cols,p)
  local t={properties=p,rows={},columns=cols,widths={}}
  self.tables[#self.tables+1]=t
  function t:setColWidth(col,w) assert(col<=cols and w>0);self.widths[col]=w end
  function t:setDefaultCellProperties() end
  function t:setDefaultComplexCellProperties() end
  function t:setTopRow(row) self.topRow=row end
  function t:setSelectedRow(row) self.selectedRow=row end
  function t:addRow(data,props)
   assert(data==nil or data==true or type(data)=='string')
   local r={rowdata=data,properties=props,index=#self.rows+1}
   for i=1,cols do
    local cell={handlers={},properties={cellBGColor=props and props.bgColor}}
    local function apply(self,p) for k,v in pairs(p or {}) do self.properties[k]=v end end
    function cell:setColSpan(n) assert(i+n-1<=cols);self.span=n;return self end
    function cell:setBackgroundColSpan(n) assert(i+n-1<=cols);self.bgSpan=n;return self end
    function cell:createText(text,p)
     -- Native text cells subtract their x offset on both sides; a narrower cell
     -- makes an invalid fontstring and the engine aborts the whole frame.
     local width=-2*(1-(self.span or 1))
     for c=i,i+(self.span or 1)-1 do width=width+r[c]:getWidth() end
     assert(width>2*Helper.standardTextOffsetx, 'text cell too narrow at column '..i..': '..width)
     self.text=text;apply(self,p);self.kind='text';return self
    end
    function cell:createButton(p) apply(self,p);self.kind='button';return self end
    function cell:createIcon(icon,p)
     assert(icon=='solid' and p.height>0 and (p.width==nil or p.width<=self:getWidth()+(self.span and 1e9 or 0)))
     apply(self,p);self.kind='icon';return self
    end
    function cell:createStatusBar(p) assert(type(p.valueColor)=='table');apply(self,p);self.kind='bar';return self end
    function cell:getWidth()
     if t.widths[i] then return t.widths[i] end
     local used=2*(cols-1);for _,w in pairs(t.widths) do used=used+w end
     return t.properties.width-used
    end
    function cell:setText(text,p) self.text=text;self.textProps=p or {};return self end
    function cell:setText2(text,p) assert(self.kind=='icon');self.text2=text;self.text2Props=p or {};return self end
    function cell:getColSpanWidth()
     local width=2*((self.span or 1)-1)
     for c=i,i+(self.span or 1)-1 do width=width+r[c]:getWidth() end
     return width
    end
    r[i]=cell
   end
   self.rows[#self.rows+1]=r;return r
  end
  return t
 end
 return f
end
function draw()
 local f=newFrame();callbacks.createInfoFrame_on_menu_infoTableMode(f)
 assert(#f.tables<=1, 'MapMenu.viewCreated binds the first info table as menu.infoTable')
 for _,t in ipairs(f.tables) do
  for rowIndex,r in ipairs(t.rows) do
   -- Scrolling needs every non-fixed row selectable, as in the bottom panel.
   assert(r.properties.fixed or r.rowdata, 'Unselectable scrolling row '..rowIndex)
   for colIndex=1,t.columns do
    local cell=r[colIndex]
    if cell.kind=='button' then assert(r.rowdata and r.properties.interactive~=false, 'Button in inert row') end
    -- Native helper.lua: without reserveScrollBar, a scrolling table narrows its last
    -- column after content was sized, so an icon reaching it overflows its parent and
    -- the engine logs an error every frame (measured: 8,159 lines in one session).
    if cell.kind=='icon' and colIndex+(cell.span or 1)-1==t.columns then
     assert(t.properties.reserveScrollBar, 'icon spans the last column of a table without reserveScrollBar')
    end
   end
  end
 end
 return f.tables[1], f
end
function value(cell) return type(cell.text)=='function' and cell.text() or cell.text end
function color(cell) local c=cell.properties.color;return type(c)=='function' and c() or c end
function find(t,key)
 for i,r in ipairs(t.rows) do if r.rowdata==key then return i end end
end
function names(t)
 local result={}
 for _,r in ipairs(t.rows) do if type(r.rowdata)=='string' then result[#result+1]=value(r[3]):match('^[^\n]*'):gsub('^\27%[[^%]]*%] ','') end end
 return table.concat(result,',')
end
'''
lua.execute(setup)
addon_files = [e.get('name') for e in E.parse(MOD / 'ui.xml').iter('file')]
assert addon_files.index('ui/ce_reward_status.lua') < addon_files.index('ui/ce_hub_list.lua')
assert addon_files.index('ui/ce_hub_status.lua') < addon_files.index('ui/ce_hub_list.lua')
for name in ('ce_hub_status.lua', 'ce_reward_status.lua', 'ce_hub_list.lua'):
    lua.execute((MOD / 'ui' / name).read_text(encoding='utf-8'))

lua.execute(r'''
local M=CEHubStatus
assert(callbacks.createSideBar_on_start and callbacks.createInfoFrame_on_menu_infoTableMode)
-- The sidebar entry follows Info once, however often the native sidebar is rebuilt.
local config={leftBar={{mode='propertyowned'},{mode='info'},{spacing=true},{mode='plots'}}}
callbacks.createSideBar_on_start(config);callbacks.createSideBar_on_start(config)
assert(#config.leftBar==6 and config.leftBar[3].spacing and config.leftBar[4].mode=='ce_hubs')
assert(config.leftBar[4].icon=='stationbuildst_habitation' and config.leftBar[4].name=='Civilian Economy')
assert(config.leftBar[4].helpOverlayText==translations[461] and config.leftBar[5].spacing)
local noInfo={leftBar={{mode='objectlist'}}};callbacks.createSideBar_on_start(noInfo)
assert(#noInfo.leftBar==3 and noInfo.leftBar[3].mode=='ce_hubs')
callbacks.createSideBar_on_start(nil);callbacks.createSideBar_on_start({})
print('Hub list sidebar: entry placement and idempotence passed')
''')

lua.execute(r'''
local M=CEHubStatus
assert(M.supply(M.get(42)).code=='supplied' and M.supply(M.get(42)).seconds==901.9)
assert(M.supply(M.get(43)).code=='shortage' and M.supply(M.get(43)).missing==1)
assert(M.supply(M.get(44)).code=='inactive' and M.supplyText(M.get(44))==translations[57])
assert(M.supplyText(M.get(42))=='Supplied, 16m left' and M.supplyColor(M.get(42))=='text_normal')
assert(M.supplyText(M.get(43))=='Shortage: 1 goods' and M.supplyColor(M.get(43))=='text_negative')
supplied[9][1][8]=899;now=1
assert(M.supply(M.get(42)).code=='low' and M.supplyText(M.get(42))=='Low, 15m left')
supplied[9][1][8]=901.9;now=2
assert(M.progressShort(M.get(42))=='To level 2: 50%' and M.progressPercent(M.get(42))==50)
supplied[3]=2;now=3;assert(M.progressShort(M.get(42))=='Expanding to level 2');supplied[3]=0
supplied[2]=10;now=4;assert(M.progressShort(M.get(42))==translations[100] and M.progressPercent(M.get(42))==0);supplied[2]=1
now=5;assert(#M.hubs()==3);known=false;assert(#M.hubs()==0);known=true
print('Hub list facts: supply classification, earliest exhaustion and short progress passed')
''')

lua.execute(r'''
local M=CEHubStatus
-- Compact status icons for the narrow layout.
now=12
assert(M.supplyCompact(M.get(42))=='\27[menu_hourglass] 16m')
assert(M.supplyCompact(M.get(43))=='\27[lso_error] 1' and M.supplyCompact(M.get(44))=='\27[lso_pause]')
supplied[9][1][8]=899;now=13;assert(M.supplyCompact(M.get(42))=='\27[lso_warning] 15m')
supplied[9][1][8]=901.9;now=14
local s=M.get(43)
assert(M.wareTime(M.find(s,'ware1'))=='16m' and M.wareIcon(M.find(s,'ware1'))=='')
assert(M.wareTime(M.find(s,'ware2'))=='\27[lso_error] '..translations[98])
local w=M.find(s,'ware1');w.remaining=100;assert(M.wareTime(w)=='\27[lso_warning] 2m')
w.rate=0;assert(M.wareTime(w)=='\27[lso_pause] '..translations[69])
print('Hub list compact status: hub and ware icons passed')
''')

lua.execute(r'''
local M=CEHubStatus
now=10
menu.infoTableMode='objectlist';local t,f=draw();assert(t==nil and #f.tables==0)
menu.infoTableMode='ce_hubs';menu.showMultiverse=true;t=draw();assert(t==nil);menu.showMultiverse=false
t,f=draw()
-- Two header rows and one two-line item per hub; vanilla row borders, no separator rows.
assert(t.columns==7 and t.properties.tabOrder==1 and #t.rows==2+3, #t.rows)
assert(t.widths[1]==1, '1px bar anchor column')
assert(f.properties.autoFrameHeightPadding==4 and t.properties.maxVisibleHeight==1080-100-6)
assert(value(t.rows[1][1])=='Civilian Economy' and t.rows[1].properties.fixed and t.rows[2].properties.fixed)
assert(value(t.rows[2][1])=='Hubs: 3 | Supplied: 1 | Shortage: 1')
-- Shortage first, then supplied, then inactive.
assert(names(t)=='Hub 43,Hub 42,Hub 44', names(t))
assert(find(t,'43')==3 and find(t,'42')==4 and find(t,'44')==5)
for i=3,5 do assert(t.rows[i].properties.borderBelow==nil, 'vanilla default border below items') end
local item=t.rows[4]
-- Vanilla property-row look: station background blue, station icon, grey second line.
assert(item.rowdata=='42' and item.properties.bgColor==Color.row_background_blue)
-- One selectable row: button, bar and both text lines share the two-line height.
assert(item[2].kind=='button' and value(item[2])=='+' and item[2].properties.height==34)
local bar, icon=item[1], item[3]
assert(bar.kind=='bar' and bar.properties.current()==50 and bar.properties.y==34-16 and bar.properties.height==16)
-- The bar starts past the button and covers the label, flex and time columns.
assert(bar.properties.x==item[1]:getWidth()+item[2]:getWidth()+4)
assert(bar.properties.width==item[3]:getWidth()+item[4]:getWidth()+item[5]:getWidth()+4)
-- The text starts right after the button: no column in between.
assert(icon.kind=='icon' and icon.span==5 and icon.properties.height==34 and icon.properties.cellBGColor==Color.row_background_blue)
assert(value(icon)=='\27[mapob_station] Hub 42\n<text_lowlight>To level 2: 50%\27X' and icon.textProps.halign=='left')
hubIcons[42]='';t=draw();assert(value(t.rows[4][3]):find('^Hub 42\n'), 'no icon without one');hubIcons[42]=nil
t=draw();item=t.rows[4];icon=item[3]
assert(icon.text2()=='\n<text_normal>\27[menu_hourglass] 16m\27X' and icon.text2Props.halign=='right')
assert(icon.properties.mouseOverText():find('^Supplied, 16m left\n\nProgress toward level 2'))
for col=4,7 do assert(item[col].kind==nil, 'no population or second row') end
assert(t.rows[3][3].text2()=='\n<text_negative>\27[lso_error] 1\27X')
assert(t.rows[5][3].text2()=='\n<text_inactive>\27[lso_pause]\27X')
-- Long names are truncated to the span; the tooltip keeps the full name.
longNames[42]=string.rep('Very long hub name ',10);t=draw();icon=t.rows[4][3]
local shown=value(icon):match('^[^\n]*')
assert(#shown<#longNames[42] and shown:sub(-3)=='...' and icon.properties.mouseOverText():sub(1,#longNames[42])==longNames[42])
longNames[42]=nil
-- Live cells follow the snapshot without a rebuild.
t=draw();supplied[9][1][8]=7200;supplied[9][2][8]=3600;now=11
assert(t.rows[4][3].text2()=='\n<text_normal>\27[menu_hourglass] 1h 0m\27X')
print('Hub list items: one two-line row, no stripe or separators, ordering, truncation, progress and compact supply passed')
''')

lua.execute(r'''
local M=CEHubStatus
-- Reward payload: bonus 1 unlocked and active, the rest still locked at level 1.
supplied[23]={1,true,'',{},10,5,3,0,0,1,2,3,4,5,6,7,{1,3,5,7,9}}
now=20;local t=draw();refreshes=0
t.rows[4][2].handlers.onClick();assert(refreshes==1)
t=draw()
assert(t.selectedRow==4 and value(t.rows[4][2])=='-')
-- Expanded: gap, Overview title, population, next level, gap, supplies heading,
-- 2 wares, gap, bonuses title, 5 bonuses, closing gap.
assert(#t.rows==5+16, #t.rows)
for _,i in ipairs({5,9,13}) do assert(t.rows[i][1].span==7 and t.rows[i][1].properties.minRowHeight==6, 'gap '..i) end
assert(t.rows[20][1].properties.minRowHeight==8 and t.rows[21].rowdata=='44')
-- No vertical bar anywhere.
for _,r in ipairs(t.rows) do for col=1,7 do local c=r[col].properties.cellBGColor;assert(not (c and c.b==179), 'no azure bar') end end
-- Row-level backgrounds: every heading blue, every content row the same grey,
-- gaps transparent. Cells inherit the row color; only the leading columns are clear.
local headingRows, contentRows = {6,10,14}, {7,8,11,12,15,16,17,18,19}
for _,i in ipairs(headingRows) do assert(t.rows[i].properties.bgColor==Color.row_title_background, 'heading '..i) end
for _,i in ipairs(contentRows) do assert(t.rows[i].properties.bgColor==Color.rowgroup_background_default, 'content '..i) end
for _,i in ipairs({5,9,13,20}) do assert(t.rows[i].properties.bgColor==nil, 'gap '..i) end
for i=5,20 do
 local r=t.rows[i]
 for col=1,7 do assert(r[col].bgSpan==nil, 'no background span') end
 if r.properties.bgColor then
  assert(r[1].properties.cellBGColor==Color.row_background and r[2].properties.cellBGColor==Color.row_background, 'leading columns '..i)
  for col=3,7 do assert(r[col].properties.cellBGColor==r.properties.bgColor, 'inherited background '..i..':'..col) end
 end
end
assert(value(t.rows[6][3])=='Overview' and t.rows[6][3].properties.font=='bold' and t.rows[6][3].properties.color.b==230)
assert(value(t.rows[7][3])=='Population' and t.rows[7][3].properties.color==Color.text_lowlight)
assert(value(t.rows[7][4])=='8.52 billion')
assert(value(t.rows[8][3])=='Next level' and value(t.rows[8][4])=='+25% demand, unlocks Energy Cells')
assert(value(t.rows[10][3])=='Supplies' and t.rows[10][3].properties.cellBGColor==Color.row_title_background)
assert(value(t.rows[10][6])=='Buying')
-- Ware rows: the bar in column 1 under name and icon/time, then buying; no status column.
local ware=t.rows[11]
assert(value(ware[3])=='Ware 2' and value(ware[5])=='1h 0m' and value(ware[6])=='300' and ware[7].kind==nil)
assert(ware[1].kind=='bar' and ware[1].properties.cellBGColor==Color.row_background and ware[1].properties.start()==500.5/4000*100)
assert(ware[1].properties.x==ware[1]:getWidth()+ware[2]:getWidth()+4)
assert(ware[1].properties.width==ware[3]:getWidth()+ware[4]:getWidth()+ware[5]:getWidth()+4)
assert(ware[5].properties.mouseOverText():find('^Supplied\nWare 2'))
-- Bonuses: title with state, unlocked benefit on a second line, locked on one grey line.
assert(value(t.rows[14][3])=='Bonuses' and t.rows[14][3].span==3)
assert(value(t.rows[14][6])=='Active' and color(t.rows[14][6])==Color.text_positive)
local unlocked=value(t.rows[15][3])
assert(unlocked==translations[408]..'\n<text_lowlight>   '..string.format(translations[412],10)..'\27X', unlocked)
for i,level in ipairs({3,5,7,9}) do
 local r=t.rows[15+i]
 assert(r[3].properties.color==Color.text_inactive and value(r[6])=='\27[menu_locked] Level '..level)
 assert(r[6].properties.color==Color.text_inactive and r[6].properties.mouseOverText():find('\n',1,true))
end
assert(names(t)=='Hub 43,Hub 42,Hub 44')
-- Collapse again.
t.rows[4][2].handlers.onClick();t=draw();assert(#t.rows==5 and value(t.rows[4][2])=='+')
supplied[23]=nil
print('Hub list expanded: sections, no bar or spacer, row backgrounds, wares, compact bonuses and selection passed')
''')

lua.execute(r'''
local M=CEHubStatus
-- Unrest, warnings and demand events in the overview and their own section.
shortage[20]={12.5,1,1,120,{'Ware 2'},7}
shortage[21]={2,{{3,25,600,'Ware 1'},{5,-10,1200,'Ware 2'}},{},1}
now=25;local t=draw();t.rows[3][2].handlers.onClick();t=draw()
local function at(label) for i,r in ipairs(t.rows) do if r[3].kind=='text' and value(r[3])==label then return i,r end end end
local i,r=at('Civil unrest')
assert(value(r[4])=='12.5/100 - '..translations[261]..', '..translations[254], value(r[4]))
assert(value(t.rows[i+1][3])=='' and value(t.rows[i+1][4])=='Shortages: Ware 2')
assert(value(t.rows[i+2][4])==string.format(translations[253],2))
local e=at('Demand events');assert(e and t.rows[e][3].properties.font=='bold' and t.rows[e-1][1].properties.minRowHeight==6)
local first=t.rows[e+1]
assert(value(first[3])==translations[323] and first[3].span==2 and first.properties.bgColor==Color.rowgroup_background_default)
assert(t.rows[e].properties.bgColor==Color.row_title_background)
assert(value(first[5])=='+25%' and color(first[5])==Color.text_warning and first[5].properties.halign=='right')
assert(value(first[6])=='10m' and first[6].properties.color==Color.text_lowlight)
assert(first[5].properties.mouseOverText()==string.format(translations[337],'Ware 1'))
assert(value(t.rows[e+2][5])=='-10%' and color(t.rows[e+2][5])==Color.text_normal)
-- Failures replace unrest and show as a warning.
shortage[15]=true;now=26;t=draw()
assert(not at('Civil unrest'));i,r=at(translations[78]);assert(r and color(r[4])==Color.text_warning)
shortage[15]=false;shortage[20]=nil;shortage[21]=nil;now=27
t.rows[3][2].handlers.onClick();t=draw();assert(#t.rows==5, #t.rows)
print('Hub list overview: unrest details, warnings and one-line demand events passed')
''')

lua.execute(r'''
local M=CEHubStatus
now=30;local t=draw()
t.rows[4][2].handlers.onClick();t=draw()
t.rows[3][2].handlers.onClick();t=draw()
-- Order stays frozen while open, even when supply states change.
shortage[9][2][2], shortage[9][2][8] = 500, 5000;supplied[9][1][2], supplied[9][1][8]=0,0
now=31;refreshes=0;refreshRequests={}
assert(menu.onUpdate()==73 and refreshes==1, 'expanded ware state change rebuilds')
t=draw();assert(names(t)=='Hub 43,Hub 42,Hub 44')
-- One refresh request per second, rotating across expanded hubs.
assert(#refreshRequests==1)
menu.onUpdate();assert(#refreshRequests==1)
now=31.5;menu.onUpdate();assert(#refreshRequests==1)
now=32;menu.onUpdate();assert(#refreshRequests==2 and refreshRequests[1]~=refreshRequests[2])
now=33;menu.onUpdate();assert(#refreshRequests==3 and refreshRequests[3]==refreshRequests[1])
assert(refreshes==1, 'no rebuild without a structural change')
-- A collapsed hub's change is live only.
paused[2]=3;now=34;menu.onUpdate();assert(refreshes==1)
-- Leaving the mode forgets the order but keeps expansion.
menu.infoTableMode='objectlist';menu.onUpdate();menu.infoTableMode='ce_hubs'
t=draw();assert(names(t)=='Hub 42,Hub 43,Hub 44', names(t))
assert(value(t.rows[3][2])=='-')
-- New hubs append; removed hubs disappear.
hubs={42,43,44,45};statuses={supplied,shortage,paused,snapshot(45,1)};now=40
menu.onUpdate();assert(refreshes==2);t=draw();assert(names(t)=='Hub 42,Hub 43,Hub 44,Hub 45', names(t))
hubs={43,45};now=41;menu.onUpdate();t=draw();assert(names(t)=='Hub 43,Hub 45')
-- Cleanup forgets expansion.
assert(menu.cleanup()==74 and nativeCleanups==1)
hubs={42,43,44};statuses={supplied,shortage,paused};now=50
t=draw();for _,r in ipairs(t.rows) do if r.rowdata and type(r.rowdata)=='string' then assert(value(r[2])=='+') end end
hubs={};statuses={};now=60;t=draw()
assert(#t.rows==3 and value(t.rows[3][1])=='No known civilian hubs.' and value(t.rows[2][1])=='Hubs: 0 | Supplied: 0 | Shortage: 0')
menu.settoprow=7;hubs={42,43,44};statuses={supplied,shortage,paused};now=61;t=draw()
assert(t.topRow==7 and menu.settoprow==nil)
print('Hub list lifecycle: frozen order, rebuilds, refresh rotation, membership, cleanup and empty state passed')
''')

lua.execute(r'''
-- Double-click on a hub row selects the hub and centres the map on it (vanilla property list).
menu.infoTableMode='ce_hubs';menu.selectedcomponents={['7']={}};now=70
currentRowData='43'
assert(menu.onSelectElement(21,nil,4,false,'mouse')==75 and #focused==0, 'single click only selects the row')
assert(menu.onSelectElement(21,nil,4,true,'mouse')==75 and nativeSelects==2)
assert(focused[1]==43 and menu.selectedcomponents['43'] and not menu.selectedcomponents['7'] and selectionSyncs==1)
-- Keyboard or gamepad confirm behaves like the double-click, as in vanilla.
currentRowData='42';menu.onSelectElement(21,nil,4,false,'keyboard');assert(focused[2]==42)
-- Ignored: other tables, non-hub rows, unknown hubs, other modes and the multiverse.
currentRowData=true;menu.onSelectElement(21,nil,6,true,'mouse');assert(#focused==2)
currentRowData='43';menu.onSelectElement(5,nil,1,true,'mouse');assert(#focused==2)
currentRowData='77';menu.onSelectElement(21,nil,4,true,'mouse');assert(#focused==2)
currentRowData='43';menu.infoTableMode='propertyowned';menu.onSelectElement(21,nil,4,true,'mouse');assert(#focused==2)
menu.infoTableMode='ce_hubs';menu.showMultiverse=true;menu.onSelectElement(21,nil,4,true,'mouse');assert(#focused==2)
menu.showMultiverse=false;assert(nativeSelects==8, 'native handler always runs')
print('Hub list selection: double-click selects and focuses the hub, native handler preserved passed')
''')
