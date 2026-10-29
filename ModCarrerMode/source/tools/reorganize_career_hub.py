"""Reorganize the installed career hub without changing its native callbacks.

Pure XML transformation. The caller stages, validates and backs up the result
before installing it. Never reads or writes a career save, NAV, DB or DLL.
"""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET

XML = 'data/ui/layout/careermanagerhubcfg.xml'
OVERLAY = 'ModCarrerMode/source/native_mods/career_overlay/layout/careermanagerhubcfg.xml'


def tile(panel, name):
    found = [t for t in panel.findall('tile') if t.find('tileid').get('NAME') == name]
    if len(found) != 1:
        raise ValueError(f'Expected one {name}, found {len(found)}')
    return found[0]


def pages(card):
    """Normalize root-level main-page data and nested slides to the same shape."""
    main = deepcopy(card.find('main_tile'))
    main.extend(deepcopy(n) for n in card.findall('data'))
    return [main] + [deepcopy(n) for n in card if n.tag.startswith('subtile')]


def page(pages_, destination=None, ident=None):
    found = [n for n in pages_ if (destination is None or n.get('DESTINATION') == destination)
             and (ident is None or n.get('ID') == ident)]
    if len(found) != 1:
        raise ValueError(f'Expected one page for {destination or ident}, found {len(found)}')
    return found[0]


def arrange(card, content):
    for node in list(card):
        if node.tag in ('main_tile', 'data', 'number_of_subtiles') or node.tag.startswith('subtile'):
            card.remove(node)
    for i, source in enumerate(content):
        node = deepcopy(source)
        node.tag = 'main_tile' if i == 0 else f'subtile{i}'
        node.set('SUBTILE_TYPE', node.get('SUBTILE_TYPE', 'TILE'))
        if i == 0:
            data = list(node.findall('data'))
            for field in data:
                node.remove(field)
            card.append(node)
            ET.SubElement(card, 'number_of_subtiles', LENGTH=str(len(content)-1))
            card.extend(data)
        else:
            card.append(node)
    settings = card.find('settings')
    settings.set('FILE_PATH', 'TILE_NESTED' if len(content) > 1 else 'TILE')
    settings.set('ENABLE_CYCLING', 'TRUE' if len(content) > 1 else 'FALSE')


def box(card, x, y, width, height):
    card.find('settings').attrib.update(X=str(x), Y=str(y), WIDTH=str(width), HEIGHT=str(height))


def destinations(root):
    return Counter(n.get('DESTINATION') for n in root.iter() if n.get('DESTINATION'))


def organized(root):
    return (any(n.get('DESTINATION') == 'Server16EnterManagerMarket'
                for n in root.find('panel_2').iter())
            and any(n.get('DESTINATION') == 'Server16EnterDressingRoom'
                    for n in root.find('panel_7').iter())
            and tile(root.find('panel_3'), 'REQUEST_FUNDS').find('main_tile').get('DESTINATION')
                    == 'Server16EnterClubFinance')


def compact_player_actions(content):
    for slide in content:
        # The old foreground art was 418 px tall. Use existing background icons
        # for a 204 px card; callbacks, native disabled-state data and IDs survive.
        slide.set('FG_PATH', '')
        slide.set('BG_ICON', 'Contracts_Small' if slide.get('DESTINATION') in
                  ('EnterSellPlayers', 'EnterNegHistory') else 'GlobalTransferNetwork_Med')
        for field in slide.findall('data'):
            if field.get('TYPE') == 'text':
                field.set('WIDTH', '370')
                field.set('HEIGHT', '65')


def refined(root):
    mine = tile(root.find('panel_7'), 'MY_TEAM_CLUB')
    content = pages(mine)
    return (content[0].get('ID') == '720'
            and len(content) > 1 and content[1].get('DESTINATION') == 'Server16EnterDressingRoom'
            and any(t.find('tileid').get('NAME') == 'SERVER16_CLUB_BROWSER'
                    for t in root.find('panel_4').findall('tile'))
            and tile(root.find('panel_2'), 'SERVER16_MANAGER_MARKET').find("data[@ID='TITLE']").get('PARAM')
                    == 'M. TÉCNICOS'
            and len([n for n in tile(root.find('panel_2'), 'GTN_STATIC').iter('data')
                     if n.get('ID') == 'MARKET_ICON_ON']) == 2)


