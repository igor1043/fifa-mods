"""Current cup phase and campaign depth from actual dated fixtures."""
from math import ceil


def knockout_first(fixtures, today):
    groups = [m for m in fixtures if m.get('stageKind') == 2]
    played = [m for m in groups if m.get('played') and m['date'] <= today]
    if not played:
        return False
    end = max(m['date'] for m in played)
    knockout = [m for m in fixtures if m.get('stageKind', 0) > 2 and m['date'] >= end]
    return (any(m.get('played') and m['date'] <= today for m in knockout)
            or (not any(not m.get('played') for m in groups)
                and any(min(m.get('home', 0), m.get('away', 0)) > 0 for m in knockout)))


def depth(fixtures):
    stages = {}
    for m in fixtures:
        key = m.get('stage', m.get('stageKind', 0))
        stages[key] = min(stages.get(key, m['date']), m['date'])
    order = {stage: i for i, (stage, _) in enumerate(sorted(stages.items(), key=lambda p: (p[1], p[0])))}
    clubs = {}
    for m in fixtures:
        rank = order[m.get('stage', m.get('stageKind', 0))]
        for club in (m['home'], m['away']):
            clubs[club] = max(clubs.get(club, 0), rank)
    return clubs


def minimum_sample(maximum):
    return max(1, ceil(maximum * .70))
