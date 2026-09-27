-- MD owns authorization, confirmation expiry and the persistent removal queue.
CEDebugReset = {}
local C = require('ffi').C
local M = CEHubStatus
local function state()
    return GetNPCBlackboard(ConvertStringToLuaID(tostring(C.GetPlayerID())), '$ce_reset')
end
local function enabled()
    local v = GetNPCBlackboard(ConvertStringToLuaID(tostring(C.GetPlayerID())), '$ce_debug_enabled')
    return v == true or v == 1
end
function CEDebugReset.busy()
    local s = state()
    return type(s) == 'table' and (s[2] == true or s[2] == 1)
end
function CEDebugReset.eligible(id)
    return id and C.IsValidComponent(id) and (C.IsComponentClass(id, 'sector') or M.isHub(id))
end
function CEDebugReset.add(menu, section, id)
    local s = state()
    if not enabled() or not CEDebugReset.eligible(id) or type(s) ~= 'table' or not s[1] then return end
    if CEDebugReset.busy() then
        local label = s[3] == 'initializing' and M.text(367) or M.text(364, s[5] - s[4], s[5])
        menu.insertInteractionContent(section, {text=label, active=false})
        if s[6] == true or s[6] == 1 then
            menu.insertInteractionContent(section, {text=M.text(368), mouseOverText=M.text(365), active=false})
        end
        return
    end
    local token, phase, used = s[1], s[3], false
    menu.insertInteractionContent(section, {
        text=M.text(phase == 'confirm' and 363 or 361), mouseOverText=M.text(362), active=true,
        script=function()
            local fresh = state()
            if used or not enabled() or not CEDebugReset.eligible(id) or CEDebugReset.busy()
                or type(fresh) ~= 'table' or fresh[1] ~= token or fresh[3] ~= phase then return end
            used = true
            AddUITriggeredEvent('CEResetTesting', (phase == 'confirm' and 'confirm:' or 'arm:') .. tostring(token),
                ConvertStringToLuaID(tostring(id)))
            menu.onCloseElement('close')
        end,
    })
end
