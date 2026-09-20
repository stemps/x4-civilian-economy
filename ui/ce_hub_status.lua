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
local expires, hubs, snapshots = nil, {}, {}
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
    expires, hubs, snapshots = nil, {}, {}
end
local function refresh()
    local now = getElapsedTime()
    if expires and now < expires and now >= expires - 1 then return end
    expires, hubs, snapshots = now + 1, {}, {}
    local player = ConvertStringToLuaID(tostring(C.GetPlayerID()))
    local function read(key) return GetNPCBlackboard(player, key) end
    if yes(read('$ce_legacy_blocked')) then return end
    local list, statuses = read('$ce_hubs'), read('$ce_hub_statuses')
    for _, raw in ipairs(type(list) == 'table' and list or {}) do
        local id = M.id(raw)
        if id then hubs[tostring(id)] = true end
    end
    for _, s in ipairs(type(statuses) == 'table' and statuses or {}) do
        local id = type(s) == 'table' and M.id(s[1])
        if id then snapshots[tostring(id)] = s end
    end
end
function M.get(raw)
    local id = M.id(raw)
    if not id or not C.IsValidComponent(id) or not C.IsObjectKnown(id) then return end
    refresh()
    if not hubs[tostring(id)] then return end
    local s = snapshots[tostring(id)]
    local result = {id=id, wares={}, available=s ~= nil}
    if not s then return result end
    result.level, result.population = number(s[2]), number(s[11])
    result.active, result.pausedOffers = yes(s[4]), yes(s[7])
    result.pauseReason = s[12]
    result.minutes, result.required = number(s[5]), number(s[6])
    for _, w in ipairs(type(s[9]) == 'table' and s[9] or {}) do
        if type(w) == 'table' and type(w[1]) == 'string' then
            result.wares[#result.wares + 1] = {
                name=w[1], demand=number(w[2]), cap=number(w[3]),
                fulfillment=number(w[8]), reliability=number(w[9]),
                shortage=number(w[10]), rate=number(w[11]),
            }
        end
    end
    return result
end
function M.amount(value)
    return value and string.format('%.1f', value) or M.text(69)
end
function M.percent(value, status)
    if not status.minutes or status.minutes == 0 or not value then return M.text(69) end
    return string.format('%.1f%%', value)
end
function M.columns(status, ware)
    return {ware.name, M.amount(ware.demand) .. ' / ' .. M.amount(ware.cap),
        M.percent(ware.fulfillment, status), M.percent(ware.reliability, status)}
end
function M.population(value)
    if not value then return M.text(69) end
    if value >= 1e12 then return M.text(75, value / 1e12) end
    if value >= 1e9 then return M.text(74, value / 1e9) end
    if value >= 1e6 then return M.text(73, value / 1e6) end
    return string.format('%.0f', value)
end
function M.state(s)
    if not s or not s.available then return M.text(68) end
    if s.active then return M.text(56) end
    local reasons = {constructing=82, damaged_modules=83, no_population=84,
        owner_changed=85, hub_unavailable=86, modules_unavailable=87}
    return M.text(reasons[s.pauseReason] or 57)
end
function M.tooltip(s)
    local level = s.level and string.format('%.0f', s.level) or M.text(69)
    return M.text(77) .. ': ' .. level .. '\n' .. M.text(76) .. ': ' .. M.population(s.population)
end
function M.history(s)
    if not s or not s.available or not s.minutes or not s.required then return M.text(68) end
    return M.text(58, s.minutes / 60, s.required / 60)
end
function M.historyState(s)
    if not s or not s.minutes or not s.required then return M.text(68) end
    return M.text(s.minutes < s.required and 59 or 79)
end
function M.score(s, w, field)
    if not s or not w or not s.minutes or s.minutes == 0 then return nil end
    return w[field]
end
function M.wareHint(s, w, field)
    if field == 'demand' then return M.text(80, M.amount(w.demand), M.amount(w.cap)) end
    if field == 'fulfillment' then return M.text(62) end
    if field == 'reliability' then return M.text(81, M.amount(w.shortage)) end
    return M.text(64, w.name, M.amount(w.rate))
end
function M.signature(s)
    if not s then return '' end
    local parts = {tostring(s.id), s.available and 'ready' or 'missing'}
    for _, w in ipairs(s.wares) do parts[#parts + 1] = w.name end
    return table.concat(parts, '\n')
end
