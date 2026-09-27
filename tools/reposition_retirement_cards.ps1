param(
    [Parameter(Mandatory = $true)]
    [string[]] $Path
)

function Set-XmlAttribute {
    param(
        [System.Xml.XmlElement] $Element,
        [string] $Name,
        [string] $Value
    )
    $Element.SetAttribute($Name, $Value)
}

function Add-XmlElement {
    param(
        [System.Xml.XmlDocument] $Document,
        [System.Xml.XmlElement] $Parent,
        [string] $Name,
        [hashtable] $Attributes
    )
    $element = $Document.CreateElement($Name)
    foreach ($key in $Attributes.Keys) {
        Set-XmlAttribute -Element $element -Name $key -Value ([string]$Attributes[$key])
    }
    [void]$Parent.AppendChild($element)
    return $element
}

function Add-RetirementCard {
    param(
        [System.Xml.XmlDocument] $Document,
        [System.Xml.XmlElement] $SettingsTile,
        [string] $ElementName,
        [string] $Id,
        [string] $Destination,
        [string] $Mode,
        [string] $Title,
        [string] $Description
    )
    $subtile = Add-XmlElement -Document $Document -Parent $SettingsTile -Name $ElementName -Attributes @{
        SUBTILE_TYPE = 'TILE'
        DESTINATION = $Destination
        FG_PATH = ''
        PARAM = $Mode
        NAME = ''
        ID = $Id
    }
    [void](Add-XmlElement -Document $Document -Parent $subtile -Name 'data' -Attributes @{
        ID = 'RETIREMENT_BG'
        TYPE = 'panel'
        PARAM = 'STYLE_SEVEN'
        TRANSLATE = 'FALSE'
        WIDTH = '418'
        HEIGHT = '204'
        X = '0'
        Y = '0'
    })
    [void](Add-XmlElement -Document $Document -Parent $subtile -Name 'data' -Attributes @{
        ID = 'RETIREMENT_ACCENT'
        TYPE = 'rectangle'
        PARAM = '0x2DB7C8'
        WIDTH = '8'
        HEIGHT = '158'
        X = '0'
        Y = '25'
    })
    [void](Add-XmlElement -Document $Document -Parent $subtile -Name 'data' -Attributes @{
        ID = 'RETIREMENT_TITLE'
        TYPE = 'title'
        FORMAT = 'SS||center'
        PARAM = $Title
        TRANSLATE = 'TRUE'
        WIDTH = '370'
        HEIGHT = '34'
        X = '22'
        Y = '85'
    })
}

foreach ($file in $Path) {
    $resolved = (Resolve-Path -LiteralPath $file -ErrorAction Stop).Path
    $document = [System.Xml.XmlDocument]::new()
    $document.PreserveWhitespace = $false
    $document.Load($resolved)

    $central = $document.SelectSingleNode('//panel_0')
    $centralTile = $central.SelectSingleNode("./tile[tileid/@tileid='725']")
    if (-not $centralTile) { throw "NEXT_MATCH_CENTRAL não encontrado em $resolved" }
    foreach ($subtile in @($centralTile.SelectNodes('./subtile1|./subtile2'))) {
        [void]$centralTile.RemoveChild($subtile)
    }
    Set-XmlAttribute -Element $centralTile.SelectSingleNode('./number_of_subtiles') -Name 'LENGTH' -Value '0'

    $office = $document.SelectSingleNode('//panel_3')
    $settingsTile = $office.SelectSingleNode("./tile[tileid/@tileid='384']")
    if (-not $settingsTile) { throw "SETTINGS não encontrado em $resolved" }
    Set-XmlAttribute -Element $settingsTile.SelectSingleNode('./settings') -Name 'FILE_PATH' -Value 'TILE_NESTED'
    $main = $settingsTile.SelectSingleNode('./main_tile')
    Set-XmlAttribute -Element $main -Name 'SUBTILE_TYPE' -Value 'TILE'
    Set-XmlAttribute -Element $main -Name 'ID' -Value '384'
    Set-XmlAttribute -Element $settingsTile.SelectSingleNode('./number_of_subtiles') -Name 'LENGTH' -Value '2'
    foreach ($old in @($settingsTile.SelectNodes('./subtile|./subtile1|./subtile2|./subtile3|./subtile4'))) {
        [void]$settingsTile.RemoveChild($old)
    }
    Add-RetirementCard -Document $document -SettingsTile $settingsTile -ElementName 'subtile1' -Id '385' `
        -Destination 'RetirementRemove' -Mode 'remove_retirement' `
        -Title 'FIFA_MODS_RETIREMENT' `
        -Description ''
    Add-RetirementCard -Document $document -SettingsTile $settingsTile -ElementName 'subtile2' -Id '386' `
        -Destination 'RetirementResetAge' -Mode 'remove_and_rejuvenate' `
        -Title 'FIFA_MODS_RETIREMENT_AGE' `
        -Description ''

    $xmlSettings = [System.Xml.XmlWriterSettings]::new()
    $xmlSettings.Encoding = [System.Text.UTF8Encoding]::new($false)
    $xmlSettings.Indent = $false
    $xmlSettings.NewLineHandling = [System.Xml.NewLineHandling]::None
    $xmlSettings.OmitXmlDeclaration = $false
    $stream = [System.IO.MemoryStream]::new()
    $writer = [System.Xml.XmlWriter]::Create($stream, $xmlSettings)
    $document.Save($writer)
    $writer.Close()
    [System.IO.File]::WriteAllBytes($resolved, $stream.ToArray())
    $stream.Dispose()
}
