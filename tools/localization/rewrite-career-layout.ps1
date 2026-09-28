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
    'COMPETICAO (ABA)' = 'FIFA_MODS_CM_COMPETITION_TAB'
    'COMPETICOES DISPUTADAS' = 'FIFA_MODS_CM_COMPETITIONS_PLAYED'
    'DADOS DA PARTIDA' = 'CM_PA_Match Info'
    'DADOS DO CLUBE' = 'FIFA_MODS_CM_CLUB_DATA'
    'NENHUM DADO REGISTRADO AINDA' = 'FIFA_MODS_CM_NO_DATA_RECORDED'
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
    $panel.NAME = 'FIFA_MODS_CM_COMPETITION_TAB'
}

foreach ($field in $xml.SelectNodes('//data[@ID="MYTEAM_NEXT_STADIUM_CAPACITY_LABEL"]')) {
    $field.PARAM = 'FIFA_MODS_CM_ESTIMATED_ATTENDANCE'
    $field.TRANSLATE = 'TRUE'
    $field.WIDTH = '320'
}

$nextMatchLayout = [ordered]@{
    'MYTEAM_NEXT_HORIZONTAL_DIVIDER' = @{ Y = '302' }
    'MYTEAM_NEXT_INFO_TITLE' = @{ Y = '314' }
    'MYTEAM_NEXT_DATE_LABEL' = @{ Y = '350' }
    'MYTEAM_NEXT_DATE' = @{ Y = '350'; X = '110' }
    'MYTEAM_NEXT_TIME_LABEL' = @{ Y = '382' }
    'MYTEAM_NEXT_TIME' = @{ Y = '382'; X = '110' }
}

foreach ($entry in $nextMatchLayout.GetEnumerator()) {
    $field = $xml.SelectSingleNode("//data[@ID='$($entry.Key)']")
    if (-not $field) {
        throw "Missing next-match layout field: $($entry.Key)"
    }
    foreach ($attribute in $entry.Value.GetEnumerator()) {
        $field.SetAttribute($attribute.Key, [string]$attribute.Value)
    }
}

$capacityLabel = $xml.SelectSingleNode('//data[@ID="MYTEAM_NEXT_STADIUM_CAPACITY_LABEL"]')
if (-not $capacityLabel) {
    throw 'Missing next-match capacity label'
}
$capacityLabel.PARAM = 'Capacity'
$capacityLabel.TRANSLATE = 'TRUE'
$capacityLabel.WIDTH = '320'

$capacityValue = $xml.SelectSingleNode('//data[@ID="MYTEAM_NEXT_STADIUM_CAPACITY"]')
if (-not $capacityValue) {
    throw 'Missing next-match capacity value'
}
$capacityValue.X = '292'
$capacityValue.Y = '552'
$capacityValue.FORMAT = 'SM||left'

$attendanceLabel = $xml.SelectSingleNode('//data[@ID="MYTEAM_NEXT_STADIUM_ATTENDANCE_LABEL"]')
if (-not $attendanceLabel) {
    $attendanceLabel = $xml.CreateElement('data')
    $attendanceLabel.SetAttribute('ID', 'MYTEAM_NEXT_STADIUM_ATTENDANCE_LABEL')
    $attendanceLabel.SetAttribute('TYPE', 'text')
    [void]$capacityValue.ParentNode.InsertAfter($attendanceLabel, $capacityValue)
}
$attendanceLabel.SetAttribute('FORMAT', 'SS||left')
$attendanceLabel.SetAttribute('TRANSLATE', 'TRUE')
$attendanceLabel.SetAttribute('HEIGHT', '18')
$attendanceLabel.SetAttribute('PARAM', 'FIFA_MODS_CM_ESTIMATED_ATTENDANCE')
$attendanceLabel.SetAttribute('WIDTH', '320')
$attendanceLabel.SetAttribute('VISIBLE', 'FALSE')
$attendanceLabel.SetAttribute('Y', '580')
$attendanceLabel.SetAttribute('X', '292')

$attendanceValue = $xml.SelectSingleNode('//data[@ID="MYTEAM_NEXT_STADIUM_ATTENDANCE"]')
if (-not $attendanceValue) {
    $attendanceValue = $xml.CreateElement('data')
    $attendanceValue.SetAttribute('ID', 'MYTEAM_NEXT_STADIUM_ATTENDANCE')
    $attendanceValue.SetAttribute('TYPE', 'text')
    [void]$attendanceLabel.ParentNode.InsertAfter($attendanceValue, $attendanceLabel)
}
$attendanceValue.SetAttribute('FORMAT', 'SM||left')
$attendanceValue.SetAttribute('TRANSLATE', 'FALSE')
$attendanceValue.SetAttribute('HEIGHT', '24')
$attendanceValue.SetAttribute('WIDTH', '220')
$attendanceValue.SetAttribute('VISIBLE', 'FALSE')
$attendanceValue.SetAttribute('Y', '602')
$attendanceValue.SetAttribute('X', '292')


$emptyStatCards = @(
    @{ Background = 'MYTEAM_GOALS_BG'; Empty = 'MYTEAM_GOALS_EMPTY' },
    @{ Background = 'MYTEAM_ASSISTS_BG'; Empty = 'MYTEAM_ASSISTS_EMPTY' },
    @{ Background = 'MYTEAM_MINUTES_BG'; Empty = 'MYTEAM_MINUTES_EMPTY' },
    @{ Background = 'MYTEAM_YELLOW_BG'; Empty = 'MYTEAM_YELLOW_EMPTY' },
    @{ Background = 'MYTEAM_RED_BG'; Empty = 'MYTEAM_RED_EMPTY' }
)

foreach ($card in $emptyStatCards) {
    if ($xml.SelectSingleNode("//data[@ID='$($card.Empty)']")) {
        continue
    }
    $background = $xml.SelectSingleNode("//data[@ID='$($card.Background)']")
    if (-not $background) {
        throw "Missing statistics-card background: $($card.Background)"
    }
    $empty = $xml.CreateElement('data')
    $empty.SetAttribute('FORMAT', 'SM||center')
    $empty.SetAttribute('TRANSLATE', 'TRUE')
    $empty.SetAttribute('HEIGHT', '28')
    $empty.SetAttribute('PARAM', 'FIFA_MODS_CM_NO_DATA_RECORDED')
    $empty.SetAttribute('WIDTH', '516')
    $empty.SetAttribute('TYPE', 'text')
    $empty.SetAttribute('VISIBLE', 'FALSE')
    $empty.SetAttribute('ID', $card.Empty)
    $empty.SetAttribute('Y', '166')
    $empty.SetAttribute('X', '18')
    [void]$background.ParentNode.InsertAfter($empty, $background)
}

$settings = New-Object System.Xml.XmlWriterSettings
$settings.Encoding = New-Object System.Text.UTF8Encoding($false)
$settings.Indent = $false
$settings.OmitXmlDeclaration = $false
$writer = [System.Xml.XmlWriter]::Create($Path, $settings)
$xml.Save($writer)
$writer.Dispose()
