-- Map left-sidebar list of every known civilian hub. Needs UI Extensions:
-- vanilla keeps config.leftBar local and has no custom info-frame mode.
local M, R = CEHubStatus, CERewardStatus
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
local frameTime, frameCache = nil, {}
local green = {r=18,g=85,b=43,a=100,glow=0}
local blue = {r=12,g=85,b=140,a=100,glow=0}
local sectionColor = {r=120,g=180,b=230,a=100,glow=0}
local COLUMNS = 7

-- Cells read live values every frame; decode each snapshot at most once per frame.
local function hub(key)
    local now = getElapsedTime()
    if frameTime ~= now then frameTime, frameCache = now, {} end
    if frameCache[key] == nil then frameCache[key] = M.get(key) or false end
    return frameCache[key] or nil
end
local function name(id)
    return GetComponentData(id, 'name') or M.text(55)
end

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
        keys[s] = {supply.rank, supply.seconds or math.huge, name(s.id), tostring(s.id)}
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
    -- [bar anchor] [+/-] [label] [flex] [time] [right] [right]
    -- The 1px first column anchors every status bar; bars are shifted past the button
    -- column, so content cells start right after it.
    t:setColWidth(1, 1)
    t:setColWidth(2, data.textHeight)
    t:setColWidth(3, math.floor(width * 0.28))
    t:setColWidth(5, math.floor(width * 0.14))
    t:setColWidth(6, math.floor(width * 0.16))
    t:setColWidth(7, math.floor(width * 0.14))
    t:setDefaultCellProperties('text', {fontsize=data.fontsize, minRowHeight=data.textHeight})
    t:setDefaultComplexCellProperties('button', 'text', {fontsize=data.fontsize})
    t:setDefaultComplexCellProperties('icon', 'text', {fontsize=data.fontsize})
    t:setDefaultComplexCellProperties('icon', 'text2', {fontsize=data.fontsize})
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

-- Scrolling rows stay selectable (but inert) so native scrolling keeps working.
local function plainRow(t, properties)
    properties = properties or {}
    properties.interactive, properties.borderBelow = false, false
    return t:addRow(true, properties)
end
-- Content areas share one background; section headings use vanilla's title blue.
local content = function() return Color['rowgroup_background_default'] end
local heading = function() return Color['row_title_background'] end
-- A text cell here would be invalid: its 5px side offsets exceed the 3px column.
-- Bars sit in column 1 and start after the button column.
local function barOffset(r)
    return r[1]:getWidth() + r[2]:getWidth() + 2 * Helper.borderSize
end
-- An expanded-block row. Vanilla addRow copies the row bgColor into every cell, so
-- the whole row shares one background; the leading columns override it.
local function blockRow(t, background)
    local r = plainRow(t, {bgColor=background or content()})
    r[1].properties.cellBGColor = Color['row_background']
    r[2].properties.cellBGColor = Color['row_background']
    return r
end
-- Empty spacing row, like vanilla table:addEmptyRow but selectable for scrolling.
-- Gaps stay transparent, so sections read as separate cards.
local function gap(t, height)
    local r = plainRow(t)
    r[1]:setColSpan(COLUMNS):createText('', {fontsize=1, minRowHeight=height})
    return r
end
local function section(t, data, title, span)
    local r = blockRow(t, heading())
    r[3]:setColSpan(span or COLUMNS - 2):createText(title, {font=Helper.standardFontBold,
        fontsize=data.sectionFontsize, color=sectionColor})
    return r
end
local function kv(t, label, value, properties)
    local r = blockRow(t)
    r[3]:createText(label, {color=Color['text_lowlight'], wordwrap=true})
    properties = properties or {}
    properties.wordwrap = true
    r[4]:setColSpan(COLUMNS - 3):createText(value, properties)
    return r
end

