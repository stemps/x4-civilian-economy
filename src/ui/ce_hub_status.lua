-- Read-only presentation of the MD snapshots. No economic calculations live here.
CEHubStatus = {}
local M = CEHubStatus
local ffi = require('ffi')
ffi.cdef[[
    uint64_t GetPlayerID(void);
    bool IsValidComponent(uint64_t componentid);
    bool IsObjectKnown(uint64_t componentid);
]]
local C = ffi.C
local expires, hubs, snapshots, lastValid = nil, {}, {}, {}
local function yes(value) return value == true or value == 1 end
local function number(value)
    local n = tonumber(value)
    if n and n == n and n >= 0 and n < math.huge then return n end
end
function M.text(id, ...)
    local value = ReadText(974201, id)
    return select('#', ...) == 0 and value or string.format(value, ...)
end
function M.id(value)
    if value == nil then return nil end
    local ok, id = pcall(ConvertStringTo64Bit, tostring(value))
    if ok and id and id ~= 0 then return id end
end
function M.reset()
    expires, hubs, snapshots, lastValid = nil, {}, {}, {}
end
-- Publication notifications bypass the read throttle without losing fallback rows.
RegisterEvent('CEHubStatusUpdated', function() expires = nil end)
function M.validSnapshot(s)
    if type(s) ~= 'table' or type(s[9]) ~= 'table' then return false end
    if tonumber(s[13]) ~= 3 then return false end
    if not number(s[2]) or not number(s[3]) or not number(s[5]) or not number(s[6]) or number(s[6]) <= 0 then return false end
    local seen = {}
    for _, w in ipairs(s[9]) do
        if type(w) ~= 'table' or type(w[1]) ~= 'string' or type(w[10]) ~= 'string' or seen[w[10]] then return false end
        seen[w[10]] = true
        for _, index in ipairs({2,3,4,5,6,7,8,9}) do
            if not number(w[index]) then return false end
        end
    end
    return true
end
local function copy(value)
    if type(value) ~= 'table' then return value end
    local result = {}
    for key, item in pairs(value) do result[key] = copy(item) end
    return result
end
local function read(key)
    return GetNPCBlackboard(ConvertStringToLuaID(tostring(C.GetPlayerID())), key)
end
local function membership(list)
    local result = {}
    for _, raw in ipairs(type(list) == 'table' and list or {}) do
        local id = M.id(raw)
        if id then result[tostring(id)] = true end
    end
    return result
end
-- Testing commands must recheck live membership; do not consult the display cache.
function M.canCreateInSector(raw)
    local id = M.id(raw)
    if not id or not C.IsValidComponent(id) then return false end
    local occupied = read('$ce_hub_sectors')
    return type(occupied) == 'table' and not membership(occupied)[tostring(id)]
end
function M.isHub(raw)
    local id = M.id(raw)
    return id and C.IsValidComponent(id) and membership(read('$ce_hubs'))[tostring(id)] == true
end
local function refresh()
    local now = getElapsedTime()
    if expires and now < expires and now >= expires - 1 then return end
    expires, hubs, snapshots = now + 1, {}, {}
    local statuses = read('$ce_hub_statuses')
    hubs = membership(read('$ce_hubs'))
    for _, s in ipairs(type(statuses) == 'table' and statuses or {}) do
        local id = type(s) == 'table' and M.id(s[1])
        if id then
            local key = tostring(id)
            if M.validSnapshot(s) then
                snapshots[key], lastValid[key] = s, copy(s)
            elseif tonumber(s[13]) == 3 and lastValid[key] then
                local retained = {}
                for index, value in pairs(lastValid[key]) do retained[index] = value end
                retained[15] = true
                retained[19] = false
                snapshots[key] = retained
            end
        end
    end
    for key in pairs(lastValid) do if not hubs[key] then lastValid[key] = nil end end
