-- FIFA16_VAR_CABIN_V1: dedicated static platform variation, preserving other mods.
-- Read the match competition before getTournamentGraphics remaps its artwork.
-- Club league assignments must not enable the cabin in cups or friendlies.
function FIFA16_VAR_CABIN_REFRESH_COMPETITION(idx)
    local s = db and db.sle and db.sle[idx]
    if not s then return end
    s.varCabinCompetitionId = -1
    local ok, id = pcall(function()
        local wipe = gSportsRNA:GetTable("wvWipe", 1)
        return gSportsRNA:GetInt(wipe, "leagueID")
    end)
    if ok and type(id) == "number" and id == math.floor(id) then
        s.varCabinCompetitionId = id
    end
end
local VarCabinBaseUpdate = SleUpdate
function SleUpdate(idx)
    VarCabinBaseUpdate(idx)
    local s = db.sle[idx]
    s.isVarCabin = 0
    if s.sletype == 3 and FIFA16_VAR_CABIN_HOOK_READY == true then
        local row = gSportsRNA:GetTable("wvSle", idx)
        if gSportsRNA:GetInt(row, "sleindex") == 1 then
            s.isVarCabin = 1
            s.isMascot = 0
            s.isEntranceProps = 0
            s.slename = "cameramansitting"
            s.attribmatname = "simple_character_static"
            s.customcolor = 4294967295
            FIFA16_VAR_CABIN_REFRESH_COMPETITION(idx)
        end
    end
end
local VarCabinBaseTexture = GetTexture
function GetTexture(idx)
    if db.sle[idx].isVarCabin == 1 then return "data/sceneassets/var_cabin/textures_v2.rx3" end
    return VarCabinBaseTexture(idx)
end
local VarCabinBaseRM = GetRMSle
function GetRMSle(idx, isModel)
    if db.sle[idx].isVarCabin == 1 then
        if isModel == 1 then return "data/sceneassets/var_cabin/textures_v2.rx3;" end
        return "data/sceneassets/var_cabin/model_v2.rx3;"
    end
    return VarCabinBaseRM(idx, isModel)
end
local function VarCabinAppend(gr, batch, sles)
    local nextIndex = 0
    for k, v in pairs(sles) do
        if type(k) == "number" and k >= nextIndex then nextIndex = k + 1 end
    end
    if nextIndex >= 176 then return false end
    if db.sle[nextIndex] == nil then db.sle[nextIndex] = {} end
    sles[nextIndex] = gr:Create("sle", nextIndex)
    gr:AddSubObject(batch, sles[nextIndex], 3)
    FIFA16_VAR_CABIN_RNA_INDEX = nextIndex
    return true
end
local VarCabinBaseVariations = CreateSleVariations
function CreateSleVariations(gr, batch, sles)
    VarCabinBaseVariations(gr, batch, sles)
    FIFA16_VAR_CABIN_LIVE_CREATED = VarCabinAppend(gr, batch, sles)
end
FIFA16_VAR_CABIN_LUA_V1 = true
FIFA16_VAR_CABIN_LUA_V3 = true
function FIFA16_VAR_CABIN_CREATE_LIVE()
    if FIFA16_VAR_CABIN_LIVE_CREATED then return end
    if gRenderObj and gRenderObj.batchSle and gRenderObj.sles then
        FIFA16_VAR_CABIN_LIVE_CREATED = VarCabinAppend(gRenderables, gRenderObj.batchSle, gRenderObj.sles)
    end
end

FIFA16_VAR_CABIN_MODEL_V2 = true
