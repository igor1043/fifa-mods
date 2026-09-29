IsCrowd3D = 1

function CrowdUpdate(idx)
	local as = gSportsRNA
	local state = as:GetTable("wvState")
	local crowd = as:GetTable("wvCrowd", idx)
	local stadium = as:GetTable("wvStadium", idx)
		
	db.crowd[idx].lightID = as:GetInt(state, "wvAttribEnvLighting")
	db.crowd[idx].homeTeamID = as:GetInt(crowd, "homeTeamID")
	db.crowd[idx].awayTeamID = as:GetInt(crowd, "awayTeamID")
	
	-- Figure out the home kit form the passed type. We need to make sure we load
	-- the kit with alcohol or gambling removed if applicable
	local realHomeKitType = as:GetInt(crowd, "homeKitTypeID")
	local realAwayKitType  = as:GetInt(crowd, "awayKitTypeID")
	
	db.crowd[idx].homeKitTeamID = as:GetInt(crowd, "homeKitTeamID")
	-- db.crowd[idx].homeKitTypeID = realHomeKitType - (realHomeKitType % 10)
	-- db.crowd[idx].homeKitAwayTypeID = db.crowd[idx].homeKitTypeID + 1
	db.crowd[idx].awayKitTeamID = as:GetInt(crowd, "awayKitTeamID")
	-- db.crowd[idx].awayKitTypeID = realAwayKitType - (realAwayKitType % 10)
	-- db.crowd[idx].awayKitAwayTypeID = db.crowd[idx].awayKitTypeID + 1
	
	db.crowd[idx].homeKitTypeID = 0
	db.crowd[idx].homeKitAwayTypeID = 1
	db.crowd[idx].awayKitTypeID = 0
	db.crowd[idx].awayKitAwayTypeID = 1

	local weather = as:GetInt(state, "wvAttribStadWeather")
	local climate = as:GetInt(state, "wvAttribStadClimate") -- 0: warm, 1: cold

	if (weather == 1 or weather == 2) then
		db.crowd[idx].wet = 1
	else
		db.crowd[idx].wet = 0
	end

	if (weather == 1 or weather == 2 or climate == 1) then
		db.crowd[idx].cold = 1
	else
		db.crowd[idx].cold = 0
	end
	
	
	local wipe3d = as:GetTable("wvWipe", 1)
	local leagueID = as:GetInt(wipe3d, "leagueID")
	leagueID = getTournamentGraphics(leagueID)
	
	db.crowd[idx].stadiumID = as:GetInt(state, "wvAttribStadID")

	if (idx > 0) then
	local player = as:GetTable("wvPlayer", 9)
	-- local kitYearOutfield = as:GetInt(player, "kitYear")
	-- if (kitYearOutfield > 0) then
	-- db.stadium[idx].tournID = kitYearOutfield
	-- db.stadium[idx].kitYearDecade = math.floor(kitYearOutfield/10)*10
	-- end
	if (futCustom) then
	local team = as:GetInt(player, "teamid")
	if (team == 130000) then
	db.crowd[idx].homeKitTeamID = team
	end
	player = as:GetTable("wvPlayer", 20)
	team = as:GetInt(player, "teamid")
	if (team == 130000) then
	db.crowd[idx].awayKitTeamID = team
	end
	end
	end
	
	db.crowd[idx].homeTeamLeague = 0
	db.crowd[idx].awayTeamLeague = 0
	if (teamTournament[db.crowd[idx].homeTeamID] ~= nil) then
	db.crowd[idx].homeTeamLeague = teamTournament[db.crowd[idx].homeTeamID]
	end
	if (teamTournament[db.crowd[idx].awayTeamID] ~= nil) then
	db.crowd[idx].awayTeamLeague = teamTournament[db.crowd[idx].awayTeamID]
	end
	
	db.crowd[idx].crowdDistribution = as:GetInt(crowd, "crowdDistribution")
	
	db.crowd[idx].homeTeamIDseat = db.crowd[idx].homeTeamID
	
	if (db.crowd[idx].crowdDistribution == 1) then
	db.crowd[idx].homeTeamIDseat = -1
	end
	
	db.crowd[idx].homecrowdsize = getHomeCrowdSize(db.crowd[idx].homeKitTeamID,db.crowd[idx].awayKitTeamID,leagueID,db.crowd[idx].homeTeamLeague,db.crowd[idx].awayTeamLeague,db.crowd[idx].stadiumID,db.crowd[idx].crowdDistribution)
	db.crowd[idx].awaycrowdsize = getAwayCrowdSize(db.crowd[idx].homeKitTeamID,db.crowd[idx].awayKitTeamID,leagueID,db.crowd[idx].homeTeamLeague,db.crowd[idx].awayTeamLeague,db.crowd[idx].stadiumID,db.crowd[idx].crowdDistribution)
	local homePrimaryColour = as:GetInt(stadium, "homePrimaryColour")
	
	-- local b = homePrimaryColour%256
	-- local g = (homePrimaryColour-b)%65536 / 256
	-- local r = (homePrimaryColour-(g*256)-b)%16777216 / 65536
	
	-- r = math.floor((r/85) + 0.5)
	-- g = math.floor((g/85) + 0.5)
	-- b = math.floor((b/85) + 0.5)
	
	-- db.crowd[idx].genSeatColour = "1"..r..g..b
	db.crowd[idx].genSeatColour = -1
	if (getIsGenericStadium(db.crowd[idx].stadiumID)) then
	db.crowd[idx].genSeatColour = getSimpleColourCode(homePrimaryColour)
	end
	

	
	