end
-- One positional wire-format decoder for every UI consumer.
local function decode(id, s)
    local result = {id=id, wares={}, available=s ~= nil}
    if not s then return result end
    result.level, result.population = number(s[2]), number(s[11])
    result.active, result.pausedOffers = yes(s[4]), yes(s[7])
    result.testUpgrade = yes(s[10])
    result.populationOverride, result.debugFallback = number(s[17]), yes(s[18])
    result.debugInitial = yes(s[19]) and not yes(s[15])
    result.layoutPhase = s[22]
    -- Designated (external) hubs: [1, maximum level]. CE never builds on them.
    result.external = type(s[24]) == 'table' and number(s[24][1]) == 1
    result.maxLevel = result.external and number(s[24][2]) or 10
    if type(s[21]) == 'table' and s[21][1] == 2 and type(s[21][2]) == 'table' then
        local payload, events, seen = s[21], {}, {}
        local rows = payload[2]
        local eligible, token = payload[3], number(payload[4])
        local valid = type(eligible) == 'table' and token and token == math.floor(token)
        for _, e in ipairs(rows) do
            if type(e) ~= 'table' then valid = false; break end
            local eventID, percent, remaining = number(e[1]), tonumber(e[2]), number(e[3])
            if not eventID or eventID < 1 or eventID > 11 or eventID ~= math.floor(eventID) or seen[eventID]
                or not percent or percent < -50 or percent > 100 or percent ~= math.floor(percent)
                or not remaining or type(e[4]) ~= 'string' then valid = false; break end
            seen[eventID] = true
            events[#events+1] = {id=eventID, percent=percent, remaining=remaining, names=e[4]}
        end
        if valid then
            table.sort(events, function(a,b) return a.id < b.id end)
            result.demandEvents = {events=events, eligible=eligible, token=token, version=2}
        end
    end
    if type(s[20]) == 'table' then
        local u = s[20]
        result.unrest = {score=number(u[1]) or 0, stage=number(u[2]) or 0,
            direction=(tonumber(u[3]) == -1 and -1 or (tonumber(u[3]) == 1 and 1 or 0)), critical=number(u[4]) or -1,
            causes=type(u[5]) == 'table' and u[5] or {}, token=number(u[6])}
    end
    result.pauseReason = s[12]
    result.profileError, result.stale = yes(s[14]), yes(s[15])
    result.rewards = type(s[23]) == 'table' and s[23] or nil
    result.growth, result.required = number(s[5]), number(s[6])
    result.target, result.plotReady, result.unlocks = number(s[3]), yes(s[8]), type(s[16]) == 'table' and s[16] or {}
    for _, w in ipairs(type(s[9]) == 'table' and s[9] or {}) do
        if type(w) == 'table' and type(w[1]) == 'string' then
            result.wares[#result.wares + 1] = {
                name=w[1], reserve=number(w[2]), capacity=number(w[3]),
                buying=number(w[4]), incoming=number(w[5]), delivered=number(w[6]), paid=number(w[7]),
                remaining=number(w[8]), rate=number(w[9]), key=w[10],
            }
        end
    end
    return result
end
function M.get(raw)
    local id = M.id(raw)
    if not id or not C.IsValidComponent(id) or not C.IsObjectKnown(id) then return end
    refresh()
    if not hubs[tostring(id)] then return end
    return decode(id, snapshots[tostring(id)])
end
-- Fresh reads deliberately neither consume nor update retained display snapshots.
-- Knowledge filtering remains a map concern; command membership matches the native menu.
function M.getFresh(raw)
    local id = M.id(raw)
    if not M.isHub(id) then return end
    local statuses = read('$ce_hub_statuses')
    for _, s in ipairs(type(statuses) == 'table' and statuses or {}) do
        if M.validSnapshot(s) and M.id(s[1]) == id then return decode(id, s) end
    end
end
function M.amount(value)
    return value and string.format('%.1f', value) or M.text(69)
end
function M.time(seconds, roundUp)
    if not seconds then return M.text(69) end
    local minutes = roundUp and math.ceil(seconds / 60) or math.floor(seconds / 60)
    return minutes >= 60 and M.text(93, math.floor(minutes/60), minutes%60) or M.text(92, minutes)
end
local wareStates = {
    paused = {label=57, rank=3, color='text_normal'},
    needed = {label=94, rank=0, color='text_negative'},
    low = {label=95, rank=1, color='text_warning'},
    supplied = {label=96, rank=2, color='text_normal'},
    full = {label=97, rank=2, color='text_normal'},
}
function M.wareCode(w)
    if not w or w.rate == 0 then return 'paused' end
    if w.reserve == 0 then return 'needed' end
    if w.remaining < 900 then return 'low' end
    return w.reserve >= w.capacity and 'full' or 'supplied'
end
function M.wareColor(w)
    return wareStates[M.wareCode(w)].color
end
function M.wareState(w)
    return M.text(wareStates[M.wareCode(w)].label)
end
function M.remaining(w)
    if w.rate == 0 then return M.text(69) end
    return w.reserve == 0 and M.text(98) or M.time(w.remaining, true)
end
function M.columns(s,w)
    return {w.name,M.remaining(w),M.wareState(w),ConvertIntegerString(w.buying, true, 2, true),
        w.incoming > 0 and string.format('%.0f',w.incoming) or '-'}
end
function M.order(s)
    local rows = {}
    for _,w in ipairs(s.wares) do rows[#rows+1]=w end
    local function rank(w)
        return wareStates[M.wareCode(w)].rank
    end
    table.sort(rows,function(a,b)
        if rank(a) ~= rank(b) then return rank(a)<rank(b) end
        if a.remaining ~= b.remaining then return a.remaining<b.remaining end
        return a.key<b.key
    end)
    local order={};for _,w in ipairs(rows) do order[#order+1]=w.key end
    return order
end
function M.find(s,key)
    if s then for _,w in ipairs(s.wares) do if w.key==key then return w end end end
end
function M.missing(s)
    local names={}
    for _,w in ipairs(s.wares) do if M.wareCode(w)=='needed' then names[#names+1]=w.name end end
    return names
end
-- Shared facts, independent of localization. Each view retains its own message priority.
function M.classify(s)
    local facts = {available=not not (s and s.available), missing={}, required=false}
    if not facts.available then return facts end
    facts.pending, facts.maximum = s.target > 0, s.level >= (s.maxLevel or 10)
    facts.ready = s.growth >= s.required
    facts.warning = s.stale and 'stale' or s.profileError and 'profile_error' or nil
    for _, w in ipairs(s.wares) do
        local code = M.wareCode(w)
        if code ~= 'paused' then facts.required = true end
        if code == 'needed' then facts.missing[#facts.missing+1] = w.name end
    end
    facts.growing = s.active and not s.stale and not facts.ready
        and #facts.missing == 0 and facts.required
    return facts
end
function M.population(value)
    if not value then return M.text(69) end
    if value >= 1e12 then return M.text(75, value / 1e12) end
    if value >= 1e9 then return M.text(74, value / 1e9) end
    if value >= 1e6 then return M.text(73, value / 1e6) end
    return string.format('%.0f', value)
end
function M.unrest(s)
    local u = s and s.unrest
    if not u then return '' end
    local direction = u.direction > 0 and 254 or (u.direction < 0 and 255 or 256)
    local value = M.text(251, u.score, M.text(260 + u.stage), M.text(direction))
    if #u.causes > 0 then value = value .. '\n' .. M.text(252, table.concat(u.causes, ', ')) end
    if u.critical >= 0 then value = value .. '\n' .. M.text(253, math.ceil(u.critical / 60)) end
    return value
end
function M.layoutState(s)
    local labels = {planning=345, layout_retry=346, build_retry=347}
    local label = s and labels[s.layoutPhase]
    return label and M.text(label) or nil
end
function M.state(s)
    local facts = M.classify(s)
    if not facts.available then return M.text(68) end
    if facts.warning then return M.text(facts.warning == 'stale' and 88 or 89) end
    if M.layoutState(s) then return M.layoutState(s) end
    if s.active then
        if facts.pending then return M.text(99,s.target) end
        if facts.maximum then return M.text(100) end
        if facts.ready then return M.text(s.plotReady and 101 or 102) end
        if #facts.missing>0 then return M.text(103,table.concat(facts.missing,', ')) end
        if facts.required then return M.text(104) end
        return M.text(71)
    end
    local reasons = {constructing=82, damaged_modules=83, no_population=84,
        owner_changed=85, hub_unavailable=86, modules_unavailable=87}
    return M.text(reasons[s.pauseReason] or 57)
end
function M.tooltip(s)
    local level = s.level and string.format('%.0f', s.level) or M.text(69)
    return M.text(77) .. ': ' .. level .. '\n' .. M.text(76) .. ': ' .. M.population(s.population)
        .. (s.unrest and ('\n' .. M.unrest(s)) or '')
end
function M.progressHint(s)
    local facts = M.classify(s)
    if not facts.available then return M.text(68) end
    if facts.warning then return M.text(facts.warning == 'stale' and 88 or 89) end
    if facts.maximum then return M.text(100) end
    local layout = M.layoutState(s)
    if facts.pending or layout or s.pauseReason == 'constructing' then
        local target = facts.pending and s.target or s.level
        return M.text(99, target) .. '\n\n' .. (layout or M.text(372))
    end
    local heading = M.text(115, s.level + 1)
    if facts.ready then return heading .. '\n\n' .. M.state(s) end
    local status = M.state(s)
    if s.active and #facts.missing > 0 then
        status = M.text(371) .. '\n- ' .. table.concat(facts.missing, '\n- ')
    elseif facts.growing then
        status = M.text(370)
    end
    return heading .. '\n' .. M.text(369, M.time(s.growth), M.time(s.required)) .. '\n\n' .. status
end
function M.progress(s)
    local facts = M.classify(s)
    if not facts.available then return M.text(68) end
    if M.layoutState(s) then return M.layoutState(s) end
    if facts.pending then return M.text(105) end
    if facts.maximum then return M.text(100) end
    return M.text(106,s.level+1,M.time(s.growth),M.time(s.required))
end
function M.action(s)
    local facts = M.classify(s)
    if not facts.available then return M.text(68) end
    if M.layoutState(s) then return M.layoutState(s) end
    if facts.pending then return M.text(105) end
    if not s.active then return M.state(s) end
    if facts.maximum then return M.text(114) end
    if #facts.missing>0 then return M.text(107,table.concat(facts.missing,', ')) end
    return M.text(108)
end
function M.levelLabel(s)
    local facts = M.classify(s)
    if not facts.available then return M.text(68) end
    local state=118
    if facts.maximum then state=120
    elseif facts.pending then state=119
    elseif facts.growing then state=117 end
    return M.text(121,s.level,M.text(state))
end
function M.nextLevel(s)
    if not s or not s.available or s.level >= (s.maxLevel or 10) then return '' end
    return #s.unlocks>0 and M.text(109,table.concat(s.unlocks,', ')) or M.text(110)
end
function M.wareHint(s,w)
    return M.text(111,w.name,M.amount(w.reserve),M.amount(w.rate),M.amount(w.capacity),w.buying,w.incoming)
end
function M.signature(s)
    if not s then return '' end
    local parts = {tostring(s.id), s.available and 'ready' or 'missing', tostring(s.level), tostring(s.target), tostring(s.stale), tostring(s.profileError), tostring(s.pausedOffers)}
    parts[#parts + 1] = tostring(s.layoutPhase)
    if s.unrest then parts[#parts + 1] = tostring(s.unrest.stage) .. ':' .. table.concat(s.unrest.causes, ',') end
    parts[#parts + 1] = M.eventSignature(s)
    for _, w in ipairs(s.wares) do parts[#parts + 1] = w.key .. ':' .. M.wareCode(w) end
    return table.concat(parts, '\n')
end

function M.eventSignature(s)
    local ids = {}
    for _, e in ipairs(s and s.demandEvents and s.demandEvents.events or {}) do ids[#ids+1] = tostring(e.id) end
    return table.concat(ids, ',')
end
function M.event(s, eventID)
    for _, e in ipairs(s and s.demandEvents and s.demandEvents.events or {}) do
        if not eventID or e.id == eventID then return e end
    end
end
function M.eventText(s, eventID)
    local e = M.event(s, eventID)
    if not e then return '' end
    return M.text(336, M.text(320 + e.id), string.format('%+d', e.percent), M.time(e.remaining, true))
end
function M.eventHint(s, eventID)
    local e = M.event(s, eventID)
    return e and M.text(337, e.names) or ''
end
