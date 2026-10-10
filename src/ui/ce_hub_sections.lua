-- Shared hub drawing for the map sidebar list and the selected-hub panel: a two-line
-- hub row and titled Overview / Demand events / Supplies / Bonuses sections. Callers
-- own their table, placement and lifecycle; this module only fills rows.
CEHubSections = {}
local S, M, R = CEHubSections, CEHubStatus, CERewardStatus
local C = require('ffi').C

-- [bar anchor] [button] [label] [flex] [time] [right] [right]
S.COLUMNS = 7
local COLUMNS = S.COLUMNS
local green = {r=18,g=85,b=43,a=100,glow=0}
local blue = {r=12,g=85,b=140,a=100,glow=0}
local sectionColor = {r=120,g=180,b=230,a=100,glow=0}
-- Content areas share one background; section headings use vanilla's title blue.
local content = function() return Color['rowgroup_background_default'] end
local heading = function() return Color['row_title_background'] end

local frameTime, frameCache = nil, {}
-- Cells read live values every frame; decode each snapshot at most once per frame.
function S.hub(key)
    local now = getElapsedTime()
    if frameTime ~= now then frameTime, frameCache = now, {} end
    if frameCache[key] == nil then frameCache[key] = M.get(key) or false end
    return frameCache[key] or nil
end
function S.name(id)
    return GetComponentData(id, 'name') or M.text(55)
end

-- Scaled sizes for one draw. buttonWidth is the second column (1 without a button).
function S.metrics(withButton)
    local data = {fontsize=Helper.scaleFont(Helper.standardFont, Helper.standardFontSize),
        sectionFontsize=Helper.scaleFont(Helper.standardFontBold, Helper.standardFontSize - 1),
        textHeight=Helper.scaleY(Helper.standardTextHeight), gap=Helper.scaleY(6), blockGap=Helper.scaleY(8)}
    -- Two text lines, measured like vanilla's double property rows.
    local ok, measured = pcall(function() return C.GetTextHeight(' \n ', Helper.standardFont, data.fontsize, 0) end)
    data.itemHeight = math.max(2 * data.textHeight, ok and tonumber(measured) and math.ceil(measured) or 0)
    data.buttonWidth = withButton and data.textHeight or 1
    return data
end

-- Column widths and default cell properties for a table of COLUMNS columns.
function S.configure(t, data, width, labelShare)
    -- The 1px first column anchors every status bar; bars are shifted past the
    -- button column, so content cells start right after it.
    t:setColWidth(1, 1)
    t:setColWidth(2, data.buttonWidth)
    t:setColWidth(3, math.floor(width * labelShare))
    t:setColWidth(5, math.floor(width * 0.14))
    t:setColWidth(6, math.floor(width * 0.16))
    t:setColWidth(7, math.floor(width * 0.14))
    t:setDefaultCellProperties('text', {fontsize=data.fontsize, minRowHeight=data.textHeight})
    t:setDefaultComplexCellProperties('button', 'text', {fontsize=data.fontsize})
    t:setDefaultComplexCellProperties('icon', 'text', {fontsize=data.fontsize})
    t:setDefaultComplexCellProperties('icon', 'text2', {fontsize=data.fontsize})
end

-- Scrolling rows stay selectable (but inert) so native scrolling keeps working.
local function plainRow(t, properties)
    properties = properties or {}
    properties.interactive, properties.borderBelow = false, false
    return t:addRow(true, properties)
end
-- Bars sit in column 1 and start after the button column.
local function barOffset(r)
    return r[1]:getWidth() + r[2]:getWidth() + 2 * Helper.borderSize
end
-- One background without gaps needs both parts (widget_fullscreen.lua): every cell
-- paints its OWN color, so the row bgColor gives all cells the same one (vanilla
-- addRow copies it into each cell); and a cell background only widens over the 2px
-- gap to the next cell when that cell is inside a background colspan.
local function spanBackground(r, first)
    r[first]:setBackgroundColSpan(COLUMNS - first + 1)
end
-- A content row: the leading columns stay clear, columns 3-7 share one background.
local function blockRow(t, background)
    local r = plainRow(t, {bgColor=background or content()})
    r[1].properties.cellBGColor = Color['row_background']
    r[2].properties.cellBGColor = Color['row_background']
    spanBackground(r, 3)
    return r
end
-- Empty spacing row, like vanilla table:addEmptyRow but selectable for scrolling.
-- Gaps stay transparent, so sections read as separate cards.
function S.gap(t, height)
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