def refine(raw):
    """Second local revision: order, Season access and icon position only."""
    root = ET.fromstring(raw)
    if refined(root):
        validate(root)
        return raw
    before_events = destinations(root)
    mine = tile(root.find('panel_7'), 'MY_TEAM_CLUB')
    content = pages(mine)
    summary = page(content, ident='720')
    # The first page must accept focus even though it has no click action,
    # otherwise the controller cannot reach the dressing room on page two.
    summary.set('HIGHLIGHTABLE', 'TRUE')
    room = page(content, destination='Server16EnterDressingRoom')
    arrange(mine, [summary, room] + [p for p in content if p not in (summary, room)])

    season = root.find('panel_4')
    other = tile(season, 'OTHER_LEAGUES')
    other_pages = pages(other)
    clubs = page(other_pages, destination='Server16EnterClubBrowser')
    team = tile(season, 'TEAM_STATS')
    team_page = pages(team)[0]
    team_page.set('ID', team.find('tileid').get('tileid'))
    player = tile(season, 'PLAYER_STATS')
    player_pages = pages(player)
    if not player_pages[0].get('ID'):
        player_pages[0].set('ID', player.find('tileid').get('tileid'))
    arrange(player, player_pages + [team_page])
    # Reuse the exact old club-browser page, including its original image.
    index = list(season).index(team)
    standalone = ET.Element('tile')
    ET.SubElement(standalone, 'tileid', tileid=clubs.get('ID'), NAME='SERVER16_CLUB_BROWSER', PARAM='')
    standalone.append(deepcopy(team.find('settings')))
    arrange(standalone, [clubs])
    season.remove(team)
    season.insert(index, standalone)
    arrange(other, [p for p in other_pages if p is not clubs])
    season.find('entries').set('numberoftiles', str(len(season.findall('tile'))))

    coach = tile(root.find('panel_2'), 'SERVER16_MANAGER_MARKET')
    coach.find("data[@ID='TITLE']").set('PARAM', 'M. TÉCNICOS')

    # The same original globe DDS pair, at the same 292x204 native size.
    # Explicit image placement is already supported by FIFA's XML tile schema.
    # Move only these large-card icons; compact-card images remain untouched.
    market = tile(root.find('panel_2'), 'GTN_STATIC')
    content = pages(market)
    for slide in content:
        if slide.get('DESTINATION') not in ('Server16EnterTransferMarket', 'EnterGTNHub'):
            continue
        if slide.get('BG_ICON') != 'GlobalTransferNetwork_Med':
            raise ValueError('Market icon changed; cannot reposition a different image')
        slide.attrib.pop('BG_ICON')
        title = slide.find("data[@ID='TITLE']")
        title.attrib.update(X='18', Y='18', WIDTH='486', HEIGHT='112')
        for field in slide.findall('data'):
            if field.get('TYPE') == 'text':
                field.attrib.pop('REL_TARGET', None)
                field.attrib.pop('REL_Y', None)
                field.attrib.update(X='18', Y='142', WIDTH='486', HEIGHT='74')
        for state, hl, uhl, name in [('active', '100', '0', 'ON'), ('nonactive', '0', '100', 'OFF')]:
            ET.SubElement(slide, 'data', ID='MARKET_ICON_'+name, TYPE='image', VISIBLE='TRUE',
                PATH=f'imgAssets/tileIcons/ti_globaltransfernetwork_med_{state}.dds',
                WIDTH='292', HEIGHT='204', X='536', Y='18', HLALPHA=hl, UHLALPHA=uhl)
    arrange(market, content)
    if destinations(root) != before_events:
        raise ValueError('Refinement lost or duplicated a career destination')
    validate(root)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def reorganize(raw):
    root = ET.fromstring(raw)
    if organized(root):
        validate(root)
        return refine(raw)
    before_events = destinations(root)
    central, transfers, office, mine = [root.find(f'panel_{i}') for i in (0, 2, 3, 7)]

    # Central retains its next-match/news pages. Move the entire deal pages,
    # including the 20 original component IDs/provider bindings, to Transfers.
    next_match = tile(central, 'NEXT_MATCH_CENTRAL')
    central_pages = pages(next_match)
    deals = [page(central_pages, ident=value) for value in ('529', '530')]
    arrange(next_match, [n for n in central_pages if n.get('ID') not in ('529', '530')])
    market = tile(transfers, 'GTN_STATIC')
    arrange(market, pages(market) + deals)
    box(market, 109, 278, 846, 632)
    for report in transfers.findall('tile'):
        if report.find('tileid').get('NAME') == 'SCOUT_REPORT':
            # Both native variants occupy this box conditionally. Preserve
            # their internals and dimensions; never add a static child to them.
            box(report, 965, 278, 846, 418)

    # Player search, instructions, shortlist, selling and negotiation history
    # form one compact, native carousel below the report. Coach market is a
    # separate neighboring card, rather than a hidden Office slide.
    search, sell = tile(transfers, 'SHOPPING_LIST'), tile(transfers, 'SELL_PLAYERS')
    player_actions = pages(search) + pages(sell)
    compact_player_actions(player_actions)
    arrange(search, player_actions)
    box(search, 965, 706, 418, 204)
    transfers.remove(sell)
    budget = tile(transfers, 'FINANCES')
    budget_page = pages(budget)[0]
    budget_page.set('ID', budget.find('tileid').get('tileid'))
    transfers.remove(budget)

    finances = tile(office, 'REQUEST_FUNDS')
    finance_pages = pages(finances)
    manager_page = page(finance_pages, destination='Server16EnterManagerMarket')
    coach = ET.SubElement(transfers, 'tile')
    ET.SubElement(coach, 'tileid', tileid=manager_page.get('ID'), NAME='SERVER16_MANAGER_MARKET', PARAM='')
    ET.SubElement(coach, 'settings')
    arrange(coach, [manager_page])
    box(coach, 1393, 706, 418, 204)

    # Finance is visible first. Native allocation retains its own provider and
    # budget fields on its slide; the shared card has no provider of its own.
    budget_title = budget_page.find("data[@ID='TITLE']")
    budget_title.set('PARAM', 'DISTRIBUIR ORÇAMENTO')
    budget_title.set('TRANSLATE', 'FALSE')
    for key, y in (('TRANSFERBUGET', 78), ('WAGEBUGET', 120)):
        field = budget_page.find(f"data[@ID='{key}']")
        field.attrib.pop('REL_TARGET', None)
        field.attrib.pop('REL_Y', None)
        field.attrib.update(WIDTH='790', HEIGHT='36', X='18', Y=str(y))
    arrange(finances, [page(finance_pages, destination='Server16EnterClubFinance'),
                       page(finance_pages, destination='Server16EnterBankLoans'),
                       budget_page, page(finance_pages, destination='EnterAdditionalFunds')])
    box(finances, 109, 706, 846, 204)
    box(tile(office, 'MY_CAREER'), 965, 492, 418, 204)

    # A wide dressing-room banner is the first page of Meu time's existing
    # bottom carousel. The full club summary remains its second page, unchanged.
    room = tile(office, 'SERVER16_DRESSING_ROOM')
    room_page = pages(room)[0]
    room_page.set('ID', room.find('tileid').get('tileid'))
    room_page.set('HIGHLIGHTABLE', 'TRUE')
    office.remove(room)
    title = room_page.find("data[@ID='TITLE']")
    title.attrib.update(PARAM='VESTIÁRIO 3D', WIDTH='1500', HEIGHT='50', X='28', Y='22')
    description = room_page.find("data[@ID='S16_ROOM_DESCRIPTION']")
    description.attrib.update(PARAM='Cenas, jogadores do time e câmera livre no ambiente do clube',
                              WIDTH='1320', HEIGHT='70', X='28', Y='100')
    club = tile(mine, 'MY_TEAM_CLUB')
    arrange(club, [room_page] + pages(club))

    for panel in (central, transfers, office, mine):
        panel.find('entries').set('numberoftiles', str(len(panel.findall('tile'))))
    if destinations(root) != before_events:
        raise ValueError('A career destination was lost or duplicated')
    validate(root)
    return refine(ET.tostring(root, encoding='utf-8', xml_declaration=True))


