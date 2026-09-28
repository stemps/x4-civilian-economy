-- Production seed completion. MD grants permission only to exact initial hubs.
local ffi = require('ffi')
ffi.cdef[[
    void ForceBuildCompletion(uint64_t containerid);
    float GetCurrentBuildProgress(uint64_t containerid);
    bool IsBuildWaitingForSecondaryComponentResources(uint64_t containerid);
]]
local C, M = ffi.C, CEHubStatus
RegisterEvent('CEInitialHubBuildReady', function(_, raw)
    local id = M.id(raw)
    if not id or not C.IsValidComponent(id) or GetComponentData(id, 'owner') ~= 'civilian' then return end
    local allowed = GetNPCBlackboard(ConvertStringToLuaID(tostring(C.GetPlayerID())), '$ce_initial_build_hubs')
    if type(allowed) ~= 'table' then return end
    for _, hub in ipairs(allowed) do
        if M.id(hub) == id then
            if C.GetCurrentBuildProgress(id) >= 0 or C.IsBuildWaitingForSecondaryComponentResources(id) then
                C.ForceBuildCompletion(id)
            end
            return
        end
    end
end)
