-- Dedicated appearance of type 16; normal officials, VAR cabin and entrance props are preserved.
local MachineBaseUpdate=SleUpdate
function SleUpdate(idx)
    MachineBaseUpdate(idx)
    local s=db.sle[idx]
    s.isSmokeMachine=0
    if s.sletype==16 and FIFA16_SMOKE_MACHINE_HOOK_READY==true then
        local row=gSportsRNA:GetTable("wvSle",idx)
        if gSportsRNA:GetInt(row,"sleindex")==1 then
            s.isSmokeMachine=1
            s.isMascot=0;s.isEntranceProps=0;s.isVarCabin=0
            s.slename="cameramansitting"
            s.attribmatname="simple_character_static"
            s.customcolor=4294967295
        end
    end
end
local MachineBaseTexture=GetTexture
function GetTexture(idx)
    if db.sle[idx] and db.sle[idx].isSmokeMachine==1 then return "data/sceneassets/smoke_machine/textures.rx3" end
    return MachineBaseTexture(idx)
end
local MachineBaseRM=GetRMSle
function GetRMSle(idx,isModel)
    if db.sle[idx] and db.sle[idx].isSmokeMachine==1 then
        if isModel==1 then return "data/sceneassets/smoke_machine/textures.rx3;" end
        return "data/sceneassets/smoke_machine/model.rx3;"
    end
    return MachineBaseRM(idx,isModel)
end
local function MachineAppend(gr,batch,sles)
    local nextIndex=0
    for k in pairs(sles) do if type(k)=="number" and k>=nextIndex then nextIndex=k+1 end end
    if nextIndex>=176 then return false end
    if db.sle[nextIndex]==nil then db.sle[nextIndex]={} end
    sles[nextIndex]=gr:Create("sle",nextIndex)
    gr:AddSubObject(batch,sles[nextIndex],16)
    return true
end
local MachineBaseVariations=CreateSleVariations
function CreateSleVariations(gr,batch,sles)
    MachineBaseVariations(gr,batch,sles)
    FIFA16_SMOKE_MACHINE_LIVE_CREATED=MachineAppend(gr,batch,sles)
end
function FIFA16_SMOKE_MACHINE_CREATE_LIVE()
    if FIFA16_SMOKE_MACHINE_LIVE_CREATED then return end
    if gRenderObj and gRenderObj.batchSle and gRenderObj.sles then
        FIFA16_SMOKE_MACHINE_LIVE_CREATED=MachineAppend(gRenderables,gRenderObj.batchSle,gRenderObj.sles)
    end
end
FIFA16_SMOKE_MACHINE_LUA_V1=true
