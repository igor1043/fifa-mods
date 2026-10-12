-- Installed by this DLL on the engine scene thread, before Crowd3dAssetBind.
-- Native instance selection is handled by the DLL; Lua registers kit textures.
if Crowd3dAssetBind ~= FIFA16_ULTRA_KITS_BIND_WRAPPER then
    assert(type(Crowd3dAssetBind) == "function", "Crowd3dAssetBind is unavailable")
    assert(type(CrowdUpdate) == "function", "CrowdUpdate is unavailable")
    local originalBind = Crowd3dAssetBind
    local originalUpdate = CrowdUpdate
    local originalShirt = GetRMCrowdShirt
    local function isBrazilClub(team)
        return FIFA16_ULTRA_LIVE_BRAZIL and FIFA16_ULTRA_LIVE_BRAZIL[team] == true
    end

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
