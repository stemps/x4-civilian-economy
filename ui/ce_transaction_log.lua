-- Optional VTL 1.14 adapter. Native ledger IDs avoid its exact-time queue matcher.
-- ego_detailmonitorhelper declares TransactionLogEntry and its native functions.
local ffi = require('ffi')
local C = ffi.C
local requestKey = '$ce_vtl_deliveries'
local vtlKey = '$verboseTransactionLog'
local details

local function enabled()
    for _, extension in ipairs(GetExtensionList()) do
        if extension.id == 'VerboseTransactionLog' then
            return extension.enabled and not extension.error
        end
    end
    return false
end

local function receipt(player, request)
    local seller, credits, completed, paid = unpack(request)
    if not seller or type(credits) ~= 'number' or credits <= 0
        or type(completed) ~= 'number' or type(paid) ~= 'number'
        or paid < completed or paid - completed > 30
        or type(request[5]) ~= 'string' then
        return nil
    end
    -- Blackboard components are Lua IDs, not native UniverseID values.
    seller = ConvertIDTo64Bit(seller)
    -- Read the ledger's timestamp and ID; never round or offset the MD timestamp.
    local count = C.GetNumTransactionLog(player, completed, paid)
    if count == 0 or count > 10000 then return nil end
    local rows = ffi.new('TransactionLogEntry[?]', count)
    count = C.GetTransactionLog(rows, count, player, completed, paid)
    local found
    for i = 0, count - 1 do
        local row = rows[i]
        if ffi.string(row.eventtype) == 'orderqueue_remove'
            and row.partnerid == seller and tonumber(row.money) == math.floor(credits * 100 + 0.5)
            and row.time >= completed and row.time <= paid then
            if found then return nil end
            found = ConvertStringTo64Bit(tostring(row.entryid))
        end
    end
    return found
end

local function addWareDetail(entry)
    if entry.eventtype ~= 'orderqueue_remove' or entry.warename ~= '' then return entry end
    if details == nil then
        details = {}
        if enabled() then
            local player = ConvertStringToLuaID(tostring(C.GetPlayerID()))
            local data = GetNPCBlackboard(player, vtlKey)
            if type(data) == 'table' and type(data.lookupTable) == 'table' then
                details = data.lookupTable
            end
        end
    end
    local stored = details[entry.entryid]
    if type(stored) == 'table' and type(stored.ceWare) == 'string' then
        entry.warename = GetWareData(stored.ceWare, 'name') or ''
    end
    -- Leave entry.ware empty: a receipt has no expandable trade breakdown.
    return entry
end

local function onDelivery()
    local nativePlayer = C.GetPlayerID()
    local player = ConvertStringToLuaID(tostring(nativePlayer))
    local requests = GetNPCBlackboard(player, requestKey)
    if type(requests) ~= 'table' then return end
    SetNPCBlackboard(player, requestKey, nil)
    if not enabled() then return end
    local data = GetNPCBlackboard(player, vtlKey)
    -- Fail closed if the installed VTL changes its saved-data contract.
    if type(data) ~= 'table' or type(data.queue) ~= 'table'
        or type(data.lookupTable) ~= 'table' then return end
    local changed = false
    for _, request in ipairs(requests) do
        local ok, id = pcall(receipt, nativePlayer, request)
        if ok and id then
            local description = ReadText(974201, 156):gsub('%%1', function() return request[5] end)
            -- A different mod's description is not ours to replace.
            if data.lookupTable[id] == nil then
                data.lookupTable[id] = {description = description}
                if type(request[6]) == 'string' and request[6] ~= '' then
                    data.lookupTable[id].ceWare = request[6]
                end
                changed = true
            end
        end
    end
    if changed then
        SetNPCBlackboard(player, vtlKey, data)
        -- VTL's installed boot listener synchronously reloads its private cache.
        -- No transfer_money event: there is no stale time-based queue to mislabel
        -- another payment, and this adapter never changes any account balance.
        CallEventScripts('mvtl.onGameLoad')
    end
end

RegisterEvent('CEVTLDelivery', onDelivery)
RegisterEvent('mvtl.onGameLoad', function() details = nil end)
if Helper.registerCallback then
    Helper.registerCallback('createTransactionLog_on_before_adding_entry', addWareDetail, 'CEWareDetail')
end
