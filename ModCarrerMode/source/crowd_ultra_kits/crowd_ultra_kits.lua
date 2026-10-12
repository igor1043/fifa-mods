-- Installed by this DLL on the engine scene thread, before Crowd3dAssetBind.
-- Native instance selection is handled by the DLL; Lua registers kit textures.
if Crowd3dAssetBind ~= FIFA16_ULTRA_KITS_BIND_WRAPPER then
    assert(type(Crowd3dAssetBind) == "function", "Crowd3dAssetBind is unavailable")
    assert(type(CrowdUpdate) == "function", "CrowdUpdate is unavailable")
    local originalBind = Crowd3dAssetBind
    local originalUpdate = CrowdUpdate
    local originalShirt = GetRMCrowdShirt
    local brazilClubs = {[383]=true,[517]=true,[567]=true,[568]=true,[569]=true,[598]=true,[983]=true,[1035]=true,[1039]=true,[1041]=true,[1043]=true,[1048]=true,[1053]=true,[1477]=true,[1598]=true,[1629]=true,[1719]=true,[1789]=true,[105501]=true,[105502]=true,[105503]=true,[105504]=true,[105511]=true,[105516]=true,[105517]=true,[105519]=true,[105520]=true,[105521]=true,[105522]=true,[105523]=true,[105524]=true,[105526]=true,[105527]=true,[105528]=true,[105529]=true,[105530]=true,[105531]=true,[105532]=true,[105533]=true,[110378]=true,[110540]=true,[110548]=true,[110549]=true,[111041]=true,[111042]=true,[111043]=true,[111044]=true,[111045]=true,[111046]=true,[111048]=true,[111049]=true,[111050]=true,[111052]=true,[111054]=true,[111057]=true,[111058]=true,[111059]=true,[111292]=true,[111293]=true,[111299]=true,[111300]=true,[111701]=true,[111704]=true,[111727]=true,[111976]=true,[112001]=true,[112077]=true,[112119]=true,[112190]=true,[112408]=true,[112427]=true,[112476]=true,[113007]=true,[113011]=true,[113013]=true,[113015]=true,[113016]=true,[113018]=true,[113022]=true,[113028]=true,[113055]=true,[113080]=true,[113101]=true,[113102]=true,[113103]=true,[113104]=true,[113105]=true,[113107]=true,[113111]=true,[113113]=true,[113115]=true,[113116]=true,[113117]=true,[113119]=true,[113120]=true,[113121]=true,[113124]=true,[113125]=true,[113127]=true,[113130]=true,[113132]=true,[113133]=true,[113134]=true,[113135]=true,[113136]=true,[113139]=true,[113145]=true,[113146]=true,[113149]=true,[113150]=true,[113152]=true,[113154]=true,[113163]=true,[113165]=true,[113167]=true,[113169]=true,[113172]=true,[120000]=true,[120001]=true,[120002]=true,[120003]=true,[120004]=true,[120005]=true,[120006]=true,[120007]=true,[120008]=true,[120009]=true,[120010]=true,[120011]=true,[120012]=true,[120013]=true,[120015]=true,[120016]=true,[120017]=true,[120018]=true,[120019]=true,[120020]=true,[120409]=true,[120410]=true,[120414]=true,[120415]=true,[120424]=true,[120425]=true,[120426]=true,[120428]=true,[120429]=true,[120432]=true,[120433]=true,[120435]=true,[120438]=true,[120439]=true,[120440]=true,[120441]=true,[120444]=true,[123917]=true,[123921]=true,[123922]=true,[123923]=true,[130011]=true,[130012]=true,[130016]=true,[130018]=true,[130019]=true,[130020]=true,[130021]=true,[130022]=true,[130023]=true,[130024]=true,[130025]=true,[130026]=true,[130027]=true,[130028]=true,[130029]=true,[130030]=true,[130033]=true,[130036]=true,[130037]=true,[130040]=true,[130041]=true,[130042]=true,[130043]=true,[130045]=true,[130046]=true,[130047]=true,[130053]=true,[130058]=true,[130059]=true,[130062]=true,[130063]=true,[130064]=true,[130065]=true,[130066]=true,[130067]=true,[130068]=true,[130069]=true,[130070]=true,[130071]=true,[130072]=true,[130073]=true,[130074]=true,[130075]=true,[130076]=true,[130077]=true,[130078]=true,[130079]=true,[130080]=true,[130081]=true,[130082]=true,[130083]=true,[130084]=true,[130085]=true,[130086]=true,[130087]=true,[130088]=true,[130089]=true,[130090]=true,[130091]=true,[130092]=true,[130093]=true,[130094]=true,[130095]=true,[130096]=true,[130097]=true,[130098]=true,[130099]=true,[130100]=true,[130101]=true,[130102]=true,[130103]=true,[130104]=true,[130105]=true,[130106]=true,[130107]=true,[130108]=true,[130109]=true,[130110]=true,[130111]=true,[130112]=true,[130113]=true,[130114]=true,[130115]=true,[130116]=true,[130117]=true,[130118]=true,[130119]=true,[130120]=true,[130121]=true,[130122]=true,[130123]=true,[130124]=true,[130125]=true,[130126]=true,[130127]=true,[130128]=true,[130129]=true,[130130]=true,[130131]=true,[130132]=true,[130133]=true,[130134]=true,[130135]=true,[130136]=true,[130137]=true,[130138]=true,[130139]=true,[130140]=true,[130141]=true,[130142]=true,[130143]=true,[130144]=true,[130145]=true,[130146]=true,[130147]=true,[130148]=true,[130149]=true,[130150]=true,[130151]=true,[130154]=true,[130157]=true,[130158]=true,[130159]=true,[130161]=true,[130162]=true,[130163]=true,[130164]=true,[130165]=true,[130166]=true,[130167]=true,[130168]=true,[130169]=true,[130170]=true,[130171]=true,[130173]=true,[130174]=true,[130176]=true,[130177]=true,[130181]=true,[130183]=true,[130184]=true,[130185]=true,[130186]=true,[130187]=true,[130188]=true,[130189]=true,[130190]=true,[130191]=true,[130192]=true,[130203]=true,[130206]=true,[130208]=true,[130209]=true,[130210]=true,[130211]=true,[130212]=true,[130213]=true,[130214]=true,[130215]=true,[130216]=true,[130218]=true,[130219]=true,[130220]=true,[130230]=true,[130232]=true,[130234]=true,[130240]=true,[130241]=true,[130242]=true,[130245]=true,[130246]=true,[130247]=true,[130248]=true,[130250]=true,[130251]=true,[130252]=true,[130253]=true,[130254]=true,[130255]=true,[130256]=true,[130259]=true,[130260]=true,[130261]=true,[130262]=true,[130263]=true,[130264]=true,[130265]=true,[130266]=true,[130267]=true,[130268]=true,[130269]=true,[130270]=true,[130274]=true,[130277]=true,[130278]=true,[130279]=true,[130280]=true,[130281]=true,[130282]=true,[130283]=true,[130284]=true,[130285]=true,[130286]=true,[130287]=true,[130288]=true,[130289]=true,[130290]=true,[130291]=true,[130292]=true,[130293]=true,[130294]=true,[130295]=true,[130296]=true,[130297]=true,[130298]=true,[130300]=true,[130301]=true,[130302]=true,[130303]=true,[130304]=true,[130305]=true,[130306]=true,[130307]=true,[130308]=true,[130309]=true,[130310]=true,[130311]=true,[130312]=true,[130313]=true,[130314]=true,[130315]=true,[130316]=true,[130317]=true,[130318]=true,[130319]=true,[130320]=true,[130321]=true,[130322]=true,[130324]=true,[130325]=true,[130326]=true,[130327]=true,[130328]=true,[130329]=true,[130330]=true,[130331]=true,[130332]=true,[130333]=true,[130334]=true,[130335]=true,[130336]=true,[130337]=true,[130338]=true,[130339]=true,[130340]=true,[130341]=true,[130342]=true,[130343]=true,[130344]=true,[130345]=true,[130346]=true,[130347]=true,[130348]=true,[130349]=true,[130350]=true,[130354]=true,[130355]=true,[130356]=true,[130357]=true,[130358]=true,[130359]=true,[130360]=true,[130361]=true,[130362]=true,[130363]=true,[130364]=true,[130365]=true,[130366]=true,[130367]=true,[130368]=true,[130372]=true,[130377]=true,[130378]=true,[130379]=true,[130380]=true,[130381]=true,[130382]=true,[130383]=true,[130384]=true,[130385]=true,[130386]=true,[130387]=true,[130388]=true,[130389]=true,[130390]=true,[130391]=true,[130392]=true,[130396]=true,[130397]=true,[130403]=true,[130406]=true,[130407]=true,[130412]=true,[130413]=true,[130414]=true,[130415]=true,[130416]=true,[130417]=true,[130418]=true,[130419]=true,[130420]=true,[130421]=true,[130422]=true,[130423]=true,[130425]=true,[130426]=true,[130427]=true,[130428]=true,[130429]=true,[130430]=true,[130431]=true,[130432]=true,[130433]=true,[130434]=true,[130435]=true,[130436]=true,[130437]=true,[130438]=true,[130439]=true,[130440]=true,[130441]=true,[130442]=true,[130443]=true,[130445]=true,[130448]=true,[130460]=true,[130461]=true,[130462]=true,[130463]=true,[130464]=true,[130465]=true,[130466]=true,[130467]=true,[130468]=true,[130469]=true,[130470]=true,[130549]=true,[130614]=true,[130615]=true,[130616]=true,[130623]=true,[130624]=true,[130626]=true,[130627]=true,[130901]=true,[131000]=true}
    local function isBrazilClub(team) return brazilClubs[team] == true end

    function FIFA16UltraThirdKit(idx, side)
        local c = db.crowd[idx]
        local team = side == 1 and c.homeKitTeamID or c.awayKitTeamID
        -- FIFA outfield kits: 0 = first, 1 = second, 3 = third; 2 is goalkeeper.
        return "data/sceneassets/kit/kit_"..team.."_3_0.rx3;"..
               "data/sceneassets/kit/kit_"..team.."_0_0.rx3;"
    end

    function FIFA16UltraGoalkeeperKit(idx, side)
        local c = db.crowd[idx]
        local team = side == 1 and c.homeKitTeamID or c.awayKitTeamID
        return "data/sceneassets/kit/kit_"..team.."_2_0.rx3;"..
               "data/sceneassets/kit/kit_"..team.."_0_0.rx3;"
    end

    function GetRMCrowdShirt(idx, side, character)
        local c = db.crowd[idx]
        local team = side == 1 and c.homeKitTeamID or c.awayKitTeamID
        local club = side == 1 and c.homeTeamID or c.awayTeamID
        if not isBrazilClub(club) then return originalShirt(idx, side, character) end
        local kit = character == 33 and 1 or 0
        return "data/sceneassets/kit/kit_"..team.."_"..kit.."_0.rx3;"..
               "data/sceneassets/kit/kit_"..team.."_0_0.rx3;"
    end

    CrowdUpdate = function(idx)
        originalUpdate(idx)
        -- Keep the four native ultra prototypes available. Actual attendance
        -- remains in native seat states and the separate attendance plugin.
        if isBrazilClub(db.crowd[idx].homeTeamID) then db.crowd[idx].homecrowdsize = 6 end
        if isBrazilClub(db.crowd[idx].awayTeamID) then db.crowd[idx].awaycrowdsize = 2 end
    end

    Crowd3dAssetBind = function(crowd)
        local result = originalBind(crowd)
        gRenderables:AddAsset(crowd, 0, "ultra_kit3_home", "${FIFA16UltraThirdKit(?,1)}", 2)
        gRenderables:AddAsset(crowd, 0, "ultra_kit3_away", "${FIFA16UltraThirdKit(?,2)}", 2)
        gRenderables:AddAsset(crowd, 0, "ultra_gk_home", "${FIFA16UltraGoalkeeperKit(?,1)}", 2)
        gRenderables:AddAsset(crowd, 0, "ultra_gk_away", "${FIFA16UltraGoalkeeperKit(?,2)}", 2)
        return result
    end
    FIFA16_ULTRA_KITS_BIND_WRAPPER = Crowd3dAssetBind
    FIFA16_ULTRA_KITS_V1 = true
end
