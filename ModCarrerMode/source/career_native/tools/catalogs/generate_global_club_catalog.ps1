[CmdletBinding()]
param(
    [string]$DatabaseDirectory = 'C:\Users\igorv\OneDrive\Área de Trabalho\estudos fifa 16\02_ENGENHARIA_REVERSA\engenharia_carreira_20260906\ir\db\loose\data\db\fifa_ng_db.db',
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\..\src\catalogs\global_clubs.inc')
)

$ErrorActionPreference = 'Stop'
$teamsPath = Join-Path $DatabaseDirectory 'teams.csv'
$linksPath = Join-Path $DatabaseDirectory 'leagueteamlinks.csv'
foreach ($path in @($teamsPath, $linksPath)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required FIFA database export missing: $path" }
}

$teams = Import-Csv -LiteralPath $teamsPath -Encoding UTF8
$links = Import-Csv -LiteralPath $linksPath -Encoding UTF8
$linkByTeam = @{}
foreach ($link in $links) {
    $teamId = 0
    $leagueId = 0
    if (-not [int]::TryParse($link.teamid, [ref]$teamId) -or $teamId -le 0) { continue }
    if (-not [int]::TryParse($link.leagueid, [ref]$leagueId) -or $leagueId -le 0 -or $leagueId -eq 78) { continue }
    if (-not $linkByTeam.ContainsKey($teamId)) { $linkByTeam[$teamId] = [System.Collections.Generic.List[int]]::new() }
    $linkByTeam[$teamId].Add($leagueId)
}

$catalog = [System.Collections.Generic.List[object]]::new()
foreach ($team in $teams) {
    $teamId = 0
    if (-not [int]::TryParse($team.teamid, [ref]$teamId) -or $teamId -le 0) { continue }
    if ($team.teamname -in @('Classic XI', 'MLS All Stars') -or -not $linkByTeam.ContainsKey($teamId)) { continue }

    $domestic = 0
    $international = 0
    $overall = 50
    [void][int]::TryParse($team.domesticprestige, [ref]$domestic)
    [void][int]::TryParse($team.internationalprestige, [ref]$international)
    [void][int]::TryParse($team.overallrating, [ref]$overall)
    $overallValid = $overall -gt 0
    if (-not $overallValid) { $overall = 50 }
    $leagueId = ($linkByTeam[$teamId] | Sort-Object | Select-Object -First 1)
    $catalog.Add([pscustomobject]@{
        TeamId = $teamId
        LeagueId = [int]$leagueId
        Domestic = [Math]::Clamp($domestic, 0, 20)
        International = [Math]::Clamp($international, 0, 20)
        Overall = [Math]::Clamp($overall, 0, 100)
        OverallValid = $overallValid
    })
}

$leagueAverages = @{}
foreach ($group in ($catalog | Group-Object LeagueId)) {
    $knownRatings = @($group.Group | Where-Object OverallValid)
    $average = 50
    if ($knownRatings.Count -gt 0) {
        $average = [int][Math]::Round(($knownRatings | Measure-Object Overall -Average).Average, 0, [MidpointRounding]::AwayFromZero)
    }
    $leagueAverages[[int]$group.Name] = [Math]::Clamp($average, 0, 100)
}

$sorted = @($catalog | Sort-Object TeamId)
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('/* Generated from the read-only FIFA 16 teams/leagueteamlinks CSV exports. */')
$lines.Add('static const GlobalClubBase g_global_club_catalog[] = {')
foreach ($item in $sorted) {
    $competitionStrength = $leagueAverages[$item.LeagueId]
    $lines.Add(('    {{{0}, {1}, {2}, {3}, {4}}},' -f $item.TeamId, $item.Domestic, $item.International, $item.Overall, $competitionStrength))
}
$lines.Add('};')
$outputDirectory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
[System.IO.File]::WriteAllLines($OutputPath, $lines, [System.Text.UTF8Encoding]::new($false))

if ($sorted.Count -ne 1305) { throw "Expected 1305 linked club records after excluding national/special teams; generated $($sorted.Count)." }
Write-Output "Generated $($sorted.Count) unique club metadata records: $OutputPath"