-- One two-line list item per hub, like vanilla's double property rows: the
-- selection highlight surrounds the name and the progress line together.
local function drawItem(t, data, s)
    local key, id = tostring(s.id), s.id
    local function current() return hub(key) end
    -- Vanilla property rows give stations row_background_blue (getContainerNameAndColors).
    -- Default border below, like vanilla list rows; no separator line.
    local head = t:addRow(key, {bgColor=Color['row_background_blue']})
    head[2]:createButton({height=data.itemHeight}):setText(expanded[key] and '-' or '+', {halign='center'})
    head[2].handlers.onClick = function()
        expanded[key] = not expanded[key] or nil
        selectRow = head.index
        menu.refreshInfoFrame()
    end
    -- The bar anchors in the 1px first column and is shifted past the button.
    local barWidth = head[3]:getWidth() + head[4]:getWidth() + head[5]:getWidth() + 2 * Helper.borderSize
    local function percent() return M.progressPercent(current()) end
    head[1]:createStatusBar({current=percent, start=percent, max=100, valueColor=green,
        markerColor=Color['statusbar_marker_hidden'], width=barWidth, height=data.textHeight,
        x=barOffset(head),
        y=data.itemHeight-data.textHeight, scaling=false})
    local item = head[3]:setColSpan(COLUMNS - 2):createIcon('solid', {color=Color['icon_transparent'],
        height=data.itemHeight})
    local offset = Helper.scaleX(Helper.standardTextOffsetx)
    local fullName = name(id)
    -- The station's own map icon before its name, as in vanilla property rows.
    local iconID = GetComponentData(id, 'icon')
    local label = (iconID and iconID ~= '' and '\27[' .. iconID .. '] ' or '') .. fullName
    local shown = TruncateText(label, Helper.standardFont, data.fontsize, item:getColSpanWidth() - 2 * offset)
    item.properties.mouseOverText = function()
        local now = current()
        local prefix = shown ~= label and fullName .. '\n\n' or ''
        return prefix .. M.supplyText(now) .. '\n\n' .. M.progressHint(now)
    end
    -- The progress line is greyed so the name stays the focus.
    local lowlight = Helper.convertColorToText(Color['text_lowlight'])
    item:setText(function() return shown .. '\n' .. lowlight .. M.progressShort(current()) .. '\27X' end,
        {halign='left', x=offset, color=Color['text_normal']})
    -- Vanilla only uses function-valued TEXT on icon sub-texts; color via an inline escape.
    item:setText2(function()
        local now = current()
        return '\n' .. Helper.convertColorToText(Color[M.supplyColor(now)]) .. M.supplyCompact(now) .. '\27X'
    end, {halign='right', x=offset})
end

local function drawOverview(t, data, key, s)
    local function current() return hub(key) end
    section(t, data, M.text(468))
    kv(t, M.text(116), function() local now = current(); return M.population(now and now.population) end)
    if s.available and s.level < (s.maxLevel or 10) then
        kv(t, M.text(470), function() return M.nextLevelValue(current()) end)
    end
    if s.stale or s.profileError or s.pausedOffers or not s.available then
        kv(t, M.text(78), function()
            local now = current()
            return (not now or not now.available or now.stale or now.profileError) and M.state(now)
                or (now.pausedOffers and M.text(70) or '')
        end, {color=Color['text_warning']})
    elseif s.unrest then
        kv(t, M.text(453), function() return M.unrestValue(current()) end)
        for index = 1, #M.unrestDetails(s) do
            kv(t, '', function() return M.unrestDetails(current())[index] or '' end)
        end
    end
end

local function drawEvents(t, data, key, s)
    local events = s.demandEvents and s.demandEvents.events or {}
    if #events == 0 then return end
    local function current() return hub(key) end
    gap(t, data.gap)
    section(t, data, M.text(469))
    for _, event in ipairs(events) do
        local eventID = event.id
        local hint = function() return M.eventHint(current(), eventID) end
        local r = blockRow(t)
        r[3]:setColSpan(2):createText(M.eventName(eventID), {mouseOverText=hint})
        r[5]:createText(function() return M.eventValue(current(), eventID) end, {halign='right',
            mouseOverText=hint, color=function()
                local e = M.event(current(), eventID)
                return Color[e and e.percent > 0 and 'text_warning' or 'text_normal']
            end})
        r[6]:setColSpan(2):createText(function() return M.eventRemaining(current(), eventID) end,
            {halign='right', mouseOverText=hint, color=Color['text_lowlight']})
    end
end

