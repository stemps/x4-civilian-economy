-- Live population adapter. MD owns discovery, reconciliation and demand.
local ffi = require('ffi')
ffi.cdef[[
    uint64_t GetPlayerID(void);
    uint64_t GetSectorPopulation(uint64_t sectorid);
    bool IsValidComponent(uint64_t componentid);
]]
local C = ffi.C
local function onRequest()
    local player = ConvertStringTo64Bit(tostring(C.GetPlayerID()))
    local request = GetNPCBlackboard(player, '$ce_population_request')
    if type(request) ~= 'table' or type(request[2]) ~= 'table' then return end
    local rows = {}
    for _, sector in ipairs(request[2]) do
        local ok, population = pcall(function()
            local id = ConvertStringTo64Bit(tostring(sector))
            if not C.IsValidComponent(id) then return nil end
            return tonumber(C.GetSectorPopulation(id))
        end)
        -- Failed reads are omitted, never interpreted as a depopulated sector.
        if ok and population and population >= 0 and population < math.huge then
            rows[#rows + 1] = {sector, population}
        else
            DebugError('[CE] Population unavailable for sector ' .. tostring(sector))
        end
    end
    SetNPCBlackboard(player, '$ce_population_response', {request[1], rows})
    AddUITriggeredEvent('CEPopulation', 'ready')
end
RegisterEvent('CEPopulationRequest', onRequest)
