-- A private second appearance of type 17. Native steadycam actors keep appearance 0.
-- RX3 resources are requested by the native scene callback, never by ball Render.
if not FIFA16_STANDBALL_LUA_V1 then
local allowed={brasileirao=true,cbf=true,paulistao=true,generic1=true,generic2=true}
local function variant()
    local name=FIFA16_STANDBALL_VARIANT
    return allowed[name] and name or 'generic1'
end
local baseUpdate=SleUpdate
function SleUpdate(idx)
    baseUpdate(idx)
    local s=db.sle[idx]
    s.isStandBall=0
    if s.sletype==17 and FIFA16_STANDBALL_HOOK_READY==true then
        local row=gSportsRNA:GetTable('wvSle',idx)
        if gSportsRNA:GetInt(row,'sleindex')==1 then
            s.isStandBall=1
            s.isMascot=0;s.isEntranceProps=0;s.isVarCabin=0;s.isSmokeMachine=0
            s.slename='cameramansitting'
            s.attribmatname='simple_character_static'
            s.customcolor=4294967295
        end
    end
end
local baseTexture=GetTexture
function GetTexture(idx)
    if db.sle[idx] and db.sle[idx].isStandBall==1 then
        return 'data/sceneassets/standball/'..variant()..'/textures.rx3'
    end
    return baseTexture(idx)
end
local baseModel=GetRMSle
function GetRMSle(idx,isModel)
    if db.sle[idx] and db.sle[idx].isStandBall==1 then
        local file=isModel==1 and 'textures.rx3;' or 'model.rx3;'
        return 'data/sceneassets/standball/'..variant()..'/'..file
    end
    return baseModel(idx,isModel)
end
local pendingSles,pendingBatch,pendingIndex,pendingActor
local function append(gr,batch,sles)
    if FIFA16_STANDBALL_HOOK_READY~=true then return false end
    for k in pairs(sles) do
        if type(k)=='number' then
            local ok,exists=pcall(function()
                local row=gSportsRNA:GetTable('wvSle',k)
                return gSportsRNA:GetInt(row,'sletype')==17 and gSportsRNA:GetInt(row,'sleindex')==1
            end)
            if ok and exists then return true end
        end
    end
    if pendingSles==sles and pendingBatch==batch and pendingActor~=nil and
       sles[pendingIndex]==pendingActor then return true end
    local index=0
    for k in pairs(sles) do if type(k)=='number' and k>=index then index=k+1 end end
    if index>=176 then return false end
    if db.sle[index]==nil then db.sle[index]={} end
    sles[index]=gr:Create('sle',index)
    gr:AddSubObject(batch,sles[index],17)
    pendingSles,pendingBatch,pendingIndex,pendingActor=sles,batch,index,sles[index]
    return true
end
local baseVariations=CreateSleVariations
function CreateSleVariations(gr,batch,sles)
    baseVariations(gr,batch,sles)
    FIFA16_STANDBALL_LIVE_CREATED=append(gr,batch,sles)
end
function FIFA16_STANDBALL_CREATE_LIVE()
    if gRenderObj and gRenderObj.batchSle and gRenderObj.sles then
        FIFA16_STANDBALL_LIVE_CREATED=append(gRenderables,gRenderObj.batchSle,gRenderObj.sles)
    end
end
FIFA16_STANDBALL_LUA_V1=true
end
