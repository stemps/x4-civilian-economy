-- Civilian selection table and compact basics-only map hover.
local M = CEHubStatus
local ffi = require('ffi')
ffi.cdef[[ uint64_t GetPickedMapComponent(uint64_t holomapid); ]]
local C = ffi.C
local registered = false
local page, selected, signature = 1, nil, nil
local order = {}
local tooltipMap
local function clearTooltip()
    if tooltipMap then SetMouseOverOverride(tooltipMap, nil); tooltipMap = nil end
end
local function normalMode(menu)
    return (menu.mode == nil or menu.mode == 'info' or menu.mode == 'infomode')
        and not menu.showMultiverse and not (menu.plotData and menu.plotData.active)
end
local function selection(menu)
    if not normalMode(menu) then return end
    local raw = next(menu.selectedcomponents or {})
    if raw and next(menu.selectedcomponents, raw) == nil then return M.get(raw) end
end
local function title(s)
    return GetComponentData(s.id, 'name') or M.text(1)
end
local PAGE_SIZE = 5

local function updateSelection(s)
    local key = tostring(s.id)
    if selected ~= key then page, order = 1, M.order(s) else
        local retained, seen = {}, {}
        for _,id in ipairs(order) do if M.find(s,id) then retained[#retained+1]=id;seen[id]=true end end
        for _,id in ipairs(M.order(s)) do if not seen[id] then retained[#retained+1]=id end end
        order=retained
    end
    selected, signature = key, M.signature(s)
    local pages = math.max(1, math.ceil(#s.wares / PAGE_SIZE))
    page = math.min(page, pages)
    return pages
end

local function createPanel(menu, frame, s)
    local data = menu.selectedShipsTableData
    local width = math.min(Helper.scaleX(1100), Helper.viewWidth - 2 *
        (menu.infoTableOffsetX + menu.infoTableWidth + 2 * Helper.borderSize))
    local border = frame:addFrameBorder('selectedships', {offset=Helper.standardContainerOffset})
    local t=frame:addTable(5,{tabOrder=21,width=width,x=(Helper.viewWidth-width)/2,y=0,
        scaling=false,reserveScrollBar=false,skipTabChange=true,
        backgroundID='solid',backgroundColor=Color['frame_background_semitransparent'],
        backgroundPadding=Helper.standardContainerOffset,frameborder=border.id})
    -- MapMenu.viewCreated binds positional widget IDs: this hook MUST add one table.
    t:setColWidth(1,1)
    t:setColWidth(2,width*0.44)
    t:setColWidth(3,width*0.18)
    t:setColWidth(4,width*0.17)
    t:setDefaultCellProperties('text',{fontsize=data.fontsize,minRowHeight=data.textHeight})
    t:setDefaultComplexCellProperties('button','text',{fontsize=data.fontsize})
    t:setDefaultComplexCellProperties('icon','text',{fontsize=data.fontsize})
    local function current() return M.get(s.id) end
    local rows={}
    local function tableRow(index)
        while #rows<index do rows[#rows+1]=t:addRow(nil,{fixed=true,borderBelow=false}) end
        return rows[index]
    end
    local function row(index)
        local result=tableRow(index+5)
        result[1]:setBackgroundColSpan(5)
        return result
    end
    local function summaryLine(index,value)
        tableRow(index+1)[1]:setColSpan(5):createText(value,{wordwrap=true})
    end
    local green = {r=18,g=85,b=43,a=100,glow=0}
    local blue = {r=12,g=85,b=140,a=100,glow=0}
    local background = Color['rowgroup_background_default']
    return {table=t, data=data, current=current, tableRow=tableRow, row=row, summaryLine=summaryLine,
        green=green, blue=blue, background=background}
end

local function drawSummary(panel, s)
    local tableRow, summaryLine, current = panel.tableRow, panel.summaryLine, panel.current
    local data, green, background = panel.data, panel.green, panel.background
    tableRow(1)[1]:setColSpan(5):createText(title(s), {font=Helper.headerRow1Font,
        halign='center', mouseOverText=title(s), wordwrap=true})
    summaryLine(1,function()
        local now=current();return M.text(116)..' '..M.population(now and now.population)
    end)
    local progress=tableRow(3)
    progress[2]:setColSpan(4)
    local function percent()
        local now=current()
        return now and now.available and now.level<10 and math.min(100,100*now.growth/now.required) or 0
    end
    local function growthHint()
        local now=current()
        return M.progress(now)..'\n'..M.state(now)..'\n'..M.action(now)
    end
    progress[1]:createStatusBar({current=percent,start=percent,max=100,
        valueColor=green,markerColor=Color['statusbar_marker_hidden'],
        width=progress[2]:getWidth(),height=data.textHeight,x=1+Helper.borderSize,scaling=false})
    progress[2]:createIcon('solid',{color=Color['icon_transparent'],height=data.textHeight,
        width=progress[2]:getWidth(),mouseOverText=growthHint,cellBGColor=background}):setText(function()
            return M.levelLabel(current())
        end,{halign='left',color=Color['text_normal']})
    summaryLine(3,function() return M.nextLevel(current()) end)
    -- Failures and explicit test overrides must remain visible, not only in a tooltip.
    if s.stale or s.profileError or s.pausedOffers or not s.available then
        summaryLine(4,function()
            local now=current()
            return (not now or not now.available or now.stale or now.profileError) and M.state(now)
                or (now.pausedOffers and M.text(70) or '')
        end)
    end
end

local function drawWareHeadings(panel)
    local row = panel.row
    local headings=row(1)
    headings[1]:setColSpan(3):createText(M.text(50), {cellBGColor=Color['row_title_background']})
    for _,entry in ipairs({{4,78},{5,91}}) do
        headings[entry[1]]:createText(M.text(entry[2]), {wordwrap=true,
            cellBGColor=Color['row_title_background'],halign=entry[1]>=5 and 'right' or 'left'})
    end
end

local function drawWareRow(panel, wareKey, index)
    local row, current, data = panel.row, panel.current, panel.data
    local blue, green, background = panel.blue, panel.green, panel.background
    local r=row(index)
    local function ware() return M.find(current(),wareKey) end
    local function hint() local w=ware();return w and M.wareHint(current(),w) or M.text(68) end
    local w=ware()
    -- A single visual ware column: name left, remaining time right, stock behind both.
    r[1].properties.cellBGColor=background
    -- All ware labels share the same baseline within the selection table.
    r[2]:createText(function()
        local now=ware();return now and now.name or M.text(69)
    end,{halign='left',mouseOverText=hint,color=Color['text_normal']})
    local function fill() local now=ware();return now and now.capacity>0 and math.min(100,now.reserve/now.capacity*100) or 0 end
    local function futureFill()
        local now=ware();return now and now.capacity>0 and math.min(100,(now.reserve+now.incoming)/now.capacity*100) or 0
    end
    r[1]:createStatusBar({current=futureFill,start=fill,max=100,valueColor=blue,posChangeColor=green,
        markerColor=Color['statusbar_marker_hidden'],width=r[2]:getWidth()+Helper.borderSize+r[3]:getWidth(),height=data.textHeight,
        x=1+Helper.borderSize,scaling=false,cellBGColor=background})
    r[3]:createText(function()
        local now=ware();return now and M.remaining(now) or M.text(69)
    end,{halign='right',mouseOverText=hint,color=Color['text_normal']})
    for col=4,5 do
        local column=col
        r[col]:createText(function()
            local now=ware();return now and M.columns(current(),now)[column-1] or M.text(69)
        end,{halign=col>4 and 'right' or 'left',mouseOverText=hint,wordwrap=col==4,
            cellBGColor=background,color=Color[col==4 and M.wareColor(w) or 'text_normal']})
    end
end

local function drawPagination(panel, menu, pages)
    local row, data = panel.row, panel.data
    if pages > 1 then
        local r = row(7)
        r[1]:setColSpan(2):createButton({active=page > 1,height=data.textHeight}):setText(M.text(66))
        r[1].handlers.onClick = function() page=math.max(1,page-1);menu.refreshMainFrame=true end
        r[3]:setColSpan(2):createText(M.text(72,page,pages),{halign='center'})
        r[5]:createButton({active=page < pages,height=data.textHeight}):setText(M.text(67))
        r[5].handlers.onClick = function() page=math.min(pages,page+1);menu.refreshMainFrame=true end
    end
end

local function draw(menu, frame, s)
    local pages = updateSelection(s)
    local panel = createPanel(menu, frame, s)
    drawSummary(panel, s)
    drawWareHeadings(panel)
    local first = (page - 1) * PAGE_SIZE + 1
    for index=first, math.min(page * PAGE_SIZE, #order) do
        drawWareRow(panel, order[index], index - first + 2)
    end
    if #s.wares == 0 then
        panel.row(2)[1]:setColSpan(5):createText(s.available and M.text(71) or M.text(68),
            {wordwrap=true,cellBGColor=panel.background})
    end
    drawPagination(panel, menu, pages)
    panel.table.properties.y=Helper.viewHeight-panel.table:getFullHeight()-Helper.borderSize
        -menu.borderOffset-Helper.standardContainerOffset
end
local function register()
    if registered then return true end
    local menu = Helper and Helper.getMenu and Helper.getMenu('MapMenu')
    if not menu or type(menu.createSelectedShips) ~= 'function'
        or type(menu.onUpdate) ~= 'function' or type(menu.cleanup) ~= 'function' then return false end
    local nativeDraw, nativeUpdate, nativeCleanup = menu.createSelectedShips, menu.onUpdate, menu.cleanup
    menu.createSelectedShips = function(frame, ...)
        local s = selection(menu)
        if s then return draw(menu, frame, s) end
        page, selected, signature = 1, nil, nil
        return nativeDraw(frame, ...)
    end
    menu.onUpdate = function(...)
        -- Native update can switch mode and install its own special-mode tooltip.
        clearTooltip()
        local result = nativeUpdate(...)
        local s = selection(menu)
        if selected and (not s or signature ~= M.signature(s)) then menu.refreshMainFrame = true end
        if normalMode(menu) and menu.map and menu.holomap and menu.holomap ~= 0 then
            local x, y = GetRenderTargetMousePosition(menu.map)
            local hovered = x and y and M.get(C.GetPickedMapComponent(menu.holomap))
            if hovered then
                SetMouseOverOverride(menu.map, M.tooltip(hovered))
                tooltipMap = menu.map
            end
        end
        return result
    end
    menu.cleanup = function(...)
        clearTooltip()
        page, selected, signature = 1, nil, nil
        M.reset()
        return nativeCleanup(...)
    end
    registered = true
    DebugError('[CE] Civilian map status registered')
    return true
end
if not register() and type(Register_OnLoad_Init) == 'function' then Register_OnLoad_Init(register, 'ce_map_status') end
RegisterEvent('CEPopulationRequest', function() if not registered then register() end end)
