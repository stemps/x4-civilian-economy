-- Optional testing UI. MD owns all economic and construction state.
local ffi = require('ffi')
ffi.cdef[[
    void ForceBuildCompletion(uint64_t containerid);
    float GetCurrentBuildProgress(uint64_t containerid);
    bool IsBuildWaitingForSecondaryComponentResources(uint64_t containerid);
]]
local C = ffi.C
local section = 'actions_ce_debug'
local registered = false
local M = CEHubStatus
local text, isHub, statusFor = M.text, M.isHub, M.getFresh
local function canFinish(id)
    return isHub(id) and (C.GetCurrentBuildProgress(id) >= 0 or C.IsBuildWaitingForSecondaryComponentResources(id))
end
local function canQueue(id)
    local s = statusFor(id)
    return s and s.active and s.level < 10 and s.target == 0 and s.plotReady
end
local function buildActions()
    local menu = Helper.getMenu('InteractMenu')
    local raw = menu and menu.componentSlot and menu.componentSlot.component
    if not raw then return end
    local id = M.id(raw)
    if not isHub(id) then return end
    local function row(label, hint)
        menu.insertInteractionContent(section, {text=label, active=false, mouseOverText=hint or (label .. '\n' .. text(16))})
    end
    local s = statusFor(id)
    if s then
        if s.stale then row(text(88)) end
        if s.profileError then row(text(89)) end
        row(text(32, s.level, s.target))
        row(text(s.active and 34 or 35))
        if s.target > 0 then row(text(99, s.target), text(105))
        elseif s.level == 10 then row(text(100))
        else row(text(113, s.growth/60, s.required/60)) end
        if s.population then row(text(44), text(45, s.population)) end
        if not s.plotReady then row(text(36), text(43)) end
        if s.testUpgrade then row(text(37)) end
        for _, w in ipairs(s.wares) do
            row(w.name, M.wareHint(s, w))
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
    action(text(s and s.pausedOffers and 42 or 41), function() return statusFor(id) ~= nil end, function()
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
            if raw and isHub(M.id(raw)) and type(entries) == 'table' and #entries > 0 then
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
