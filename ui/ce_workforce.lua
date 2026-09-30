-- Read native workforce limits. MD alone grants immigrants and owns saved fractions.
local ffi = require('ffi')
-- WorkforceInfluenceInfo and its subordinate structs are declared by vanilla menus.
ffi.cdef[[
    void GetContainerWorkforceInfluence(WorkforceInfluenceInfo* result, uint64_t containerid, const char* raceid);
    WorkforceInfluenceCounts GetNumContainerWorkforceInfluence(uint64_t containerid, const char* raceid, bool force);
    bool ShouldContainerFillWorkforceCapacity(uint64_t containerid);
]]
local C = ffi.C
local function finite(n) return type(n)=='number' and n==n and n > -math.huge and n < math.huge end
local function read(station, race)
    local counts = C.GetNumContainerWorkforceInfluence(station, race[2], true)
    local capacity, growth = tonumber(counts.numcapacityinfluences), tonumber(counts.numgrowthinfluences)
    if not finite(capacity) or not finite(growth) or capacity<0 or growth<0 or capacity>4096 or growth>4096 then return end
    local buf = ffi.new('WorkforceInfluenceInfo')
    local caps = ffi.new('UIWorkforceInfluence[?]', math.max(1,capacity))
    local grows = ffi.new('UIWorkforceInfluence[?]', math.max(1,growth))
    buf.capacityinfluences, buf.numcapacityinfluences = caps, capacity
    buf.growthinfluences, buf.numgrowthinfluences = grows, growth
    C.GetContainerWorkforceInfluence(buf, station, race[2])
    local target = C.ShouldContainerFillWorkforceCapacity(station) and tonumber(buf.capacity) or tonumber(buf.target)
    local row = {race[1],tonumber(buf.capacity),tonumber(buf.sustainable),target,tonumber(buf.change)}
    for i=2,5 do if not finite(row[i]) or (i<5 and row[i]<0) then return end end
    return row
end
local function onRequest()
    local player = ConvertStringTo64Bit(tostring(C.GetPlayerID()))
    local request = GetNPCBlackboard(player, '$ce_workforce_request')
    if type(request)~='table' or type(request[2])~='table' then return end
    local rows = {}
    for _,entry in ipairs(request[2]) do
        local ok, stationRows = pcall(function()
            local station = ConvertStringTo64Bit(tostring(entry[1]))
            if not C.IsValidComponent(station) then return end
            local result = {}
            for _,race in ipairs(entry[2]) do
                local success,row = pcall(read,station,race)
                if success and row then result[#result+1]=row end
            end
            return {entry[1],result}
        end)
        if ok and stationRows then rows[#rows+1]=stationRows end
    end
    SetNPCBlackboard(player, '$ce_workforce_response', {request[1],rows})
    AddUITriggeredEvent('CEWorkforce', 'ready')
end
RegisterEvent('CEWorkforceRequest', onRequest)
