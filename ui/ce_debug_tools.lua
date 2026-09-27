-- Optional testing UI. MD owns all economic and construction state.
local ffi = require('ffi')
ffi.cdef[[
    bool IsComponentClass(uint64_t componentid, const char* classname);
    void ForceBuildCompletion(uint64_t containerid);
    float GetCurrentBuildProgress(uint64_t containerid);
    bool IsBuildWaitingForSecondaryComponentResources(uint64_t containerid);
]]
local C = ffi.C
local section = 'actions_ce_debug'
local registered = false
local M = CEHubStatus
local text, isHub, statusFor = M.text, M.isHub, M.getFresh
local function debugEnabled()
    local value = GetNPCBlackboard(ConvertStringToLuaID(tostring(C.GetPlayerID())), '$ce_debug_enabled')
    return value == true or value == 1
end
local function canCreate(id)
    return id and C.IsValidComponent(id) and C.IsComponentClass(id, 'sector') and M.canCreateInSector(id)
end
local function canFinish(id)
    return isHub(id) and (C.GetCurrentBuildProgress(id) >= 0 or C.IsBuildWaitingForSecondaryComponentResources(id))
end
local function canQueue(id)
    local s = statusFor(id)
    return s and s.active and s.level < 10 and s.target == 0 and s.plotReady
end
local function canAdvance(id, level)
    local s = statusFor(id)
    return s and s.active and s.target == 0 and level > s.level and level <= 10
