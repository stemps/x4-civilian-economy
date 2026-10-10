-- Map left-sidebar list of every known civilian hub. Needs UI Extensions:
-- vanilla keeps config.leftBar local and has no custom info-frame mode.
-- Section drawing is shared with the selected-hub panel (ce_hub_sections.lua).
local M, S = CEHubStatus, CEHubSections
local ffi = require('ffi')
local C = ffi.C
-- Vanilla menu_map declares this too; a duplicate declaration is harmless under pcall.
pcall(ffi.cdef, [[ void SetFocusMapComponent(uint64_t holomapid, uint64_t componentid, bool resetplayerpan); ]])
local MODE = 'ce_hubs'
local registered = false
local menu
-- Expanded hubs and the frozen display order live for one map session only.
local expanded, order = {}, nil
local signature, checkAt, refreshIndex = nil, nil, 0
local selectRow
local COLUMNS = S.COLUMNS

-- Shortage first, then the earliest exhaustion. Kept while the panel is open so
-- rows do not jump; new hubs append and removed hubs disappear.
local function ordered(list)
    local byKey, fresh = {}, {}
    for _, s in ipairs(list) do byKey[tostring(s.id)] = s end
    local result, seen = {}, {}
    for _, key in ipairs(order or {}) do
        if byKey[key] then result[#result + 1] = byKey[key]; seen[key] = true end
    end
    for _, s in ipairs(list) do if not seen[tostring(s.id)] then fresh[#fresh + 1] = s end end
    local keys = {}
    for _, s in ipairs(fresh) do
        local supply = M.supply(s)
        keys[s] = {supply.rank, supply.seconds or math.huge, S.name(s.id), tostring(s.id)}
    end
    table.sort(fresh, function(a, b)
        local x, y = keys[a], keys[b]
        for i = 1, 4 do if x[i] ~= y[i] then return x[i] < y[i] end end
        return false
    end)
    for _, s in ipairs(fresh) do result[#result + 1] = s end
    order = {}
    for _, s in ipairs(result) do order[#order + 1] = tostring(s.id) end
    return result
end

-- Collapsed rows are fully live; only expanded content has structure to rebuild.
local function listSignature(list)
    local parts = {}
    for _, s in ipairs(list) do
        local key = tostring(s.id)
        parts[#parts + 1] = expanded[key] and M.signature(s) .. '\n' .. tostring(s.rewards ~= nil) or key
    end
    table.sort(parts)
    return table.concat(parts, '\n\n')
end

local function counts()
    local total, supplied, shortage = 0, 0, 0
    for _, s in ipairs(M.hubs()) do
        total = total + 1
        local code = M.supply(s).code
        if code == 'shortage' then shortage = shortage + 1
        elseif code ~= 'inactive' then supplied = supplied + 1 end
    end
    return total, supplied, shortage
end

local function createTable(frame, data)
    local border = frame:addFrameBorder('ce_hubs', {
        offset = Helper.standardContainerOffset,
        offsetTop = -Helper.standardContainerOffset,
        active = menu.panelState and menu.panelState.leftmenu,
        color = Helper.getFrameBorderColor(menu, menu.panelState and menu.panelState.leftmenu, menu.panelPins and menu.panelPins.leftmenu),
        linewidth = Helper.getFrameBorderLineWidth(menu, menu.panelState and menu.panelState.leftmenu),
    })
    Helper.setFrameBorderIcon(menu, border, 'left', menu.sideBarWidth / 2)
    local width = frame.properties.width - 2 * Helper.standardContainerOffset
    -- MapMenu.viewCreated binds the first info-frame table as menu.infoTable.
    local t = frame:addTable(COLUMNS, {tabOrder=1, x=Helper.standardContainerOffset, width=width,
        -- Reserve the scrollbar (vanilla default): without it Helper narrows the last
        -- column only once the list scrolls, after the item icon spanning it was sized,
        -- and the engine logs "icon width exceeds the maximum available width" each frame.
        scaling=false, reserveScrollBar=true, backgroundID='solid',
        backgroundColor=Color['container_subsection_background'], backgroundPadding=0, frameborder=border.id})
    S.configure(t, data, width, 0.28)
    return t
end

local function drawHeader(t, data)
    local title = t:addRow(nil, {fixed=true})
    title[1]:setColSpan(COLUMNS):createText(M.text(460), {font=Helper.titleFont,
        fontsize=Helper.scaleFont(Helper.titleFont, Helper.titleFontSize), halign='center',
        cellBGColor=Color['container_panel_header'], minRowHeight=Helper.scaleY(Helper.largeRowHeight)})
    local summary = t:addRow(nil, {fixed=true})
    summary[1]:setColSpan(COLUMNS):createText(function() return M.text(462, counts()) end,
        {halign='center', wordwrap=true})
end

-- The sidebar item: a hub row with the expand button.
local function drawItem(t, data, s)
    local key = tostring(s.id)
    S.drawItem(t, data, s, {rowdata=key, button={text=expanded[key] and '-' or '+', onClick=function(head)
        expanded[key] = not expanded[key] or nil
        selectRow = head.index
        menu.refreshInfoFrame()
    end}})
end

local function draw(frame)
    local data = S.metrics(true)
    frame.properties.autoFrameHeightPadding = Helper.standardContainerOffset
    local t = createTable(frame, data)
    drawHeader(t, data)
    local list = ordered(M.hubs())
    signature = listSignature(list)
    if #list == 0 then
        local r = t:addRow(true, {interactive=false})
        r[1]:setColSpan(COLUMNS):createText(M.text(465), {wordwrap=true})
    end
    for _, s in ipairs(list) do
        local key = tostring(s.id)
        drawItem(t, data, s)
        if expanded[key] then
            S.drawDetails(t, data, s)
            S.gap(t, data.blockGap)
        end
    end
    t.properties.maxVisibleHeight = Helper.viewHeight - frame.properties.y - Helper.frameBorder
    if type(menu.settoprow) == 'number' and menu.settoprow > 0 then t:setTopRow(menu.settoprow) end
    menu.settoprow = nil
    if selectRow then t:setSelectedRow(selectRow); selectRow = nil end
end

-- One refresh request per second, rotating through expanded hubs.
local function requestRefresh(list)
    local keys = {}
    for _, s in ipairs(list) do if expanded[tostring(s.id)] then keys[#keys + 1] = tostring(s.id) end end
    if #keys == 0 then return end
    refreshIndex = refreshIndex % #keys + 1
    M.requestRefresh(keys[refreshIndex])
end

local function update()
    local now = getElapsedTime()
    if checkAt and now < checkAt and now >= checkAt - 1 then return end
    checkAt = now + 1
    local list = M.hubs()
    requestRefresh(list)
    if signature and listSignature(list) ~= signature then
        signature = nil
        menu.refreshInfoFrame()
    end
end

local function reset(all)
    order, signature, checkAt, selectRow = nil, nil, nil, nil
    if all then expanded, refreshIndex = {}, 0 end
end

local function addSidebarEntry(config)
    local bar = config and config.leftBar
    if type(bar) ~= 'table' then return end
    for _, entry in ipairs(bar) do if entry.mode == MODE then return end end
    local position = #bar + 1
    for i, entry in ipairs(bar) do
        if entry.mode == 'info' then position = i + 1; break end
    end
    table.insert(bar, position, {spacing=true})
    table.insert(bar, position + 1, {name=M.text(460), icon='stationbuildst_habitation', mode=MODE,
        helpOverlayID='ce_map_sidebar_hubs', helpOverlayText=M.text(461)})
end

-- Double-click (or a keyboard/gamepad select) on a hub row selects that hub and
-- centres the map on it, like vanilla's property list (menu.onSelectElement).
local function selectHub(uitable, isdblclick, input)
    if menu.infoTableMode ~= MODE or menu.showMultiverse or uitable ~= menu.infoTable then return end
    if not (isdblclick or input ~= 'mouse') then return end
    local rowdata = Helper.getCurrentRowData(menu, uitable)
    local s = type(rowdata) == 'string' and M.get(rowdata)
    if not s or not menu.holomap or menu.holomap == 0 then return end
    -- Clears the old selection first, so an NPC hub can replace selected player ships.
    menu.addSelectedComponent(s.id)
    menu.setSelectedMapComponents()
    C.SetFocusMapComponent(menu.holomap, s.id, true)
end

local function register()
    if registered then return true end
    menu = Helper and Helper.getMenu and Helper.getMenu('MapMenu')
    if not menu or type(menu.registerCallback) ~= 'function' or type(menu.onUpdate) ~= 'function'
        or type(menu.cleanup) ~= 'function' then return false end
    menu.registerCallback('createSideBar_on_start', addSidebarEntry, 'civilian_economy_hubs')
    menu.registerCallback('createInfoFrame_on_menu_infoTableMode', function(frame)
        if menu.infoTableMode ~= MODE or menu.showMultiverse then return end
        draw(frame)
    end, 'civilian_economy_hubs')
    local nativeUpdate, nativeCleanup = menu.onUpdate, menu.cleanup
    menu.onUpdate = function(...)
        local result = nativeUpdate(...)
        if menu.infoTableMode == MODE and not menu.showMultiverse then update() elseif order then reset(false) end
        return result
    end
    menu.cleanup = function(...)
        reset(true)
        return nativeCleanup(...)
    end
    -- Helper looks menu.onSelectElement up by name per event, so wrapping works.
    local nativeSelect = menu.onSelectElement
    menu.onSelectElement = function(uitable, modified, row, isdblclick, input, ...)
        selectHub(uitable, isdblclick, input)
        if nativeSelect then return nativeSelect(uitable, modified, row, isdblclick, input, ...) end
    end
    registered = true
    DebugError('[CE] Civilian hub list registered')
    return true
end
if not register() and type(Register_OnLoad_Init) == 'function' then Register_OnLoad_Init(register, 'ce_hub_list') end
RegisterEvent('CEPopulationRequest', function() if not registered then register() end end)
