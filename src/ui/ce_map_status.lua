-- Civilian selection panel (bottom centre, one selected hub) and compact map hover.
-- Rows come from the shared hub sections (ce_hub_sections.lua), as in the sidebar
-- list; this module owns placement, scrolling, refresh throttling and the hover.
local M, S = CEHubStatus, CEHubSections
local ffi = require('ffi')
ffi.cdef[[ uint64_t GetPickedMapComponent(uint64_t holomapid); ]]
local C = ffi.C
local registered = false
-- Rows 1-2 are the fixed vanilla-style title and the growth row; sections scroll.
local FIXED_ROWS = 2
local topRow, selected, signature = nil, nil, nil
local order = {}
local eventSignature
local tooltipMap
local refreshHub, refreshAt
local function requestRefresh(s)
    if not s then refreshHub, refreshAt = nil, nil; return end
    local key, now = tostring(s.id), getElapsedTime()
    if refreshHub ~= key or not refreshAt or now >= refreshAt or now < refreshAt - 1 then
        refreshHub, refreshAt = key, now + 1
        M.requestRefresh(key)
    end
end
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
-- Structure that needs a rebuild: wares, states, events, level and bonus payload.
local function structure(s)
    return M.signature(s) .. '\n' .. tostring(s.rewards ~= nil)
end

-- Ware order is frozen while the same hub stays selected; new wares append and
-- removed wares disappear. A new event set scrolls back to the top.
local function updateSelection(s)
    local key = tostring(s.id)
    if selected ~= key then topRow, order = nil, M.order(s) else
        local retained, seen = {}, {}
        for _,id in ipairs(order) do if M.find(s,id) then retained[#retained+1]=id;seen[id]=true end end
        for _,id in ipairs(M.order(s)) do if not seen[id] then retained[#retained+1]=id end end
        order=retained
    end
    local newEvents = M.eventSignature(s)
    if eventSignature ~= newEvents then topRow = nil end
    eventSignature = newEvents
    selected, signature = key, structure(s)
end

local function createPanel(menu, frame, data)
    local width = math.min(Helper.scaleX(1100), Helper.viewWidth - 2 *
        (menu.infoTableOffsetX + menu.infoTableWidth + 2 * Helper.borderSize))
    local border = frame:addFrameBorder('selectedships', {offset=Helper.standardContainerOffset})
    -- MapMenu.viewCreated binds positional widget IDs: this hook MUST add one table.
    -- reserveScrollBar=false keeps measured and rendered widths identical for the
    -- bottom anchoring (see renderedHeight); so no icon may reach the last column.
    local t=frame:addTable(S.COLUMNS,{tabOrder=21,width=width,x=(Helper.viewWidth-width)/2,y=0,
        scaling=false,reserveScrollBar=false,skipTabChange=true,maxVisibleHeight=math.floor(Helper.viewHeight*0.4),
        backgroundID='solid',backgroundColor=Color['frame_background_semitransparent'],
        backgroundPadding=Helper.standardContainerOffset,frameborder=border.id})
    S.configure(t, data, width, 0.18)
    return t
end

-- Bottom anchoring needs the height the widget system will draw, not Helper's
-- getVisibleHeight(). A scrolling table is drawn with whole rows only, starting at
-- the first scrolling row, and keeps that height (widget_fullscreen.lua
-- drawTableSection / initial table setup). Helper instead reports the full cap.
-- Requires reserveScrollBar=false: otherwise Helper widens the last column only
-- after this measurement, when no scrollbar is needed, and wrapped text shrinks.
local function renderedHeight(t)
    local cap = t.getMaxVisibleHeight and t:getMaxVisibleHeight() or t.properties.maxVisibleHeight
    local rows, heights, full, fixed, tallest = t.rows, {}, 0, 0, 0
    for i, r in ipairs(rows) do
        heights[i] = r:getHeight() + (r.properties.paddingTop or 0) + (r.properties.paddingBottom or 0)
        full = full + heights[i]
        if i < #rows and r.properties.borderBelow then full = full + Helper.borderSize end
        if r.properties.fixed then fixed = fixed + heights[i] else tallest = math.max(tallest, heights[i]) end
    end
    -- Native minimum for a scrolling table: fixed rows plus one selectable row group.
    local minimum = fixed + math.max(tallest, 35)
    if not cap or cap <= 0 or full <= cap or full <= minimum then return full end
    local height = 0
    for i, r in ipairs(rows) do
        local next = heights[i] + ((i > 1 and rows[i-1].properties.borderBelow) and Helper.borderSize or 0)
        if not r.properties.fixed and height + next > cap then break end
        height = height + next
    end
    return math.min(cap, math.max(height, minimum))
end

-- Vanilla single-object title (menu_map.lua createSelectedShips): the station icon
-- and "name (idcode)" centred in headerRow1Font, in the object's map colour.
local function drawTitle(menu, t, s)
    local name, icon, idcode = GetComponentData(s.id, 'name', 'icon', 'idcode')
    local title = (name or M.text(55)) .. ((idcode and idcode ~= '') and (' (' .. idcode .. ')') or '')
    if icon and icon ~= '' then title = '\27[' .. icon .. '] ' .. title end
    local color = type(menu.getObjectColor) == 'function' and menu.getObjectColor(s.id) or Color['text_normal']
    local r = t:addRow(nil, {fixed=true, borderBelow=false})
    r[1]:setColSpan(S.COLUMNS):createText(title, {halign='center', color=color, font=Helper.headerRow1Font,
        fontsize=Helper.scaleFont(Helper.headerRow1Font, Helper.headerRow1FontSize),
        minRowHeight=Helper.scaleY(Helper.headerRow1Height), mouseOverText=title})
    return r
end

local function draw(menu, frame, s)
    updateSelection(s)
    local data = S.metrics(false)
    local t = createPanel(menu, frame, data)
    drawTitle(menu, t, s)
    S.drawProgress(t, data, s, {fixed=true})
    S.drawDetails(t, data, s, {wareOrder=order, incoming=true})
    local first = FIXED_ROWS + 1
    local restored = type(topRow) == 'number' and topRow or first
    t:setTopRow(math.max(first, math.min(restored, #t.rows)))
    t.ceRenderedHeight=renderedHeight(t)
    -- Leave two pixels of clearance for native widget rounding at the bottom edge.
    t.properties.y=math.floor(Helper.viewHeight-math.ceil(t.ceRenderedHeight)-Helper.borderSize
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
        requestRefresh(s)
        if s then return draw(menu, frame, s) end
        topRow, selected, signature = nil, nil, nil
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
        requestRefresh(s)
        if selected and (not s or signature ~= structure(s)) then menu.refreshMainFrame = true end
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
        requestRefresh(nil)
        topRow, selected, signature = nil, nil, nil
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
