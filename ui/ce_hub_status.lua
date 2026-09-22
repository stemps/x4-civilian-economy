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
    result.pauseReason = s[12]
    result.profileError, result.stale = yes(s[14]), yes(s[15])
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
    facts.pending, facts.maximum = s.target > 0, s.level == 10
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
function M.state(s)
    local facts = M.classify(s)
    if not facts.available then return M.text(68) end
    if facts.warning then return M.text(facts.warning == 'stale' and 88 or 89) end
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
end
function M.progress(s)
    local facts = M.classify(s)
    if not facts.available then return M.text(68) end
    if facts.pending then return M.text(105) end
    if facts.maximum then return M.text(100) end
    return M.text(106,s.level+1,M.time(s.growth),M.time(s.required))
end
function M.action(s)
    local facts = M.classify(s)
    if not facts.available then return M.text(68) end
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
    if not s or not s.available or s.level==10 then return '' end
    return #s.unlocks>0 and M.text(109,table.concat(s.unlocks,', ')) or M.text(110)
end
function M.wareHint(s,w)
    return M.text(111,w.name,M.amount(w.reserve),M.amount(w.rate),M.amount(w.capacity),w.buying,w.incoming)
end
function M.signature(s)
    if not s then return '' end
    local parts = {tostring(s.id), s.available and 'ready' or 'missing', tostring(s.level), tostring(s.target), tostring(s.stale), tostring(s.profileError), tostring(s.pausedOffers)}
    for _, w in ipairs(s.wares) do parts[#parts + 1] = w.key .. ':' .. M.wareCode(w) end
    return table.concat(parts, '\n')
end