end

function Crowd3dAssetBind(crowd)
    local gr = gRenderables
    local lod = 0
    local priority = 2
    local ethnicity = 0
	
	gr:AddCallback(crowd, lod, "CrowdUpdate(?)")
	gr:AddAsset(crowd, lod, "shader", "data/fifarna/shader.big", priority)
	gr:AddAsset(crowd, lod, "charcmn", "data/sceneassets/charactercmn/charactercmn_${db.crowd[?].lightID}.rx3")
    
    local settingTable = gSportsRNA:GetTable("Settings")
    gSportsRNA:SetInt(settingTable, "IsCrowd3D", IsCrowd3D)
    
    local path = "data/sceneassets/crowd/"
    
	-- Normal crowd
	function BindCrowd(code_index, asset_index)
		local texpart = "bodytex_" .. code_index
		-- local texpath = path .. "crowd_" .. asset_index .. "_" .. ethnicity .. "_0_${db.crowd[?].cold}_textures.rx3"
		-- always lod cold assets
		local teamtype = 2
		if (is_home_team) then
		teamtype = 1
		end
		local texpath = "${GetRMCrowd(?,0,"..asset_index..",1,0)}"..path .. "crowd_" .. asset_index .. "_" .. ethnicity .. "_0_${db.crowd[?].cold}_textures.rx3"
		
		gr:AddAsset(crowd, lod, texpart, texpath, priority)
        
		for glod = 0, 4 do
			local glodx = glod - crowdLODAdjust
			
			if (glodx < 0) then
			glodx = 0
			end
			
			if (glodx > 4) then
			glodx = 4
			end
		
			local meshpart = "bodymesh_" .. code_index .. "_lod" .. glod
		
            gr:AddAsset(crowd, lod, meshpart,
				"${GetRMCrowd(?,0,"..asset_index..",0,"..(glodx+1)..")}"..path .. "crowd_" .. asset_index .. "_" .. ethnicity .. "_" .. (glodx+1) .. "_${db.crowd[?].cold}.rx3", priority)
				
			gr:CreateMaterial(crowd, lod, meshpart, "crowd3d_body.fx")
			gr:SetTexture(crowd, lod, meshpart, "textures", "diffuseTexture", texpart, "") -- grabs first texture from the texlib
        end
	end
	
	BindCrowd(0, 1)
	BindCrowd(1, 2)
	BindCrowd(2, 4)
	BindCrowd(3, 6)
	
	-- Ultra fans
	
	-- index: Numerical asset index (starts from 0)
	-- asset_index: Index of asset on disk
	-- is_home_team: 
	function BindUltraFan(index, asset_index, is_home_team)
		-- Add the body (head, legs) texture
		local bodytexpart = "ultrabodytex_" .. index
		local bodywrinklepart = "ultrajerseywrinkletex_" .. index
		local bodyaopart = "ultrajerseyaotex_" .. index
		--local bodytexpath = path .. "crowd_" .. asset_index .. "_" .. ethnicity .. "_0_${db.crowd[?].cold}_textures.rx3"
		
		local teamtype = 2
		if (is_home_team) then
		teamtype = 1
		end
		
		local bodytexpath = "${GetRMCrowd(?,"..teamtype..","..asset_index..",1,0)}"..path .. "crowd_" .. asset_index .. "_" .. ethnicity .. "_0_${db.crowd[?].cold}_textures.rx3"
		
		gr:AddAsset(crowd, lod, bodytexpart, bodytexpath, priority)
		gr:AddAsset(crowd, lod, bodywrinklepart, "data/sceneassets/kitcmn/jersey_1_0_0_bnm.rx3", priority)
		gr:AddAsset(crowd, lod, bodyaopart.."_dry", "data/sceneassets/kitcmn/jersey_1_0_0_textures.rx3", priority)
		gr:AddAsset(crowd, lod, bodyaopart.."_wet", "data/sceneassets/kitcmn/jersey_1_1_0_textures.rx3", priority)
		
		-- Add the jersey texture. Crowd is always wearing home kit of team
		local jerseytexpath
		if is_home_team then
			if (index < 2) then
				jerseytexpath = "${GetRMCrowdShirt(?,1,"..asset_index..")}data/sceneassets/kit/kit_${db.crowd[?].homeKitTeamID}_${db.crowd[?].homeKitTypeID}_0.rx3;data/sceneassets/kit/kit_${db.crowd[?].homeKitTeamID}_0_0.rx3"
			else
				jerseytexpath = "${GetRMCrowdShirt(?,1,"..asset_index..")}data/sceneassets/kit/kit_${db.crowd[?].homeKitTeamID}_${db.crowd[?].homeKitAwayTypeID}_0.rx3;data/sceneassets/kit/kit_${db.crowd[?].homeKitTeamID}_0_0.rx3"
			end
		else
			if (index < 2) then
				jerseytexpath = "${GetRMCrowdShirt(?,2,"..asset_index..")}data/sceneassets/kit/kit_${db.crowd[?].awayKitTeamID}_${db.crowd[?].awayKitTypeID}_0.rx3;data/sceneassets/kit/kit_${db.crowd[?].awayKitTeamID}_0_0.rx3"
			else
				jerseytexpath = "${GetRMCrowdShirt(?,2,"..asset_index..")}data/sceneassets/kit/kit_${db.crowd[?].awayKitTeamID}_${db.crowd[?].awayKitAwayTypeID}_0.rx3;data/sceneassets/kit/kit_${db.crowd[?].awayKitTeamID}_1_0.rx3"
			end
		end
		
		local jerseytexpart = "ultrajerseytex_" .. index
		gr:AddAsset(crowd, lod, jerseytexpart, jerseytexpath, priority)
		
		-- Add the mesh
		for glod = 0, 4 do		
			local glodx = glod - crowdLODAdjust
			
			if (glodx < 0) then
			glodx = 0
			end
			
			if (glodx > 4) then
			glodx = 4
			end
			
			local bodymeshpart = "ultrabodymesh_" .. index .. "_lod" .. glod
			local jerseymeshpart = "ultrajerseymesh_" .. index .. "_lod" .. glod
			local meshpath = "${GetRMCrowd(?,"..teamtype..","..asset_index..",0,"..(glodx+1)..")}"..path .. "crowd_" .. asset_index .. "_" .. ethnicity .. "_" .. (glodx+1) .. "_${db.crowd[?].cold}.rx3"
			
			-- Add the jersey
			gr:AddAsset(crowd, lod, jerseymeshpart, meshpath, priority)
			gr:CreateMaterial(crowd, lod, jerseymeshpart, "crowd3d_jersey.fx")
			gr:SetSubMesh(crowd, lod, jerseymeshpart, "crowd_jersey")
			
			-- Add the body
			gr:AddAsset(crowd, lod, bodymeshpart, meshpath, priority)
			gr:CreateMaterial(crowd, lod, bodymeshpart, "crowd3d_body.fx")
			gr:SetSubMesh(crowd, lod, bodymeshpart, "crowd_body")
			gr:SetTexture(crowd, lod, bodymeshpart, "textures", "diffuseTexture", bodytexpart, "")
		end
	end
	
	-- Away team should have odd index
	-- TODO: Put this in a loop once we have more combinations
	BindUltraFan(0, 30, true)
	BindUltraFan(1, 30, false)
	BindUltraFan(2, 33, true)
	BindUltraFan(3, 33, false)

    -- Chair
	for glod = 0,1 do
		gr:AddAsset(crowd, lod, "chairmesh_lod" .. glod, "${GetRMChairMod(?)}data/sceneassets/crowdchair/crowdchair_" .. glod .. ".rx3", priority)
		gr:AddAsset(crowd, lod, "chairtex_lod" .. glod, "${GetRMChair(?)}data/sceneassets/crowdchair/chaircmn_textures.rx3", priority)
		gr:CreateMaterial(crowd, lod, "chairmesh_lod" .. glod, "crowd3d_chair.fx")
		gr:SetTexture(crowd, lod, "chairmesh_lod" .. glod, "textures", "diffuseTexture", "chairtex_lod" .. glod, "")
	end
    
	-- Scarves
	-- TODO: Add scarf texture variation
	local scarftex_prefix = "scarftex_"
	gr:AddAsset(crowd, lod, scarftex_prefix .. "home", "data/sceneassets/flag/scarf_${db.crowd[?].homeTeamID}.rx3;data/sceneassets/flag/flag_${db.crowd[?].homeTeamID}.rx3", priority)
	gr:AddAsset(crowd, lod, scarftex_prefix .. "away", "data/sceneassets/flag/scarf_${db.crowd[?].awayTeamID}.rx3;data/sceneassets/flag/flag_${db.crowd[?].awayTeamID}.rx3", priority)
	
	for glod = 0, 4 do
		local scarfmeshname = "scarfmesh0_lod" .. glod
		gr:AddAsset(crowd, lod, scarfmeshname, path .. "crowd_scarf_0.rx3", priority)
		gr:CreateMaterial(crowd, lod, scarfmeshname, "crowd3d_accs.fx")
	end
		
	return crowd
