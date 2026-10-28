"""Read-only saved FCE schedule and previous-round movements. No runtime reference install required."""
import struct,datetime

def read_schedule(raw, stage_formats=None):
    marker = raw.find(b'FCE_Setup_Stage')
    start = marker - 12 - 2 * 47
    if marker < 0 or start < 0:
        return []

    def block(offset, stride):
        rows = []
        for index in range(65536):
            if offset + stride > len(raw) or struct.unpack_from('<H', raw, offset)[0] != index:
                break
            rows.append(raw[offset:offset + stride])
            offset += stride
        return (rows, offset)
    nodes, offset = block(start, 47)
    if len(nodes) < 3 or nodes[0][12:16] != b'FIFA':
        return []
    assignments, offset = block(offset, 10)
    fixtures, offset = block(offset, 21)
    rounds, offset = block(offset, 12)
    entrants, offset = block(offset, 20)
    pools, offset = block(offset, 10)
    periods, offset = block(offset, 14)
    standings, offset = block(offset, 21)
    if not all((nodes, assignments, fixtures, rounds, entrants, pools, periods, standings)):
        return []
    objects = {struct.unpack_from('<H', r, 3)[0]: r for r in nodes if r[2] == 1}
    teams = {struct.unpack_from('<H', r, 0)[0]: struct.unpack_from('<i', r, 5)[0] for r in standings if r[2] == 1}
    standing_groups = {struct.unpack_from('<H', r, 0)[0]: struct.unpack_from('<H', r, 3)[0] for r in standings if r[2] == 1}
    stage_names = {'FCE_Group_Stage': 2, 'FCE_Round_1': 3, 'FCE_Round_2': 4, 'FCE_Round_of_32': 5, 'FCE_Round_of_16': 6, 'FCE_Quarter_Finals': 7, 'FCE_Semi_Finals': 8, 'FCE_Third_Place': 9, 'FCE_Final': 10}
    stage_formats = stage_formats or {}

    def stage_kind(stage):
        visited = set()
        while stage in objects and stage not in visited:
            visited.add(stage)
            node = objects[stage]
            if node[5] == 4:
                if stage in stage_formats:return stage_formats[stage]['kind']
                name = node[12:45].split(b'\x00', 1)[0].decode('ascii', errors='ignore')
                if name.startswith('FCE_'):
                    return stage_names.get(name, 1 if name == 'FCE_Setup_Stage' else 0)
            stage = struct.unpack_from('<h', node, 45)[0]
        return 0
    result = []
    for row in fixtures:
        if row[2] != 1:
            continue
        date = struct.unpack_from('<I', row, 6)[0]
        try:
            datetime.date(date // 10000, date // 100 % 100, date % 100)
        except ValueError:
            continue
        home = teams.get(struct.unpack_from('<H', row, 12)[0], -1)
        away = teams.get(struct.unpack_from('<H', row, 16)[0], -1)
        if home < 0 or away < 0 or home == away:
            continue
        stage = struct.unpack_from('<H', row, 3)[0]
        home_group = standing_groups.get(struct.unpack_from('<H', row, 12)[0])
        away_group = standing_groups.get(struct.unpack_from('<H', row, 16)[0])
        group = home_group if home_group == away_group else None
        if group in objects:
            stage = group
        if stage in objects and objects[stage][5]==5:
            stage = struct.unpack_from('<h',objects[stage],45)[0]
        kind = stage_kind(stage)
        root = stage
        visited = set()
        asset = 0
        while root in objects and root not in visited:
            visited.add(root)
            node = objects[root]
            if node[5] == 3:
                key = node[6:12].split(b'\x00', 1)[0].decode('ascii', errors='ignore')
                title = node[12:45].split(b'\x00', 1)[0].decode('ascii', errors='ignore')
                identity = title.removeprefix('TrophyName_Abbr15_') if title.startswith('TrophyName_Abbr15_') else key[1:] if key.startswith('C') else ''
                asset = int(identity) if identity.isdigit() else 0
                break
            root = struct.unpack_from('<h', node, 45)[0]
        time_value = struct.unpack_from('<H', row, 10)[0]
        result.append({'id': struct.unpack_from('<H', row, 0)[0], 'home': home, 'away': away, 'root': root, 'asset': asset, 'date': date, 'time': f'{time_value // 100:02d}:{time_value % 100:02d}', 'stage': stage, 'group':group, 'stageKind': kind, 'homeScore': row[14] if row[14] != 255 else None, 'awayScore': row[18] if row[18] != 255 else None, 'played': bool(row[20]), 'score': f'{row[14]} – {row[18]}' if row[20] else '—'})
    return result

def read_assignment_roots(raw):
    marker = raw.find(b'FCE_Setup_Stage')
    start = marker - 12 - 2 * 47
    if marker < 0 or start < 0:
        return {}

    def block(offset, stride):
        rows = []
        for index in range(65536):
            if offset + stride > len(raw) or struct.unpack_from('<H', raw, offset)[0] != index:
                break
            rows.append(raw[offset:offset + stride])
            offset += stride
        return (rows, offset)
    nodes, offset = block(start, 47)
    if not nodes:
        return {}
    assignments, offset = block(offset, 10)
    objects = {struct.unpack_from('<H', row, 3)[0]: row for row in nodes if row[2] == 1}

    def identity(root):
        node = objects.get(root)
        if node is None:
            return 0
        key = node[6:12].split(b'\x00', 1)[0].decode('ascii', errors='ignore')
        title = node[12:45].split(b'\x00', 1)[0].decode('ascii', errors='ignore')
        value = title.removeprefix('TrophyName_Abbr15_') if title.startswith('TrophyName_Abbr15_') else key[1:] if key.startswith('C') else ''
        return int(value) if value.isdigit() else 0
    result = {}
    for row in assignments:
        if row[2] != 1:
            continue
        obj = struct.unpack_from('<H', row, 3)[0]
        team = struct.unpack_from('<i', row, 6)[0]
        visited = set()
        root = obj
        while root in objects and root not in visited:
            visited.add(root)
            node = objects[root]
            if node[5] == 3:
                break
            root = struct.unpack_from('<h', node, 45)[0]
        if root not in objects or objects[root][5] != 3 or team <= 0:
            continue
        asset = identity(root)
        if asset <= 0:
            continue
        entries = result.setdefault(team, [])
        if not any((item['root'] == root for item in entries)):
            entries.append({'root': root, 'asset': asset})
    return result

def _apply_league_table_movements(rows, fixtures, career_date):
    """Compare the current league table with the table before its latest round."""
    if not rows:
        return rows
    played = []
    for match in fixtures or ():
        if not match.get('played'):
            continue
        try:
            date = int(match.get('date') or 0)
            home = int(match.get('home') or 0)
            away = int(match.get('away') or 0)
            home_score = int(match.get('homeScore'))
            away_score = int(match.get('awayScore'))
        except (TypeError, ValueError):
            continue
        if not home or not away or home == away or (career_date and date and (date > career_date)):
            continue
        try:
            round_number = int(match.get('round') or 0)
        except (TypeError, ValueError):
            round_number = 0
        played.append((match, date, round_number, home, away, home_score, away_score))
    if not played:
        return rows
    round_numbers = [item[2] for item in played if item[2] > 0]
    if round_numbers:
        latest_round = max(round_numbers)
        latest = [item for item in played if item[2] == latest_round]
    else:
        latest_date = max((item[1] for item in played))
        latest = [item for item in played if item[1] == latest_date]
    previous = {}
    for row in rows:
        try:
            team = int(row.get('team') or 0)
        except (TypeError, ValueError):
            continue
        if team <= 0:
            continue
        previous[team] = {'team': team, 'name': str(row.get('name') or ''), 'games': max(0, int(row.get('games') or 0)), 'wins': max(0, int(row.get('wins') or 0)), 'draws': max(0, int(row.get('draws') or 0)), 'losses': max(0, int(row.get('losses') or 0)), 'goalsFor': max(0, int(row.get('goalsFor') or 0)), 'goalsAgainst': max(0, int(row.get('goalsAgainst') or 0)), 'points': max(0, int(row.get('points') or 0))}
    for _, _, _, home, away, home_score, away_score in latest:
        for team, goals_for, goals_against in ((home, home_score, away_score), (away, away_score, home_score)):
            row = previous.get(team)
            if not row or row['games'] <= 0:
                continue
            row['games'] = max(0, row['games'] - 1)
            row['goalsFor'] = max(0, row['goalsFor'] - goals_for)
            row['goalsAgainst'] = max(0, row['goalsAgainst'] - goals_against)
            if goals_for > goals_against:
                row['wins'] = max(0, row['wins'] - 1)
                row['points'] = max(0, row['points'] - 3)
            elif goals_for == goals_against:
                row['draws'] = max(0, row['draws'] - 1)
                row['points'] = max(0, row['points'] - 1)
            else:
                row['losses'] = max(0, row['losses'] - 1)
    previous_rows = sorted(previous.values(), key=lambda row: (-row['points'], -row['wins'], -(row['goalsFor'] - row['goalsAgainst']), -row['goalsFor'], row['name'].casefold()))
    previous_rank = {row['team']: position for position, row in enumerate(previous_rows, 1)}
    for index, row in enumerate(rows, 1):
        row['movement'] = 0
        try:
            team = int(row.get('team') or 0)
            games = int(row.get('games') or 0)
            rank = int(row.get('rank') or index)
            old_rank = previous_rank.get(team, 0)
        except (TypeError, ValueError):
            continue
        if games < 2 or not old_rank or previous.get(team, {}).get('games', 0) < 1:
            continue
        if rank < old_rank:
            row['movement'] = 1
        elif rank > old_rank:
            row['movement'] = -1
    return rows
