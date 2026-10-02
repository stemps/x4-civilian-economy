-- Respect player intervention in the native production pause control.
-- No UI timer owns simulation state; MD persists all effect deadlines.
local hooked
local function register()
    if hooked then return end
    local menu = Helper and Helper.getMenu and Helper.getMenu('StationOverviewMenu')
    if not menu or type(menu.buttonPauseProductionModules) ~= 'function' then return end
    local native = menu.buttonPauseProductionModules
    menu.buttonPauseProductionModules = function(modules, pause, ...)
        for _, module in ipairs(modules) do
            AddUITriggeredEvent('CEProductionPause', 'player', ConvertStringToLuaID(tostring(module)))
        end
        return native(modules, pause, ...)
    end
    hooked = true
end
register()
if type(Register_OnLoad_Init) == 'function' then Register_OnLoad_Init(register, 'ce_unrest') end
RegisterEvent('CEPopulationRequest', register)