end







function GetRMCrowdShirt(idx,ishome,character)
	local kit = ""
	
	local team = db.crowd[idx].homeKitTeamID
	local ctype = 1
	local var = math.random(0,3)
	
	if (ishome == 2) then
	team = db.crowd[idx].awayKitTeamID
	end
	
	if (character == 33) then
	ctype = 2
	end
	
	kit = kit.."data/sceneassets/crowd/crowdkit_"..team.."_"..ctype.."_"..(ishome+4)..".rx3;"
	kit = kit.."data/sceneassets/crowd/crowdkit_"..team.."_"..ctype.."_"..var..".rx3;"
	kit = kit.."data/sceneassets/crowd/crowdkit_"..team.."_"..ctype.."_0.rx3;"
	kit = kit.."data/sceneassets/crowd/crowdkit_"..team.."_0_"..(ishome+4)..".rx3;"
	kit = kit.."data/sceneassets/crowd/crowdkit_"..team.."_0_"..var..".rx3;"
	kit = kit.."data/sceneassets/crowd/crowdkit_"..team.."_0_0.rx3;"

	return kit
end

function GetRMCrowd(idx,i,j,k,l)
	local cwd = ""
	
	local tex = ""
	if (k == 1) then
	tex = "_textures"
	end
	
	local team = db.crowd[idx].homeTeamID
	local tourn = db.crowd[idx].homeTeamLeague
	--if (i == 1) then
	--team = db.crowd[idx].homeTeamID
	--end
	if (i == 2) then
	team = db.crowd[idx].awayTeamID
	tourn = db.crowd[idx].awayTeamLeague
	end
	
	
	local homecrowdchar = {} --{1,2,4,6,30,33}
	local awaycrowdchar = {} --{30,33}
	
	
	homecrowdchar[1] = 1
	homecrowdchar[2] = 3
	homecrowdchar[4] = 5
	homecrowdchar[6] = 6
	homecrowdchar[30] = 2
	homecrowdchar[33] = 4
	
	awaycrowdchar[30] = 1
	awaycrowdchar[33] = 2
	
	if (k == 0) then
	if (i == 2) then
	if (awaycrowdchar[j] > db.crowd[idx].awaycrowdsize) then
	cwd = cwd.."data/sceneassets/crowd/crowd_empty.rx3;"
	end
	else
	if (homecrowdchar[j] > db.crowd[idx].homecrowdsize) then
	cwd = cwd.."data/sceneassets/crowd/crowd_empty.rx3;"
	end
	end
	end
	
	cwd = cwd.."data/sceneassets/crowd/specificcrowd_"..team.."_0_"..j.."_"..l.."_"..db.crowd[idx].cold..""..tex..".rx3;"
	cwd = cwd.."data/sceneassets/crowd/specificcrowd_"..team.."_0_"..j.."_0_"..db.crowd[idx].cold..""..tex..".rx3;"
	cwd = cwd.."data/sceneassets/crowd/specificcrowd_"..team.."_0_"..j.."_"..l.."_0"..tex..".rx3;"
	cwd = cwd.."data/sceneassets/crowd/specificcrowd_"..team.."_0_"..j.."_0_0"..tex..".rx3;"
	
	cwd = cwd.."data/sceneassets/crowd/specificcrowd_0_"..tourn.."_"..j.."_"..l.."_"..db.crowd[idx].cold..""..tex..".rx3;"
	cwd = cwd.."data/sceneassets/crowd/specificcrowd_0_"..tourn.."_"..j.."_0_"..db.crowd[idx].cold..""..tex..".rx3;"
	cwd = cwd.."data/sceneassets/crowd/specificcrowd_0_"..tourn.."_"..j.."_"..l.."_0"..tex..".rx3;"
	cwd = cwd.."data/sceneassets/crowd/specificcrowd_0_"..tourn.."_"..j.."_0_0"..tex..".rx3;"
	return cwd
