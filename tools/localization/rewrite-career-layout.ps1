param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$map = [ordered]@{
    'ABRIR ELENCO' = 'FIFA_MODS_CM_OPEN_SQUAD'
    'APROVEITAMENTO GERAL' = 'FIFA_MODS_CM_OVERALL_PERFORMANCE'
    'ARTILHARIA' = 'Top Scorers'
    'ASSIST' = 'TXT_ACCOMP_NAME_ASSISTS'
    'ASSISTENCIAS' = 'TXT_ACCOMP_NAME_ASSISTS'
    'ATACANTES' = 'FUT_FORWARDS'
    'CAPACIDADE' = 'Capacity'
    'CARTOES AMARELOS' = 'TXT_ACCOMP_NAME_YELLOW_CARDS'
    'CARTOES VERM.' = 'TXT_ACCOMP_NAME_RED_CARDS'
    'CASA' = 'CM_PA_VenueHome'
    'CLUBE' = 'CM_Career Summary_Stats_1'
    'COMPETICAO' = 'CM_Competition'
    'COMPETICOES DISPUTADAS' = 'FIFA_MODS_CM_COMPETITIONS_PLAYED'
    'DADOS DA PARTIDA' = 'CM_PA_Match Info'
    'DADOS DO CLUBE' = 'FIFA_MODS_CM_CLUB_DATA'
    'DATA:' = 'SCRAPBOOK_DATE'
    'date' = 'Date'
    'DEFESAS' = 'FUT_DEFENDERS'
    'DERROTAS' = 'ProfileStat_6'
    'DIVISAO POR POSICAO' = 'FIFA_MODS_CM_POSITION_BREAKDOWN'
    'ELENCO' = 'Squad'
    'EMPATES' = 'ProfileStat_5'
    'ESTADIO' = 'Stadium_mixedcase'
    'GOLS' = 'Goals'
    'GOLS E ASSISTENCIAS POR COMPETICAO' = 'FIFA_MODS_CM_GOALS_ASSISTS_BY_COMPETITION'
    'GF     GA     SG' = 'FIFA_MODS_CM_GOAL_DIFFERENCE_HEADERS'
    'GOLEIRO' = 'FUT_GOALKEEPER'
    'GOLEIROS' = 'CLUBS_SEARCH_GK'
    'HORA:' = 'Time'
    'IDA' = 'CM_KO_LEG_LABEL'
    'IDADE MEDIA' = 'FIFA_MODS_CM_AVERAGE_AGE'
    'JOGADORES' = 'CM_Players'
    'JOGADORES LESIONADOS' = 'FIFA_MODS_CM_INJURED_PLAYERS'
    'JOGADORES MAIS VELHOS' = 'FIFA_MODS_CM_OLDEST_PLAYERS'
    'MANDANTE' = 'CM_PA_VenueHome'
    'MEDIA GERAL' = 'CM_AverageRating'
    'MEIAS' = 'Midfielders'
    'MINUTOS JOGADOS' = 'ProfileStat_122'
    'PONTUACAO GERAL' = 'OverallRating'
    'PROXIMA PARTIDA' = 'CM_NextMatchCaps'
    'PTS' = 'TXT_POINTS'
    'REPUTACAO' = 'CM_ManagerRep'
    'RETORNO' = 'FIFA_MODS_CM_RETURN'
    'RETROSPECTO DO CLUBE' = 'CM_Career Summary_Stats_20'
    'SALA DE TROFEUS' = 'TrophyRoom'
    'SEM PROXIMA PARTIDA' = 'CM_PA_NoMatch'
    'V     E     D' = 'FIFA_MODS_CM_WDL_HEADERS'
    'VITORIAS' = 'ProfileStat_4'
    'VISITANTE' = 'CM_PA_VenueAway'
    'VS' = 'TXT_VS_LARGE'
}

[xml]$xml = Get-Content -LiteralPath $Path -Raw
foreach ($node in $xml.SelectNodes('//data')) {
    $param = [string]$node.PARAM
    if ($map.Contains($param)) {
        $node.PARAM = $map[$param]
        $node.TRANSLATE = 'TRUE'
    }
}

foreach ($panel in $xml.SelectNodes('//panel_set/panel[@PANEL_ID="5"]')) {
    $panel.NAME = 'CM_Competition'
}

foreach ($field in $xml.SelectNodes('//data[@ID="MYTEAM_NEXT_STADIUM_CAPACITY_LABEL"]')) {
    $field.PARAM = 'Attendance'
    $field.TRANSLATE = 'TRUE'
}

$settings = New-Object System.Xml.XmlWriterSettings
$settings.Encoding = New-Object System.Text.UTF8Encoding($false)
$settings.Indent = $false
$settings.OmitXmlDeclaration = $false
$writer = [System.Xml.XmlWriter]::Create($Path, $settings)
$xml.Save($writer)
$writer.Dispose()