-- One two-line hub row, like vanilla's double property rows: the station icon and
-- name, then the greyed progress line over the growth bar, and the compact supply
-- status on the right. opts: rowdata, fixed, button={text, onClick}. The text icon
-- spans the last column, so the table must reserve the scrollbar (see KNOWLEDGEBASE).
function S.drawItem(t, data, s, opts)
    local key, id = tostring(s.id), s.id
    local function current() return S.hub(key) end
    -- Vanilla property rows give stations row_background_blue (getContainerNameAndColors).
    local head = t:addRow(opts.rowdata, {fixed=opts.fixed, bgColor=Color['row_background_blue']})
    spanBackground(head, 1)
    if opts.button then
        head[2]:createButton({height=data.itemHeight}):setText(opts.button.text, {halign='center'})
        head[2].handlers.onClick = function() return opts.button.onClick(head) end
    end
    local barWidth = head[3]:getWidth() + head[4]:getWidth() + head[5]:getWidth() + 2 * Helper.borderSize
    local function percent() return M.progressPercent(current()) end
    head[1]:createStatusBar({current=percent, start=percent, max=100, valueColor=green,
        markerColor=Color['statusbar_marker_hidden'], width=barWidth, height=data.textHeight,
        x=barOffset(head), y=data.itemHeight-data.textHeight, scaling=false})
    local item = head[3]:setColSpan(COLUMNS - 2):createIcon('solid',
        {color=Color['icon_transparent'], height=data.itemHeight})
    local offset = Helper.scaleX(Helper.standardTextOffsetx)
    local fullName = S.name(id)
    -- The station's own map icon before its name, as in vanilla property rows.
    local iconID = GetComponentData(id, 'icon')
    local label = (iconID and iconID ~= '' and '\27[' .. iconID .. '] ' or '') .. fullName
    local shown = TruncateText(label, Helper.standardFont, data.fontsize, item:getColSpanWidth() - 2 * offset)
    local function hint()
        local now = current()
        local prefix = shown ~= label and fullName .. '\n\n' or ''
        return prefix .. M.supplyText(now) .. '\n\n' .. M.progressHint(now)
    end
    item.properties.mouseOverText = hint
    -- The progress line is greyed so the name stays the focus.
    local lowlight = Helper.convertColorToText(Color['text_lowlight'])
    item:setText(function() return shown .. '\n' .. lowlight .. M.progressShort(current()) .. '\27X' end,
        {halign='left', x=offset, color=Color['text_normal']})
    -- Vanilla only uses function-valued TEXT on icon sub-texts; color via an inline escape.
    item:setText2(function()
        local now = current()
        return '\n' .. Helper.convertColorToText(Color[M.supplyColor(now)]) .. M.supplyCompact(now) .. '\27X'
    end, {halign='right', x=offset})
    return head
end

-- One-line growth row for panels with their own title: the progress label over the
-- growth bar and the compact supply status as a text cell in the last column.
function S.drawProgress(t, data, s, opts)
    local key = tostring(s.id)
    local function current() return S.hub(key) end
    local function hint()
        local now = current()
        return M.supplyText(now) .. '\n\n' .. M.progressHint(now)
    end
    local r = t:addRow(nil, {fixed=opts.fixed, borderBelow=false})
    local barWidth = r[3]:getWidth() + r[4]:getWidth() + r[5]:getWidth() + 2 * Helper.borderSize
    local function percent() return M.progressPercent(current()) end
    r[1]:createStatusBar({current=percent, start=percent, max=100, valueColor=green,
        markerColor=Color['statusbar_marker_hidden'], width=barWidth, height=data.textHeight,
        x=barOffset(r), scaling=false})
    r[3]:setColSpan(3):createText(function() return M.progressShort(current()) end,
        {mouseOverText=hint, color=Color['text_normal']})
    r[6]:setColSpan(2):createText(function() return M.supplyCompact(current()) end, {halign='right',
        mouseOverText=hint, color=function() return Color[M.supplyColor(current())] end})
    return r
end

local function drawOverview(t, data, key, s)
    local function current() return S.hub(key) end
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
    local function current() return S.hub(key) end
    S.gap(t, data.gap)
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

-- order: ware keys in display order (defaults to M.order). incoming: own column.
local function drawWares(t, data, key, s, order, incoming)
    local function current() return S.hub(key) end
    S.gap(t, data.gap)
    local title = section(t, data, M.text(402), 3)
    if incoming then
        title[6]:createText(M.text(91), {halign='right'})
        title[7]:createText(M.text(112), {halign='right'})
    else
        title[6]:setColSpan(2):createText(M.text(91), {halign='right'})
    end
    if #s.wares == 0 then
        blockRow(t)[3]:setColSpan(COLUMNS - 2):createText(s.available and M.text(71) or M.text(68),
            {wordwrap=true})
        return
    end
    for _, wareKey in ipairs(order or M.order(s)) do
        local function ware() return M.find(current(), wareKey) end
        local function hint()
            local w = ware()
            return w and M.wareState(w) .. '\n' .. M.wareHint(current(), w) or M.text(68)
        end
        local w = ware()
        local r = blockRow(t)
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
            {halign='right', mouseOverText=hint, color=Color[w and M.wareColor(w) or 'text_normal']})
        local function column(index)
            return function() local now = ware(); return now and M.columns(current(), now)[index] or M.text(69) end
        end
        if incoming then
            r[6]:createText(column(4), {halign='right', mouseOverText=hint})
            r[7]:createText(column(5), {halign='right', mouseOverText=hint, color=Color['text_lowlight']})
        else
            r[6]:setColSpan(2):createText(column(4), {halign='right', mouseOverText=hint})
        end
    end
end

local function drawBonuses(t, data, key, s)
    local function current() return S.hub(key) end
    S.gap(t, data.gap)
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
        elseif entry.color == 'text_inactive' then
            -- No usable bonus data: one grey line, the reason is in the tooltip.
            r[3]:setColSpan(COLUMNS - 2):createText(function() return now().name end,
                {mouseOverText=hint, color=Color['text_inactive']})
        else
            -- Unlocked: the name, with its benefit indented on a second line.
            r[3]:setColSpan(COLUMNS - 2):createText(function()
                local e = now()
                return e.name .. '\n' .. lowlight .. '   ' .. e.value .. '\27X'
            end, {mouseOverText=function() return now().hint end, wordwrap=true})
        end
    end
end

-- All detail sections of one hub. opts: wareOrder, incoming.
function S.drawDetails(t, data, s, opts)
    opts = opts or {}
    local key = tostring(s.id)
    S.gap(t, data.gap)
    drawOverview(t, data, key, s)
    drawEvents(t, data, key, s)
    drawWares(t, data, key, s, opts.wareOrder, opts.incoming)
    drawBonuses(t, data, key, s)
end
