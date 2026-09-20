-- Civilian selection table and compact basics-only map hover.
local M = CEHubStatus
local ffi = require('ffi')
ffi.cdef[[ uint64_t GetPickedMapComponent(uint64_t holomapid); ]]
local C = ffi.C
local registered = false
local page, selected, signature = 1, nil, nil
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
local function draw(menu, frame, s)
    local key = tostring(s.id)
    if selected ~= key then page = 1 end
    selected, signature = key, M.signature(s)
    local pages = math.max(1, math.ceil(#s.wares / 5))
    page = math.min(page, pages)
    local data = menu.selectedShipsTableData
    local width = math.min(Helper.scaleX(840), Helper.viewWidth - 2 *
        (menu.infoTableOffsetX + menu.infoTableWidth + 2 * Helper.borderSize))
    local border = frame:addFrameBorder('selectedships', {offset=Helper.standardContainerOffset})
    local t = frame:addTable(6, {tabOrder=21, width=width, x=(Helper.viewWidth-width)/2,
        y=0, scaling=false, reserveScrollBar=false, skipTabChange=true,
        backgroundID='solid', backgroundColor=Color['frame_background_semitransparent'],
        backgroundPadding=Helper.standardContainerOffset, frameborder=border.id})
    -- One-pixel anchor columns let native status bars sit behind the text cells,
    -- matching vanilla createSelectedShips' storage bars without text glyph art.
    t:setColWidth(1, width * 0.26)
    t:setColWidth(2, width * 0.30)
    t:setColWidth(3, 1)
    t:setColWidth(4, width * 0.21)
    t:setColWidth(5, 1)
    t:setDefaultBackgroundColSpan(1, 6)
    t:setDefaultCellProperties('text', {fontsize=data.fontsize, minRowHeight=data.textHeight})
    t:setDefaultComplexCellProperties('button', 'text', {fontsize=data.fontsize})
    t:setDefaultComplexCellProperties('icon', 'text', {fontsize=data.fontsize})
    local function current() return M.get(s.id) end
    local function row() return t:addRow(nil, {fixed=true, borderBelow=false}) end
    local function full(value, properties) row()[1]:setColSpan(6):createText(value, properties or {}) end
    full(title(s), {font=Helper.headerRow1Font, halign='center', mouseOverText=title(s), wordwrap=true})
    local basic = row()
    basic[1]:createText(M.text(77))
    basic[2]:createText(function()
        local now = current()
        return now and now.level and string.format('%.0f', now.level) or M.text(69)
    end, {halign='right'})
    basic[3]:setColSpan(2):createText(M.text(76))
    basic[5]:setColSpan(2):createText(function()
        local now = current(); return M.population(now and now.population)
    end, {halign='right'})
    local state = row()
    state[1]:createText(M.text(78))
    state[2]:setColSpan(3):createText(function() return M.state(current()) end)
    state[5]:setColSpan(2):createText(function()
        local now = current(); return now and now.pausedOffers and M.text(70) or ''
    end, {halign='right', wordwrap=true})
    local history = row()
    history[1]:createText(M.text(60))
    history[2]:setColSpan(3):createText(function() return M.history(current()) end)
    history[5]:setColSpan(2):createText(function() return M.historyState(current()) end,
        {halign='right', wordwrap=true})
    local headings = row()
    headings[1]:createText(M.text(50), {mouseOverText=M.text(54)})
    headings[2]:createText(M.text(51), {halign='right', mouseOverText=M.text(61)})
    headings[3]:setColSpan(2):createText(M.text(52), {halign='center', mouseOverText=M.text(62)})
    headings[5]:setColSpan(2):createText(M.text(53), {halign='center', mouseOverText=M.text(63)})
    for index = (page - 1) * 5 + 1, math.min(page * 5, #s.wares) do
        local wareIndex = index
        local r = row()
        local function ware()
            local now = current(); return now, now and now.wares[wareIndex]
        end
        local function hint(field)
            return function()
                local now, w = ware(); return w and M.wareHint(now, w, field) or M.text(68)
            end
        end
        for col = 1, 2 do
            local column = col
            r[col]:createText(function()
                local now = current()
                local w = now and now.wares[wareIndex]
                return w and M.columns(now, w)[column] or M.text(69)
            end, {halign=column == 1 and 'left' or 'right', mouseOverText=hint(column == 1 and 'ware' or 'demand')})
        end
        for i, field in ipairs({'fulfillment', 'reliability'}) do
            local metric = field
            local anchor, col = i * 2 + 1, i * 2 + 2
            local function score()
                local now, w = ware(); return M.score(now, w, metric)
            end
            local function fill() return math.min(100, math.max(0, score() or 0)) end
            r[anchor]:createStatusBar({current=fill, start=fill, max=100,
                valueColor=Color['statusbar_value_default'], markerColor=Color['statusbar_marker_hidden'],
                width=r[col]:getWidth(), height=data.textHeight, x=1 + Helper.borderSize, scaling=false})
            r[col]:createIcon('solid', {color=Color['icon_transparent'], height=data.textHeight,
                mouseOverText=hint(metric)}):setText(function()
                    local now = current()
                    return now and M.percent(score(), now) or M.text(69)
                end, {halign='right'})
        end
    end
    if #s.wares == 0 then full(s.available and M.text(71) or M.text(68)) end
    if pages > 1 then
        local r = row()
        r[1]:createButton({active=page > 1, height=data.textHeight}):setText(M.text(66))
        r[1].handlers.onClick = function() page=math.max(1, page-1); menu.refreshMainFrame=true end
        r[2]:setColSpan(3):createText(M.text(72, page, pages), {halign='center'})
        r[5]:setColSpan(2):createButton({active=page < pages, height=data.textHeight}):setText(M.text(67))
        r[5].handlers.onClick = function() page=math.min(pages, page+1); menu.refreshMainFrame=true end
    end
    t.properties.y = Helper.viewHeight - t:getFullHeight() - Helper.borderSize
        - menu.borderOffset - Helper.standardContainerOffset
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