end

function GetRMChair(idx)
	local chair = ""
		
	chair = chair.."data/sceneassets/crowdchair/specificchair_"..db.crowd[idx].homeTeamIDseat.."_"..db.crowd[idx].stadiumID.."_textures.rx3;"
	chair = chair.."data/sceneassets/crowdchair/specificchair_0_"..db.crowd[idx].stadiumID.."_textures.rx3;"
	chair = chair.."data/sceneassets/crowdchair/specificchair_"..db.crowd[idx].homeTeamIDseat.."_0_textures.rx3;"
	chair = chair.."data/sceneassets/crowdchair/specificchair_0_0_textures.rx3;"
	
	chair = chair.."data/sceneassets/crowdchair/genericchair_"..db.crowd[idx].genSeatColour.."_0_textures.rx3;"

	return chair
end




homeCrowdTeam = {}
awayCrowdTeam = {}

homeCrowdGame = {}
awayCrowdGame = {}


homeCrowdTournamentTeam = {}
awayCrowdTournamentTeam = {}

homeCrowdTournamentGame = {}
awayCrowdTournamentGame = {}

homeCrowdTournament = {}
awayCrowdTournament = {}


homeCrowdTournamentFinal = {}
awayCrowdTournamentFinal = {}

homeCrowdLeagueVersusLeague = {}
awayCrowdLeagueVersusLeague = {}

