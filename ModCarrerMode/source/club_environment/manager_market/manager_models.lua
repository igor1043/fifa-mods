-- Career only. -1 preserves every fixed Revolution Mod club assignment;
-- 0 skips those overrides and lets FIFA load its ordinary generic manager.
-- The native callback validates the loaded save/context at resource lookup.
local CareerManagerBaseRM = GetRMSle
function GetRMSle(idx, isModel)
    local s = db.sle[idx]
    if s and (s.sletype == 10 or s.sletype == 11)
        and type(FIFA16_Career_Manager_Asset) == 'function' then
        local asset = FIFA16_Career_Manager_Asset(s.teamid)
        if asset == 0 then return '' end
        if type(asset) == 'number' and asset > 0 and asset <= 200000 and asset == math.floor(asset) then
            local weather = (s.cold == 1) and 1 or 0
            local suffix = (isModel == 1) and '_textures' or ''
            return 'data/sceneassets/manager_market/' .. asset .. '/model_' .. weather .. suffix .. '.rx3;'
        end
    end
    return CareerManagerBaseRM(idx, isModel)
end