local function drawWares(t, data, key, s)
    local function current() return hub(key) end
    gap(t, data.gap)
    local title = section(t, data, M.text(402), 3)
    title[6]:setColSpan(2):createText(M.text(91), {halign='right'})
    if #s.wares == 0 then
        blockRow(t)[3]:setColSpan(COLUMNS - 2):createText(s.available and M.text(71) or M.text(68),
            {wordwrap=true})
        return
    end
    for _, wareKey in ipairs(M.order(s)) do
        local function ware() return M.find(current(), wareKey) end
        local function hint()
            local w = ware()
            return w and M.wareState(w) .. '\n' .. M.wareHint(current(), w) or M.text(68)
        end
        local w = ware()
        local r = plainRow(t, {bgColor=content()})
        r[1].properties.cellBGColor = Color['row_background']
        r[2].properties.cellBGColor = Color['row_background']
        local barWidth = r[3]:getWidth() + r[4]:getWidth() + r[5]:getWidth() + 2 * Helper.borderSize
        local function fill() local now = ware(); return now and now.capacity > 0 and math.min(100, now.reserve / now.capacity * 100) or 0 end
        local function futureFill()
            local now = ware(); return now and now.capacity > 0 and math.min(100, (now.reserve + now.incoming) / now.capacity * 100) or 0
        end
        -- The bar anchors in column 1 and covers the name and time columns.
        r[1]:createStatusBar({current=futureFill, start=fill, max=100, valueColor=blue, posChangeColor=green,
            markerColor=Color['statusbar_marker_hidden'], width=barWidth, height=data.textHeight,
            x=barOffset(r), scaling=false, cellBGColor=Color['row_background']})
        r[3]:setColSpan(2):createText(function() local now = ware(); return now and now.name or M.text(69) end,
            {halign='left', mouseOverText=hint, color=Color['text_normal']})
        -- Status is the colored icon and time; the label moves to the tooltip.
        r[5]:createText(function() local now = ware(); return now and M.wareTime(now) or M.text(69) end,
            {halign='right', mouseOverText=hint, color=Color[M.wareColor(w)]})
        r[6]:setColSpan(2):createText(function()
            local now = ware(); return now and M.columns(current(), now)[4] or M.text(69)
        end, {halign='right', mouseOverText=hint})
    end
end

local function drawBonuses(t, data, key, s)
    local function current() return hub(key) end
    gap(t, data.gap)
    local title = section(t, data, M.text(403), 3)
    title[6]:setColSpan(2):createText(function() return R.state(current()) end, {halign='right',
        mouseOverText=function() return R.reason(current()) end,
        color=function() return Color[R.summaryColor(current())] end})
    local lowlight = Helper.convertColorToText(Color['text_lowlight'])
    for index, entry in ipairs(R.rows(s)) do
        local function now() return R.rows(current())[index] end
        local hint = function() local e = now(); return e.value .. '\n' .. e.hint end
        local r = blockRow(t)
        if entry.locked then
            -- Locked: one grey line; the benefit is in the tooltip.
            r[3]:setColSpan(3):createText(function() return now().name end, {mouseOverText=hint,
                color=Color['text_inactive']})
            r[6]:setColSpan(2):createText('\27[menu_locked] ' .. M.text(475, entry.unlockLevel),
                {halign='right', mouseOverText=hint, color=Color['text_inactive']})
        else
            -- Unlocked: the name, with its benefit indented on a second line.
            r[3]:setColSpan(COLUMNS - 2):createText(function()
                local e = now()
                return e.name .. '\n' .. lowlight .. '   ' .. e.value .. '\27X'
            end, {mouseOverText=function() return now().hint end, wordwrap=true})
        end
    end
end

-- The same facts as the selected-hub panel, in titled sections for the narrow sidebar.
local function drawExpanded(t, data, key, s)
    gap(t, data.gap)
    drawOverview(t, data, key, s)
    drawEvents(t, data, key, s)
    drawWares(t, data, key, s)
    drawBonuses(t, data, key, s)
    gap(t, data.blockGap)
end

local function draw(frame)
    local data = {fontsize=Helper.scaleFont(Helper.standardFont, Helper.standardFontSize),
        sectionFontsize=Helper.scaleFont(Helper.standardFontBold, Helper.standardFontSize - 1),
        textHeight=Helper.scaleY(Helper.standardTextHeight), 
        gap=Helper.scaleY(6), blockGap=Helper.scaleY(8)}
    -- Two text lines, measured like vanilla's double property rows.
    local ok, measured = pcall(function() return C.GetTextHeight(' \n ', Helper.standardFont, data.fontsize, 0) end)
    data.itemHeight = math.max(2 * data.textHeight, ok and tonumber(measured) and math.ceil(measured) or 0)
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
        if expanded[key] then drawExpanded(t, data, key, s) end
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
