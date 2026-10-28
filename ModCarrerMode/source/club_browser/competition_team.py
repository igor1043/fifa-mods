"""Choose a balanced XI using only validated match ratings of one competition."""
from collections import defaultdict

FORMATIONS = (
    ('4-3-3', (0, 3, 4, 6, 7, 13, 14, 15, 23, 25, 27)),
    ('4-4-2', (0, 3, 4, 6, 7, 12, 13, 15, 16, 24, 26)),
    ('4-2-3-1', (0, 3, 4, 6, 7, 9, 11, 17, 18, 19, 25)),
    ('3-5-2', (0, 4, 5, 6, 12, 13, 14, 15, 16, 24, 26)),
    ('5-3-2', (0, 2, 4, 5, 6, 8, 13, 14, 15, 24, 26)),
)



def position_name(value):
    if type(value) is not int or not 0 <= value <= 27:return ''
    if value == 0:return 'Goleiro'
    if value == 1:return 'Líbero'
    if value in (2,3):return 'Lateral-direito'
    if value in (4,5,6):return 'Zagueiro'
    if value in (7,8):return 'Lateral-esquerdo'
    if value in (9,10,11):return 'Volante'
    if 12 <= value <= 16:return 'Meio-campista'
    if 17 <= value <= 19:return 'Meia-atacante'
    if 20 <= value <= 22:return 'Segundo atacante'
    if value == 23:return 'Ponta-direita'
    if value == 27:return 'Ponta-esquerda'
    return 'Centroavante'

def build_competition_statistics(snapshot, roots, players, display_name, team_names=None):
    """Small current-career payload; does not load the world/history catalogue."""
    team_names = team_names or {}
    requested = set(roots)
    nodes = {}
    for row in snapshot.get('nodes', []):
        if isinstance(row, list) and len(row) >= 3:
            try:
                node, parent, kind = map(int, row[:3])
                nodes[node] = (parent, kind)
            except (TypeError, ValueError):
                continue
    def root_for(node):
        seen = set()
        while node in nodes and node not in seen:
            seen.add(node)
            parent, kind = nodes[node]
            if kind == 3:
                return node
            node = parent
        return None
    grouped = defaultdict(list)
    for row in snapshot.get('stats', []):
        if not isinstance(row, list) or len(row) < 8:
            continue
        try:
            sid, competition, team, player, appearances, minutes, goals, assists = map(int, row[:8])
            rating, valid = map(int, row[8:10]) if len(row) >= 10 else (0, 0)
        except (TypeError, ValueError):
            continue
        root = root_for(competition)
        if root not in requested or min(team, player) <= 0 or min(appearances, minutes, goals, assists) < 0:
            continue
        grouped[root].append({'id': sid, 'competition': competition, 'root': root, 'team': team, 'player': player,
                              'appearances': appearances, 'minutes': minutes, 'goals': goals, 'assists': assists,
                              'ratingSum': rating, 'profileValid': valid})
    result = {}
    for root in requested:
        rows = grouped.get(root, [])
        unique = {}
        for row in rows:
            key = row['player'], row['team'], row['competition']
            old = unique.get(key)
            if old is None or (row['appearances'], row['minutes'], row['id']) >= (old['appearances'], old['minutes'], old['id']):
                unique[key] = row
        by_player = defaultdict(list)
        for row in unique.values():
            by_player[row['player']].append(row)
        leaders = {'goals': [], 'assists': []}
        for player, items in by_player.items():
            if player not in players:
                continue
            selected = [row for row in items if row['competition'] == root] or items
            for field in leaders:
                value = sum(row[field] for row in selected)
                if value <= 0:
                    continue
                club = max(selected, key=lambda row: (row[field], row['appearances'], row['team']))['team']
                leaders[field].append({'id': player, 'player': player, 'club': club, 'clubName': team_names.get(club, 'Clube'),
                                       'name': display_name(players[player]), 'value': value,
                                       'position': position_name(players[player].get('preferredposition1')),
                                       'appearances': sum(row['appearances'] for row in selected)})
        for values in leaders.values():
            values.sort(key=lambda row: (-row['value'], -row['appearances'], row['name'].casefold(), row['id']))
        result[root] = {'root': root, 'statsGeneration': snapshot.get('generation'), **leaders,
                        'teamOfCompetition': build_competition_team(root, rows, players, display_name, team_names)}
    return result