end
local function buildActions()
    if not debugEnabled() then return end
    local menu = Helper.getMenu('InteractMenu')
    local raw = menu and menu.componentSlot and menu.componentSlot.component
    if not raw then return end
    local id = M.id(raw)
    if canCreate(id) then
        local used = false
        menu.insertInteractionContent(section, {text=text(138), active=true, mouseOverText=text(139), script=function()
            if used or not debugEnabled() or not canCreate(id) then return end
            used = true
            AddUITriggeredEvent('CESectorTesting', 'create_hub_5b', ConvertStringToLuaID(tostring(id)))
            menu.onCloseElement('close')
        end})
        return
    end
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
        if s.populationOverride then row(text(140)) end
        if s.debugFallback then row(text(141)) end
        if not s.plotReady then row(text(36), text(43)) end
        if s.testUpgrade then row(text(37)) end
        for _, w in ipairs(s.wares) do
            row(w.name, M.wareHint(s, w))
        end
    else
        row(text(68))
    end
    local actionSection = section .. '_station'
    menu.insertInteractionGroup(section, actionSection, text(301))
    menu.insertInteractionGroup(section, section .. '_wares', text(302))
    local function action(label, allowed, run, hint)
        local used = false
        menu.insertInteractionContent(actionSection, {text=label, active=not not allowed(), mouseOverText=hint or (label == text(11) and text(12) or label), script=function()
            if used or not debugEnabled() or not allowed() then return end
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
    local progressToken = s and s.unrest and s.unrest.token
    action(text(308), function()
        local fresh = statusFor(id)
        return fresh and not fresh.stale and fresh.active and fresh.level < 10 and fresh.target == 0
            and fresh.growth < fresh.required and progressToken and fresh.unrest and fresh.unrest.token == progressToken
    end, function()
        AddUITriggeredEvent('CEProgressTesting', 'hour:' .. string.format('%d', progressToken), ConvertStringToLuaID(tostring(id)))
    end, text(309))
    for level=2,10 do
        local target = level
        action(text(124, target), function() return canAdvance(id, target) end, function()
            AddUITriggeredEvent('CELevelTesting', 'advance_level_' .. target, ConvertStringToLuaID(tostring(id)))
        end, text(125))
    end
    actionSection = section .. '_wares'
    action(text(s and s.pausedOffers and 42 or 41), function() return statusFor(id) ~= nil end, function()
        AddUITriggeredEvent('CELevelTesting', 'pause_offers', ConvertStringToLuaID(tostring(id)))
    end)
    if s and not s.stale and s.unrest and s.unrest.token then
        local token = s.unrest.token
        for _, w in ipairs(s.wares) do
            if w.rate > 0 then
                local key = w.key
                actionSection = section .. '_ware_' .. key
                menu.insertInteractionGroup(section .. '_wares', actionSection, w.name)
                for _, mode in ipairs({'random', 'zero'}) do
                    local command = mode .. ':' .. key .. ':' .. string.format('%d', token)
                    action(text(mode == 'random' and 304 or 305), function()
                        local fresh = statusFor(id)
                        local ware = M.find(fresh, key)
                        return fresh and not fresh.stale and fresh.unrest and fresh.unrest.token == token
                            and ware and ware.rate > 0
                    end, function()
                        AddUITriggeredEvent('CEWareTesting', command, ConvertStringToLuaID(tostring(id)))
                    end, text(mode == 'random' and 306 or 307))
                end
            end
        end
    end
    if s and s.demandEvent then
        actionSection = section .. '_events'
        menu.insertInteractionGroup(section, actionSection, text(338))
        local token = s.demandEvent.token
        local function eligible(eventID)
            local fresh = statusFor(id)
            local e = fresh and fresh.demandEvent
            if not fresh or fresh.stale or not e or e.token ~= token then return false end
            if eventID == 0 then return e.id > 0 end
            if not fresh.active or fresh.profileError then return false end
            for _, candidate in ipairs(e.eligible) do if candidate == eventID then return true end end
            return false
        end
        for index=0,11 do
            local eventID = index
            action(eventID == 0 and text(340) or text(339, text(320 + eventID)),
                function() return eligible(eventID) end,
                function()
                    AddUITriggeredEvent('CEEventTesting', string.format('%d:%d', eventID, token), ConvertStringToLuaID(tostring(id)))
                end, text(eventID == 0 and 342 or (eligible(eventID) and 341 or 343)))
        end
    end
    if s and s.unrest and s.unrest.token then
        actionSection = section .. '_unrest'
        menu.insertInteractionGroup(section, actionSection, text(303))
        local token = s.unrest.token
        local commands = {'stage_1','stage_2','stage_3','stage_4','clear','warning',
            'raid_1','raid_2','raid_3','production','turrets','cargo','shields','destroy','cooldowns'}
        for index, command in ipairs(commands) do
            local control = command .. ':' .. string.format('%d', token)
            action(text(210 + index), function()
                local fresh = statusFor(id)
                return fresh and not fresh.stale and fresh.unrest and fresh.unrest.token == token
            end, function()
                AddUITriggeredEvent('CEUnrestTesting', control, ConvertStringToLuaID(tostring(id)))
            end, text(226))
        end
    end
end
local function register()
    if registered then return true end
    local menu = Helper and Helper.getMenu and Helper.getMenu('InteractMenu')
    if not menu or type(menu.Add_Custom_Actions_Group) ~= 'function' or type(menu.registerCallback) ~= 'function'
        or type(menu.insertInteractionContent) ~= 'function' or type(menu.insertInteractionGroup) ~= 'function' then return false end
    menu.Add_Custom_Actions_Group(section, text(10))
    menu.registerCallback('prepareSections_on_end', buildActions, 'civilian_economy')
    -- Native preparation returns false when a construction placeholder has no
    -- native actions, even though our custom section has already been prepared.
    -- Keep only prepared hub or eligible sector debug actions accessible.
    if type(menu.prepareActions) == 'function' then
        local prepare = menu.prepareActions
        menu.prepareActions = function(...)
            local result = prepare(...)
            if result then return result end
            local raw = menu.componentSlot and menu.componentSlot.component
            local entries = menu.actions and menu.actions[section]
            if debugEnabled() and raw and (isHub(M.id(raw)) or canCreate(M.id(raw))) and type(entries) == 'table' and #entries > 0 then
                DebugError('[CE] Displaying prepared civilian testing section')
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

-- MD emits this only for an explicitly requested debug advance with a native build.
RegisterEvent('CEAdvanceBuildReady', function(_, raw)
    local id = M.id(raw)
    local s = id and statusFor(id)
    if s and s.testUpgrade and s.target > s.level and canFinish(id) then
        DebugError('[CE] TEST: automatically completing target level ' .. s.target .. ' on ' .. tostring(id))
        C.ForceBuildCompletion(id)
        AddUITriggeredEvent('CELevelTesting', 'advance_complete', ConvertStringToLuaID(tostring(id)))
    end
end)

-- Initial creation is authorized separately from growth/upgrade shortcuts.
RegisterEvent('CEInitialBuildReady', function(_, raw)
    local id = M.id(raw)
    local s = id and statusFor(id)
    if s and s.debugInitial and not s.stale and s.target == 0
        and GetComponentData(id, 'owner') == 'civilian' and canFinish(id) then
        DebugError('[CE] TEST: automatically completing initial build on ' .. tostring(id))
        C.ForceBuildCompletion(id)
        AddUITriggeredEvent('CELevelTesting', 'initial_complete', ConvertStringToLuaID(tostring(id)))
    end
end)