def validate(root):
    """Reject clipping/overlap, malformed cycling and accidental mod duplicates."""
    for panel in root:
        if not panel.tag.startswith('panel_') or panel.tag == 'panel_set':
            continue
        cards = panel.findall('tile')
        if int(panel.find('entries').get('numberoftiles')) != len(cards):
            raise ValueError(f'Incorrect tile count in {panel.tag}')
        for card in cards:
            children = [n for n in card if n.tag.startswith('subtile')]
            counter = card.find('number_of_subtiles')
            if counter is not None and int(counter.get('LENGTH')) != len(children):
                # Central training has five native training slots in LENGTH,
                # including its main page. It is an original FIFA convention.
                if not (card.find('tileid').get('NAME') == 'TRAINING'
                        and int(counter.get('LENGTH')) == len(children)+1):
                    raise ValueError('Incorrect carousel count')
            if [n.tag for n in children] != [f'subtile{i+1}' for i in range(len(children))]:
                raise ValueError('Non-contiguous carousel pages')
        # The active-day cards in Central and the two scout-report variants are
        # native conditional alternatives. Other simultaneous tiles cannot overlap.
        if panel.tag in ('panel_2', 'panel_3', 'panel_4', 'panel_7'):
            rects = []
            for card in cards:
                name = card.find('tileid').get('NAME')
                s = card.find('settings')
                x, y, w, h = [int(s.get(k)) for k in ('X', 'Y', 'WIDTH', 'HEIGHT')]
                if x < 109 or y < 278 or x+w > 1811 or y+h > 910 or min(w, h) <= 0:
                    raise ValueError(f'Card outside career bounds: {name}')
                for other, a, b, c, d in rects:
                    if name == other == 'SCOUT_REPORT':
                        continue
                    if x < a+c and a < x+w and y < b+d and b < y+h:
                        raise ValueError(f'Overlapping cards: {name} / {other}')
                rects.append((name, x, y, w, h))
    expected = {'Server16EnterTransferMarket': 2, 'Server16EnterManagerMarket': 2,
                'Server16EnterClubFinance': 3, 'Server16EnterBankLoans': 3,
                'Server16EnterDressingRoom': 7, 'Server16EnterClubBrowser': 4}
    for event, panel_id in expected.items():
        matches = [p.tag for p in root if p.tag.startswith('panel_') for n in p.iter()
                   if n.get('DESTINATION') == event]
        if matches != [f'panel_{panel_id}']:
            raise ValueError(f'Incorrect career destination: {event}: {matches}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error('Stage to a different file before installation')
    result = reorganize(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