homeCrowdTournamentLeagueVersusLeague = {}
awayCrowdTournamentLeagueVersusLeague = {}


homeCrowdTeamVersusLeague = {}
awayCrowdTeamVersusLeague = {}

homeCrowdTournamentTeamVersusLeague = {}
awayCrowdTournamentTeamVersusLeague = {}

homeCrowdDefault = 6
awayCrowdDefault = 2

function setDefaultCrowdSize(home,away)

if (type(home) == "number") then
homeCrowdDefault = home
else
homeCrowdDefault = home[math.random(#home)]
end

if (type(away) == "number") then
awayCrowdDefault = away
else
awayCrowdDefault = away[math.random(#away)]
end

end


function setTeamCrowdSize(team,home,away)

if (type(home) == "number") then
homeCrowdTeam[team] = home
else
homeCrowdTeam[team] = home[math.random(#home)]
end

if (type(away) == "number") then
awayCrowdTeam[team] = away
else
awayCrowdTeam[team] = away[math.random(#away)]
end

end


function setTournamentCrowdSize(tourn,home,away)

if (type(home) == "number") then
homeCrowdTournament[tourn] = home
else
homeCrowdTournament[tourn] = home[math.random(#home)]
end

if (type(away) == "number") then
awayCrowdTournament[tourn] = away
else
awayCrowdTournament[tourn] = away[math.random(#away)]
end

end


function setGameCrowdSize(hometeam,awayteam,home,away)
if (homeCrowdGame[hometeam] == nil) then
homeCrowdGame[hometeam] = {}
end

if (awayCrowdGame[hometeam] == nil) then
awayCrowdGame[hometeam] = {}
end

if (type(home) == "number") then
homeCrowdGame[hometeam][awayteam] = home
else
homeCrowdGame[hometeam][awayteam] = home[math.random(#home)]
end

if (type(away) == "number") then
awayCrowdGame[hometeam][awayteam] = away
else
awayCrowdGame[hometeam][awayteam] = away[math.random(#away)]
end

end


function setTournamentTeamCrowdSize(team,tourn,home,away)
if (homeCrowdTournamentTeam[team] == nil) then
homeCrowdTournamentTeam[team] = {}
end

if (awayCrowdTournamentTeam[team] == nil) then
awayCrowdTournamentTeam[team] = {}
end

if (type(home) == "number") then
homeCrowdTournamentTeam[team][tourn] = home
else
homeCrowdTournamentTeam[team][tourn] = home[math.random(#home)]
end

if (type(away) == "number") then
awayCrowdTournamentTeam[team][tourn] = away
else
awayCrowdTournamentTeam[team][tourn] = away[math.random(#away)]
end

end


function setTournamentGameCrowdSize(hometeam,awayteam,tourn,home,away)
if (homeCrowdTournamentGame[hometeam] == nil) then
homeCrowdTournamentGame[hometeam] = {}
end

if (awayCrowdTournamentGame[hometeam] == nil) then
awayCrowdTournamentGame[hometeam] = {}
end

if (homeCrowdTournamentGame[hometeam][awayteam] == nil) then
homeCrowdTournamentGame[hometeam][awayteam] = {}
end

if (awayCrowdTournamentGame[hometeam][awayteam] == nil) then
awayCrowdTournamentGame[hometeam][awayteam] = {}
end

if (type(home) == "number") then
homeCrowdTournamentGame[hometeam][awayteam][tourn] = home
else
homeCrowdTournamentGame[hometeam][awayteam][tourn] = home[math.random(#home)]
end

if (type(away) == "number") then
awayCrowdTournamentGame[hometeam][awayteam][tourn] = away
else
awayCrowdTournamentGame[hometeam][awayteam][tourn] = away[math.random(#away)]
end

end








function setTournamentFinalCrowdSize(tourn,home,away)

if (type(home) == "number") then
homeCrowdTournamentFinal[tourn] = home
else
homeCrowdTournamentFinal[tourn] = home[math.random(#home)]
end

if (type(away) == "number") then
awayCrowdTournamentFinal[tourn] = away
else
awayCrowdTournamentFinal[tourn] = away[math.random(#away)]
end

end



function setLeagueVersusLeagueCrowdSize(hometeamleague,awayteamleague,home,away)
if (homeCrowdLeagueVersusLeague[hometeamleague] == nil) then
homeCrowdLeagueVersusLeague[hometeamleague] = {}
end

if (awayCrowdLeagueVersusLeague[hometeamleague] == nil) then
awayCrowdLeagueVersusLeague[hometeamleague] = {}
end

if (type(home) == "number") then
homeCrowdLeagueVersusLeague[hometeamleague][awayteamleague] = home
else
homeCrowdLeagueVersusLeague[hometeamleague][awayteamleague] = home[math.random(#home)]
end

if (type(away) == "number") then
awayCrowdLeagueVersusLeague[hometeamleague][awayteamleague] = away
else
awayCrowdLeagueVersusLeague[hometeamleague][awayteamleague] = away[math.random(#away)]
end

end



function setTournamentLeagueVersusLeagueCrowdSize(hometeam,awayteam,tourn,home,away)
if (homeCrowdTournamentLeagueVersusLeague[hometeam] == nil) then
homeCrowdTournamentLeagueVersusLeague[hometeam] = {}
end

if (awayCrowdTournamentLeagueVersusLeague[hometeam] == nil) then
awayCrowdTournamentLeagueVersusLeague[hometeam] = {}
end

if (homeCrowdTournamentLeagueVersusLeague[hometeam][awayteam] == nil) then
homeCrowdTournamentLeagueVersusLeague[hometeam][awayteam] = {}
end

if (awayCrowdTournamentLeagueVersusLeague[hometeam][awayteam] == nil) then
awayCrowdTournamentLeagueVersusLeague[hometeam][awayteam] = {}
end

if (type(home) == "number") then
homeCrowdTournamentLeagueVersusLeague[hometeam][awayteam][tourn] = home
else
homeCrowdTournamentLeagueVersusLeague[hometeam][awayteam][tourn] = home[math.random(#home)]
end

if (type(away) == "number") then
awayCrowdTournamentLeagueVersusLeague[hometeam][awayteam][tourn] = away
else
awayCrowdTournamentLeagueVersusLeague[hometeam][awayteam][tourn] = away[math.random(#away)]
end

end





function setTeamVersusLeagueCrowdSize(hometeam,awayteam,home,away)
if (homeCrowdTeamVersusLeague[hometeam] == nil) then
homeCrowdTeamVersusLeague[hometeam] = {}
end

if (awayCrowdTeamVersusLeague[hometeam] == nil) then
awayCrowdTeamVersusLeague[hometeam] = {}
end

if (type(home) == "number") then
homeCrowdTeamVersusLeague[hometeam][awayteam] = home
else
homeCrowdTeamVersusLeague[hometeam][awayteam] = home[math.random(#home)]
end

if (type(away) == "number") then
awayCrowdTeamVersusLeague[hometeam][awayteam] = away
else
awayCrowdTeamVersusLeague[hometeam][awayteam] = away[math.random(#away)]
end

end



function setTournamentTeamVersusLeagueCrowdSize(hometeam,awayteam,tourn,home,away)
if (homeCrowdTournamentTeamVersusLeague[hometeam] == nil) then
homeCrowdTournamentTeamVersusLeague[hometeam] = {}
end

if (awayCrowdTournamentTeamVersusLeague[hometeam] == nil) then
awayCrowdTournamentTeamVersusLeague[hometeam] = {}
end

if (homeCrowdTournamentTeamVersusLeague[hometeam][awayteam] == nil) then
homeCrowdTournamentTeamVersusLeague[hometeam][awayteam] = {}
end

if (awayCrowdTournamentTeamVersusLeague[hometeam][awayteam] == nil) then
awayCrowdTournamentTeamVersusLeague[hometeam][awayteam] = {}
end

if (type(home) == "number") then
homeCrowdTournamentTeamVersusLeague[hometeam][awayteam][tourn] = home
else
homeCrowdTournamentTeamVersusLeague[hometeam][awayteam][tourn] = home[math.random(#home)]
end

if (type(away) == "number") then
awayCrowdTournamentTeamVersusLeague[hometeam][awayteam][tourn] = away
else
awayCrowdTournamentTeamVersusLeague[hometeam][awayteam][tourn] = away[math.random(#away)]
end

end






function getHomeCrowdSize(hometeam,awayteam,tourn,hometeamleague,awayteamleague,stad,dist)

--tournament final
if (getTournamentFinal(tourn,stad,dist)) then
if (homeCrowdTournamentFinal[tourn] ~= nil) then
return homeCrowdTournamentFinal[tourn]
end
end

--tournament match
if (homeCrowdTournamentGame[hometeam] ~= nil) then
if (homeCrowdTournamentGame[hometeam][awayteam] ~= nil) then
if (homeCrowdTournamentGame[hometeam][awayteam][tourn] ~= nil) then
return homeCrowdTournamentGame[hometeam][awayteam][tourn]
end
end
end

--tournament team v league
if (homeCrowdTournamentTeamVersusLeague[hometeam] ~= nil) then
if (homeCrowdTournamentTeamVersusLeague[hometeam][awayteamleague] ~= nil) then
if (homeCrowdTournamentTeamVersusLeague[hometeam][awayteamleague][tourn] ~= nil) then
return homeCrowdTournamentTeamVersusLeague[hometeam][awayteamleague][tourn]
end
end
end

--tournament team
if (homeCrowdTournamentTeam[hometeam] ~= nil) then
if (homeCrowdTournamentTeam[hometeam][tourn] ~= nil) then
return homeCrowdTournamentTeam[hometeam][tourn]
end
end

--match
if (homeCrowdGame[hometeam] ~= nil) then
if (homeCrowdGame[hometeam][awayteam] ~= nil) then
return homeCrowdGame[hometeam][awayteam]
end
end

--team v league
if (homeCrowdTeamVersusLeague[hometeam] ~= nil) then
if (homeCrowdTeamVersusLeague[hometeam][awayteamleague] ~= nil) then
return homeCrowdTeamVersusLeague[hometeam][awayteamleague]
end
end

--team
if (homeCrowdTeam[hometeam] ~= nil) then
return homeCrowdTeam[hometeam]
end

--tournament league v league
if (homeCrowdTournamentLeagueVersusLeague[hometeamleague] ~= nil) then
if (homeCrowdTournamentLeagueVersusLeague[hometeamleague][awayteamleague] ~= nil) then
if (homeCrowdTournamentLeagueVersusLeague[hometeamleague][awayteamleague][tourn] ~= nil) then
return homeCrowdTournamentLeagueVersusLeague[hometeamleague][awayteamleague][tourn]
end
end
end

--tournament
if (homeCrowdTournament[tourn] ~= nil) then
return homeCrowdTournament[tourn]
end

--league v league
if (homeCrowdLeagueVersusLeague[hometeamleague] ~= nil) then
if (homeCrowdLeagueVersusLeague[hometeamleague][awayteamleague] ~= nil) then
return homeCrowdLeagueVersusLeague[hometeamleague][awayteamleague]
end
end

if (homeCrowdTournament[hometeamleague] ~= nil) then
return homeCrowdTournament[hometeamleague]
end

return homeCrowdDefault
end



function getAwayCrowdSize(hometeam,awayteam,tourn,hometeamleague,awayteamleague,stad,dist)

--tournament final
if (getTournamentFinal(tourn,stad,dist)) then
if (awayCrowdTournamentFinal[tourn] ~= nil) then
return awayCrowdTournamentFinal[tourn]
end
end

--tournament match
if (awayCrowdTournamentGame[hometeam] ~= nil) then
if (awayCrowdTournamentGame[hometeam][awayteam] ~= nil) then
if (awayCrowdTournamentGame[hometeam][awayteam][tourn] ~= nil) then
return awayCrowdTournamentGame[hometeam][awayteam][tourn]
end
end
end

--tournament team v league
if (awayCrowdTournamentTeamVersusLeague[hometeam] ~= nil) then
if (awayCrowdTournamentTeamVersusLeague[hometeam][awayteamleague] ~= nil) then
if (awayCrowdTournamentTeamVersusLeague[hometeam][awayteamleague][tourn] ~= nil) then
return awayCrowdTournamentTeamVersusLeague[hometeam][awayteamleague][tourn]
end
end
end

--tournament team
if (awayCrowdTournamentTeam[awayteam] ~= nil) then
if (awayCrowdTournamentTeam[awayteam][tourn] ~= nil) then
return awayCrowdTournamentTeam[awayteam][tourn]
end
end

--match
if (awayCrowdGame[hometeam] ~= nil) then
if (awayCrowdGame[hometeam][awayteam] ~= nil) then
return awayCrowdGame[hometeam][awayteam]
end
end

--team v league
if (awayCrowdTeamVersusLeague[hometeam] ~= nil) then
if (awayCrowdTeamVersusLeague[hometeam][awayteamleague] ~= nil) then
return awayCrowdTeamVersusLeague[hometeam][awayteamleague]
end
end

--team
if (awayCrowdTeam[awayteam] ~= nil) then
return awayCrowdTeam[awayteam]
end

--tournament league v league
if (awayCrowdTournamentLeagueVersusLeague[hometeamleague] ~= nil) then
if (awayCrowdTournamentLeagueVersusLeague[hometeamleague][awayteamleague] ~= nil) then
if (awayCrowdTournamentLeagueVersusLeague[hometeamleague][awayteamleague][tourn] ~= nil) then
return awayCrowdTournamentLeagueVersusLeague[hometeamleague][awayteamleague][tourn]
end
end
end

--tournament
if (awayCrowdTournament[tourn] ~= nil) then
return awayCrowdTournament[tourn]
end

--league v league
if (awayCrowdLeagueVersusLeague[hometeamleague] ~= nil) then
if (awayCrowdLeagueVersusLeague[hometeamleague][awayteamleague] ~= nil) then
return awayCrowdLeagueVersusLeague[hometeamleague][awayteamleague]
end
end

if (awayCrowdTournament[awayteamleague] ~= nil) then
return awayCrowdTournament[awayteamleague]
end

return awayCrowdDefault
end


crowdLODAdjust = 0

function setCrowdLOD(lod)
crowdLODAdjust = lod
end



teamSeatsRemoved = {}
stadiumSeatsRemoved = {}

function removeSeatsTeam(team)
teamSeatsRemoved[team] = 1
end

function removeSeatsStadium(stad)
stadiumSeatsRemoved[stad] = 1
end


function getRemoveSeats(team,stad)
if (stadiumSeatsRemoved[stad] == 1) then
return true
end

if (teamSeatsRemoved[team] == 1) then
return true
end

return false
end



function GetRMChairMod(idx)
	local chair = ""
	
	if (getRemoveSeats(db.crowd[idx].homeKitTeamID,db.crowd[idx].stadiumID)) then
	chair = chair.."data/sceneassets/crowdchair/crowdchair_empty.rx3;"
	end
	
	chair = chair.."data/sceneassets/crowdchair/specificchair_"..db.crowd[idx].homeTeamIDseat.."_"..db.crowd[idx].stadiumID..".rx3;"
	chair = chair.."data/sceneassets/crowdchair/specificchair_0_"..db.crowd[idx].stadiumID..".rx3;"
	chair = chair.."data/sceneassets/crowdchair/specificchair_"..db.crowd[idx].homeTeamIDseat.."_0.rx3;"
	chair = chair.."data/sceneassets/crowdchair/specificchair_0_0.rx3;"

	return chair
end


genericStadium = {}

function identifyGenericStadium(id)
genericStadium[id] = 1
end

function getIsGenericStadium(id)
if (genericStadium[id] ~= nil) then
return true
end
return false
end




--Revolution Mod 16 V1.3.5
--Edited by scouser09
