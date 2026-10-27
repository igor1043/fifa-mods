$ErrorActionPreference = 'Stop'
$path = 'U:\fifa 16\ModCarrerMode\mods\enabled.txt'
$bytes = [System.IO.File]::ReadAllBytes($path)
$text = [System.Text.Encoding]::UTF8.GetString($bytes)
$updated = [regex]::Replace($text, '(?m)^[ \t]*stadium_pyrotechnics\\stadium_pyrotechnics\.dll[ \t]*\r?\n?', '')
if ($updated -ne $text) {
    [System.IO.File]::WriteAllBytes($path + '.before_disable_pyro.bak', $bytes)
    [System.IO.File]::WriteAllText($path, $updated, [System.Text.UTF8Encoding]::new($false))
}
Write-Host 'Modulo de fogos desativado. Feche e abra o FIFA para aplicar.'
