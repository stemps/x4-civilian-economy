-- Optional testing UI. MD owns all economic and construction state.
local ffi = require('ffi')
ffi.cdef[[
    void ForceBuildCompletion(uint64_t containerid);
    float GetCurrentBuildProgress(uint64_t containerid);
    bool IsBuildWaitingForSecondaryComponentResources(uint64_t containerid);
    bool IsValidComponent(uint64_t componentid);
    uint64_t GetPlayerID(void);
]]
local C = ffi.C
local section = 'actions_ce_debug'
local registered = false
local function read(key)
    return GetNPCBlackboard(ConvertStringToLuaID(tostring(C.GetPlayerID())), key)
end
local function yes(value) return value == true or value == 1 end
local function text(id, ...)
    local s = ReadText(974201, id)
    if select('#', ...) == 0 then return s end
    return string.format(s, ...)
end
local function isHub(id)
    if not id or id == 0 or not C.IsValidComponent(id) or yes(read('$ce_legacy_blocked')) then return false end
    for _, hub in ipairs(read('$ce_hubs') or {}) do
        if ConvertStringTo64Bit(tostring(hub)) == id then return true end
    end
    return false
end
local function statusFor(id)
    for _, s in ipairs(read('$ce_hub_statuses') or {}) do
        if CEHubStatus.validSnapshot(s) and s[1] and ConvertStringTo64Bit(tostring(s[1])) == id then return s end
    end
end
local function canFinish(id)
    return isHub(id) and (C.GetCurrentBuildProgress(id) >= 0 or C.IsBuildWaitingForSecondaryComponentResources(id))
end
local function canQueue(id)
    local s = statusFor(id)
    return isHub(id) and s and yes(s[4]) and (tonumber(s[2]) or 10) < 10 and tonumber(s[3]) == 0 and yes(s[8])
end
local function buildActions()
    local menu = Helper.getMenu('InteractMenu')
    local raw = menu and menu.componentSlot and menu.componentSlot.component
    if not raw then return end
    local id = ConvertStringTo64Bit(tostring(raw))
    if not isHub(id) then return end
    local function row(label, hint)
        menu.insertInteractionContent(section, {text=label, active=false, mouseOverText=hint or (label .. '\n' .. text(16))})
    end
    local s = statusFor(id)
    if s then
        if yes(s[15]) then row(text(88)) end
        if yes(s[14]) then row(text(89)) end
        row(text(32, tonumber(s[2]) or 1, tonumber(s[3]) or 0))
        row(text(yes(s[4]) and 34 or 35))
        if tonumber(s[3]) > 0 then row(text(99, s[3]), text(105))
        elseif tonumber(s[2]) == 10 then row(text(100))
        else row(text(113, s[5]/60, s[6]/60)) end
        if tonumber(s[11]) then row(text(44), text(45, tonumber(s[11]))) end
        if not yes(s[8]) then row(text(36), text(43)) end
        if yes(s[10]) then row(text(37)) end
        for _, w in ipairs(type(s[9]) == 'table' and s[9] or {}) do
            row(tostring(w[1]),text(111,tostring(w[1]),string.format('%.1f',w[2]),string.format('%.1f',w[9]),string.format('%.0f',w[3]),w[4],w[5]))
        end
    else
        row(text(68))
    end
    local function action(label, allowed, run)
        local used = false
        menu.insertInteractionContent(section, {text=label, active=not not allowed(), mouseOverText=label == text(11) and text(12) or label, script=function()
            if used or not allowed() then return end
            used = true
            run()
            menu.onCloseElement('close')
        end})
    end
    action(text(11), function() return canFinish(id) end, function()
        DebugError('[CE] TEST: force completion on ' .. tostring(id))
        C.ForceBuildCompletion(id)
    end)
    action(text(40), function() return canQueue(id) end, function()
        AddUITriggeredEvent('CELevelTesting', 'queue_upgrade', ConvertStringToLuaID(tostring(id)))
    end)
    action(text(s and yes(s[7]) and 42 or 41), function() return isHub(id) and statusFor(id) ~= nil end, function()
        AddUITriggeredEvent('CELevelTesting', 'pause_offers', ConvertStringToLuaID(tostring(id)))
    end)
end
local function register()
    if registered then return true end
    local menu = Helper and Helper.getMenu and Helper.getMenu('InteractMenu')
    if not menu or type(menu.Add_Custom_Actions_Group) ~= 'function' or type(menu.registerCallback) ~= 'function'
        or type(menu.insertInteractionContent) ~= 'function' then return false end
    menu.Add_Custom_Actions_Group(section, text(10))
    menu.registerCallback('prepareSections_on_end', buildActions, 'civilian_economy')
    -- Native preparation returns false when a construction placeholder has no
    -- native actions, even though our custom section has already been prepared.
    -- Keep that section accessible for the exact registered hub only.
    if type(menu.prepareActions) == 'function' then
        local prepare = menu.prepareActions
        menu.prepareActions = function(...)
            local result = prepare(...)
            if result then return result end
            local raw = menu.componentSlot and menu.componentSlot.component
            local entries = menu.actions and menu.actions[section]
            if raw and isHub(ConvertStringTo64Bit(tostring(raw))) and type(entries) == 'table' and #entries > 0 then
                DebugError('[CE] Hub has no native menu actions; displaying civilian testing section')
                return true
            end
            return result
        end
    end
    registered = true
    DebugError('[CE] Level testing menu registered')
    return true
end
if not register() and type(Register_OnLoad_Init) == 'function' then Register_OnLoad_Init(register, 'ce_debug_tools') end
-- Retry after all addons are loaded, without making population depend on UIX.
RegisterEvent('CEPopulationRequest', function() if not registered then register() end end)
