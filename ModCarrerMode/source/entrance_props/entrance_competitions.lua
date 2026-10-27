-- FIFA16_ENTRANCE_COMPETITIONS_V17
-- Resources are published only after the native catalogue validates both RX3s.
local CompetitionPropsBaseUpdate = SleUpdate
local CompetitionPropsBaseTexture = GetTexture
local CompetitionPropsBaseRM = GetRMSle
local function CompetitionPropsAvailable()
    return type(FIFA16_ENTRANCE_MODEL_FILE) == "string" and
           type(FIFA16_ENTRANCE_TEXTURE_FILE) == "string" and
           FIFA16_ENTRANCE_MODEL_FILE ~= "" and FIFA16_ENTRANCE_TEXTURE_FILE ~= ""
end
function SleUpdate(idx)
    CompetitionPropsBaseUpdate(idx)
    local s = db.sle[idx]
    if s.isEntranceProps == 1 and not CompetitionPropsAvailable() then s.isEntranceProps = 0 end
end
function GetTexture(idx)
    local s = db.sle[idx]
    if s and s.isEntranceProps == 1 then
        if CompetitionPropsAvailable() then return FIFA16_ENTRANCE_TEXTURE_FILE end
        s.isEntranceProps = 0
        local result = CompetitionPropsBaseTexture(idx)
        s.isEntranceProps = 1
        return result
    end
    return CompetitionPropsBaseTexture(idx)
end
function GetRMSle(idx,isModel)
    local s = db.sle[idx]
    if s and s.isEntranceProps == 1 then
        if CompetitionPropsAvailable() then
            if isModel == 1 then return FIFA16_ENTRANCE_TEXTURE_FILE..";" end
            return FIFA16_ENTRANCE_MODEL_FILE..";"
        end
        s.isEntranceProps = 0
        local result = CompetitionPropsBaseRM(idx,isModel)
        s.isEntranceProps = 1
        return result
    end
    return CompetitionPropsBaseRM(idx,isModel)
end
FIFA16_ENTRANCE_COMPETITIONS_LUA_V17 = true
