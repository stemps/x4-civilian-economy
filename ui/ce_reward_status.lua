-- Read-only reward presentation. All values and unlock levels come from MD.
CERewardStatus = {}
local R, M = CERewardStatus, CEHubStatus
local function valid(s)
    local b=s and s.rewards
    if not s or s.stale or not s.available or type(b)~='table' or b[1]~=1 then return end
    if type(b[4])~='table' or type(b[17])~='table' or #b[17]~=5 then return end
    for _,i in ipairs({5,6,7,10,11,12,13,14,15,16}) do
        if type(b[i])~='number' or b[i]~=b[i] or math.abs(b[i])==math.huge then return end
    end
    for _,v in ipairs(b[17]) do if type(v)~='number' then return end end
    return b
end
local function active(b) return b[2]==true or b[2]==1 end
function R.summary(s)
    local b=valid(s)
    if not b then return M.text(401)..': '..M.text(68) end
    return M.text(401)..': '..M.text(active(b) and 404 or 405)
end
function R.summaryColor(s)
    local b=valid(s)
    if not b then return 'text_inactive' end
    return active(b) and 'text_positive' or 'text_negative'
end
function R.reason(s)
    local b=valid(s)
    if not b then return M.text(68) end
    if active(b) then return M.text(420) end
    if b[3]=='shortage' then return M.text(411) end
    return b[3]=='no_demand' and M.text(421) or ''
end
function R.rows(s)
    local b=valid(s)
    local rows={}
    for i=1,5 do
        local state, value, hint = M.text(68), '-', M.text(68)
        local color='text_inactive'
        if b then
            local unlocked=s.level>=b[17][i]
            state=not unlocked and M.text(406,b[17][i]) or (active(b) and M.text(404) or M.text(405))
            color=not unlocked and 'text_inactive' or (active(b) and 'text_positive' or 'text_negative')
            if i==1 then value=M.text(412,b[5]);hint=M.text(423,b[10])
            elseif i==2 then value=M.text(413,b[6]);hint=M.text(424,b[11])
            elseif i==3 then value=M.text(414,b[7]);hint=M.text(425)
            elseif i==4 then value=M.text(415,b[12]);hint=M.text(426)
            else
                value=M.text(unlocked and active(b) and 416 or 433);hint=M.text(427)
            end
            hint=hint..'\n'..R.reason(s)
        end
        rows[i]={name=M.text(({408,409,410,428,429})[i]),value=value,state=state,hint=hint,color=color}
    end
    return rows
end