def _eligible(slot, positions):
    if slot == 0:
        return 0 in positions
    positions = set(positions) - {0}
    allowed = ({2, 3} if slot in (2, 3) else {7, 8} if slot in (7, 8)
               else {1, 4, 5, 6} if slot in (4, 5, 6)
               else set(range(9, 16)) if slot in (9, 10, 11)
               else set(range(9, 20)) if slot in (13, 14, 15)
               else {12, 17, 20, 23} if slot == 12
               else {16, 19, 22, 27} if slot == 16
               else set(range(12, 23)) if slot in (17, 18, 19)
               else {12, 17, 20, 23, 24} if slot == 23
               else {16, 19, 22, 26, 27} if slot == 27
               else set(range(20, 28)))
    return bool(positions & allowed)


def _matching(slots, candidates):
    """Rectangular Hungarian matching: maximize total mean, unique players."""
    n, m = len(slots), len(candidates)
    if m < n:
        return None
    illegal = 1000000.0
    costs = [[(-p['ratingSum'] / (10 * p['appearances'])
               - min(p['appearances'], 255) * 1e-9 - min(p['minutes'], 65535) * 1e-13)
              if _eligible(slot, p['positions']) else illegal
              for p in candidates] for slot in slots]
    u, v, owner, previous = [0.] * (n + 1), [0.] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        owner[0], column = i, 0
        best, used = [float('inf')] * (m + 1), [False] * (m + 1)
        while True:
            used[column] = True
            row, delta, next_column = owner[column], float('inf'), 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cost = costs[row - 1][j - 1] - u[row] - v[j]
                if cost < best[j]:
                    best[j], previous[j] = cost, column
                if best[j] < delta:
                    delta, next_column = best[j], j
            for j in range(m + 1):
                if used[j]:
                    u[owner[j]] += delta
                    v[j] -= delta
                else:
                    best[j] -= delta
            column = next_column
            if not owner[column]:
                break
        while column:
            next_column = previous[column]
            owner[column] = owner[next_column]
            column = next_column
    result = [None] * n
    for j in range(1, m + 1):
        if owner[j]:
            row = owner[j] - 1
            if costs[row][j - 1] >= illegal:
                return None
            result[row] = {**candidates[j - 1], 'slot': slots[row]}
    return result


def build_competition_team(root, stats, players, display_name, team_names=None):
    """Rows must belong to root. Root totals replace their child-stage totals."""
    team_names = team_names or {}
    unique = {}
    for row in stats:
        if row.get('root', root) != root or not (int(row.get('profileValid') or 0) & 2):
            continue
        appearances, rating = int(row.get('appearances') or 0), int(row.get('ratingSum') or 0)
        if appearances <= 0 or not 0 < rating <= appearances * 100:
            continue
        key = (row['player'], row['team'], row['competition'])
        current = unique.get(key)
        if current is None or (appearances, row.get('minutes', 0), row.get('id', 0)) > (
                current['appearances'], current.get('minutes', 0), current.get('id', 0)):
            unique[key] = row
    groups = defaultdict(list)
    for row in unique.values():
        groups[row['player']].append(row)
    candidates = []
    for player_id, rows in sorted(groups.items()):
        player = players.get(player_id)
        if not player:
            continue
        positions = [player.get(f'preferredposition{i}') for i in range(1, 5)]
        positions = [p for p in positions if isinstance(p, int) and 0 <= p < 28]
        if not positions:
            continue
        totals = [row for row in rows if row['competition'] == root] or rows
        appearances = sum(row['appearances'] for row in totals)
        rating = sum(row['ratingSum'] for row in totals)
        club = max(totals, key=lambda row: (row['appearances'], row.get('minutes', 0), row['team']))['team']
        candidates.append({'id': player_id, 'name': display_name(player), 'positions': positions,
                           'positionId': positions[0], 'club': club, 'clubName': team_names.get(club, 'Clube'),
                           'appearances': appearances, 'minutes': sum(row.get('minutes', 0) for row in totals),
                           'ratingSum': rating, 'averageRating': round(rating / (10 * appearances), 4)})
    candidates.sort(key=lambda p: (-p['averageRating'], -p['appearances'], -p['minutes'], p['id']))
    best, best_score, formation = None, None, ''
    for name, slots in FORMATIONS:
        lineup = _matching(slots, candidates)
        if lineup is None:
            continue
        score = (sum(p['ratingSum'] / (10 * p['appearances']) for p in lineup),
                 sum(p['appearances'] for p in lineup), sum(p['minutes'] for p in lineup))
        if best_score is None or score > best_score:
            best, best_score, formation = lineup, score, name
    return {'available': best is not None, 'reason': None if best else 'positions' if candidates else 'no-ratings',
            'competitionRoot': root, 'ratedPlayers': len(candidates), 'minimumAppearances': 1,
            'formation': formation, 'averageRating': round(best_score[0] / 11, 2) if best_score else None,
            'starters': [{k: v for k, v in p.items() if k != 'positions'} for p in best] if best else []}
