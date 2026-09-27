-- Civilian selection table and compact basics-only map hover.
local M = CEHubStatus
local ffi = require('ffi')
ffi.cdef[[ uint64_t GetPickedMapComponent(uint64_t holomapid); ]]
local C = ffi.C
local registered = false
local topRow, selected, signature = 7, nil, nil
local order = {}
local eventSignature
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

local function updateSelection(s)
    local key = tostring(s.id)
    if selected ~= key then topRow, order = M.eventSignature(s) ~= '' and 6 or 7, M.order(s) else
        local retained, seen = {}, {}
        for _,id in ipairs(order) do if M.find(s,id) then retained[#retained+1]=id;seen[id]=true end end
        for _,id in ipairs(M.order(s)) do if not seen[id] then retained[#retained+1]=id end end
        order=retained
    end
    local newEvents = M.eventSignature(s)
    if eventSignature ~= newEvents then topRow = newEvents ~= '' and 6 or 7 end
    eventSignature = newEvents
    selected, signature = key, M.signature(s)
end

local function createPanel(menu, frame, s)
    local data = menu.selectedShipsTableData
    local eventCount = s.demandEvents and #s.demandEvents.events or 0
    local fixedRows = eventCount > 0 and 5 or 6
    local width = math.min(Helper.scaleX(1100), Helper.viewWidth - 2 *
        (menu.infoTableOffsetX + menu.infoTableWidth + 2 * Helper.borderSize))
    local border = frame:addFrameBorder('selectedships', {offset=Helper.standardContainerOffset})
    local t=frame:addTable(5,{tabOrder=21,width=width,x=(Helper.viewWidth-width)/2,y=0,
        scaling=false,reserveScrollBar=true,skipTabChange=true,maxVisibleHeight=math.floor(Helper.viewHeight*0.4),
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
        while #rows<index do
            local fixed = #rows<fixedRows
            -- Native scrolling keeps each selectable row and following plain rows
            -- together. Give each scrolling row its own boundary, as vanilla does
            -- for informational capacity rows, without making it interactive.
            rows[#rows+1]=t:addRow(not fixed or nil,{fixed=fixed,interactive=false,borderBelow=false})
        end
        return rows[index]
    end
    local function row(index)
        local result=tableRow(index+5+eventCount)
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
        green=green, blue=blue, background=background, eventCount=eventCount, fixedRows=fixedRows}
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
        return M.progressHint(current())
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
    elseif s.unrest then
        summaryLine(4,function() return M.unrest(current()) end)
    end
    for index, event in ipairs(s.demandEvents and s.demandEvents.events or {}) do
        local eventID = event.id
        tableRow(5+index)[1]:setColSpan(5):createText(function() return M.eventText(current(), eventID) end,
            {wordwrap=true, mouseOverText=function() return M.eventHint(current(), eventID) end})
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

local function draw(menu, frame, s)
    updateSelection(s)
    local panel = createPanel(menu, frame, s)
    drawSummary(panel, s)
    drawWareHeadings(panel)
    for index, wareKey in ipairs(order) do
        drawWareRow(panel, wareKey, index + 1)
    end
    if #s.wares == 0 then
        panel.row(2)[1]:setColSpan(5):createText(s.available and M.text(71) or M.text(68),
            {wordwrap=true,cellBGColor=panel.background})
    end
    local restoredTopRow = type(topRow) == 'number' and topRow or panel.fixedRows+1
    panel.table:setTopRow(math.max(panel.fixedRows+1, math.min(restoredTopRow, math.max(panel.fixedRows+1, math.max(1,#order)+6+panel.eventCount))))
    -- Leave two pixels of clearance for native widget rounding at the bottom edge.
    panel.table.properties.y=math.floor(Helper.viewHeight-math.ceil(panel.table:getVisibleHeight())-Helper.borderSize
        -menu.borderOffset-Helper.standardContainerOffset-2)
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
        topRow, selected, signature = 7, nil, nil
        eventSignature = nil
        return nativeDraw(frame, ...)
    end
    menu.onUpdate = function(...)
        -- Native update can switch mode and install its own special-mode tooltip.
        clearTooltip()
        -- Capture the live scroll position before nativeUpdate may rebuild the frame.
        local before = selection(menu)
        if before and selected == tostring(before.id) and menu.selectedShipsTable and menu.selectedShipsTable ~= 0 then
            local liveTopRow = GetTopRow(menu.selectedShipsTable)
            if type(liveTopRow) == 'number' then topRow = liveTopRow end
        end
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
        topRow, selected, signature = 7, nil, nil
        eventSignature = nil
        M.reset()
        return nativeCleanup(...)
    end
    registered = true
    DebugError('[CE] Civilian map status registered')
    return true
end
if not register() and type(Register_OnLoad_Init) == 'function' then Register_OnLoad_Init(register, 'ce_map_status') end
RegisterEvent('CEPopulationRequest', function() if not registered then register() end end)
