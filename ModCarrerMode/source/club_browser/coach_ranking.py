"""Read-only manager ranking from the active career's manager-market ledger.

Only fixtures tied to a coach ID are ranked. Aggregate club tables are never
assigned to a manager because they cannot establish who coached each match.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import sqlite3
from urllib.parse import quote


def _path_key(value):
    text = str(value or '')
    if text.startswith('\\\\?\\'):
        text = text[4:]
    return os.path.normcase(os.path.normpath(os.path.abspath(text)))


def _date_cutoff(today, years):
    year = today // 10000 - years
    month = today // 100 % 100
    day = today % 100
    if month == 2 and day == 29:
        day = 28
    return year * 10000 + month * 100 + day


def _coach_key(value, used):
    candidate = int.from_bytes(hashlib.sha256(value.encode('utf-8')).digest()[:4], 'little') & 0x7fffffff
    candidate = candidate or 1
    while candidate in used and used[candidate] != value:
        candidate = candidate % 0x7fffffff + 1
    used[candidate] = value
    return candidate


def project(game, save, snapshot, *, pid, rules, teams=None):
    """Return ranked coaches and a safe default when the active ledger is absent."""
    empty = dict(rows=[], mine=0, matches=0, branch_date=0, branch=None)
    root = Path(game) / 'ModCarrerMode/runtime/manager_market'
    try:
        state = json.loads((root / 'state_ready.json').read_text(encoding='utf-8'))
        if (int(state.get('pid', 0)) != int(pid)
                or int(state.get('club', 0)) != int(snapshot.get('club', 0))
                or int(state.get('date', 0)) > int(snapshot['date'])
                or _path_key(state.get('save')) != _path_key(save)):
            return empty
        database = Path(str(state['database']).removeprefix('\\\\?\\'))
        branch = str(state['branch'])
        if not database.is_file() or not branch:
            return empty
        uri = 'file:' + quote(database.resolve().as_posix(), safe='/:') + '?mode=ro'
        connection = sqlite3.connect(uri, uri=True, timeout=.25)
        connection.row_factory = sqlite3.Row
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        return empty

    try:
        branch_row = connection.execute(
            'SELECT start_date,game_date,user_club FROM branches WHERE id=?', (branch,)
        ).fetchone()
        if (not branch_row or branch_row['user_club'] != snapshot['club']
                or branch_row['game_date'] > snapshot['date']):
            return empty

        today = int(snapshot['date'])
        lower = _date_cutoff(today, int(rules.get('years', 4)))
        coaches = {
            row['coach_id']: dict(row)
            for row in connection.execute(
                'SELECT coach_id,name,nationality,reputation FROM coaches WHERE branch=?', (branch,)
            )
            if row['coach_id']
        }
        clubs = {
            row['club_id']: dict(row)
            for row in connection.execute(
                'SELECT club_id,name,league_name,country FROM clubs WHERE branch=?', (branch,)
            )
        }
        appointments = list(connection.execute(
            'SELECT coach_id,club_id,start_date,end_date FROM appointments '
            'WHERE branch=? AND start_date<=? ORDER BY start_date, rowid', (branch, today)
        ))
        current_appointment = {}
        for appointment in appointments:
            current_appointment[appointment['coach_id']] = appointment

        honors = {}
        for row in connection.execute(
            'SELECT coach_id,COUNT(*) AS total FROM honours '
            'WHERE branch=? AND game_date BETWEEN ? AND ? GROUP BY coach_id',
            (branch, lower, today),
        ):
            honors[row['coach_id']] = row['total']

        stats = {}
        tracked_matches = 0
        result_rows = connection.execute(
            'SELECT game_date,home,away,hg,ag,home_coach,away_coach FROM results '
            'WHERE branch=? AND game_date BETWEEN ? AND ? ORDER BY game_date,match_key',
            (branch, lower, today),
        )
        for match in result_rows:
            home_coach, away_coach = match['home_coach'], match['away_coach']
            hg, ag = match['hg'], match['ag']
            if (not home_coach or not away_coach or home_coach == away_coach
                    or type(hg) is not int or type(ag) is not int
                    or not 0 <= hg < 100 or not 0 <= ag < 100):
                continue
            tracked_matches += 1
            for is_home, coach_id, opponent in (
                (True, home_coach, match['away']),
                (False, away_coach, match['home']),
            ):
                if coach_id not in coaches:
                    continue
                row = stats.setdefault(coach_id, dict(games=0, wins=0, draws=0, losses=0, recent=[]))
                gf, ga = (hg, ag) if is_home else (ag, hg)
                result = 'V' if gf > ga else 'E' if gf == ga else 'D'
                row['games'] += 1
                row['wins'] += result == 'V'
                row['draws'] += result == 'E'
                row['losses'] += result == 'D'
                row['recent'].append(dict(
                    date=match['game_date'],
                    opponent=clubs.get(opponent, {}).get('name', f'Clube {opponent}'),
                    score=f'{gf}–{ga}', delta=3 if result == 'V' else 1 if result == 'E' else 0,
                    importance=1.0,
                ))

        policy = rules.get('coaches', {})
        prior = max(1, int(policy.get('prior_games', 24)))
        performance_weight = float(policy.get('performance_weight', 700))
        games_weight = float(policy.get('games_weight', 28))
        title_bonus = float(policy.get('title_bonus', 12))
        title_cap = max(0, int(policy.get('title_cap', 5)))
        id_map = {}
        used = {}
        by_key = {}
        for coach_id, record in stats.items():
            games = record['games']
            if games <= 0:
                continue
            points = 3 * record['wins'] + record['draws']
            observed = points / (3 * games)
            adjusted = (points + 1.5 * prior) / (3 * (games + prior))
            confidence = games / (games + prior)
            performance = (adjusted - .5) * performance_weight * confidence
            volume = games_weight * math.log1p(games)
            titles = honors.get(coach_id, 0)
            title_points = min(titles, title_cap) * title_bonus
            appointment = current_appointment.get(coach_id)
            club_id = appointment['club_id'] if appointment else 0
            club = clubs.get(club_id, {})
            team=(teams or {}).get(club_id,{})
            overall=max(30,min(99,int(team.get('overall') or 50)))
            domestic=max(0,min(20,int(team.get('domestic') or 0)))
            international=max(0,min(20,int(team.get('international') or 0)))
            club_points=max(0,overall-50)*float(policy.get('club_overall_weight',5))
            club_points+=domestic*float(policy.get('club_domestic_weight',8))+international*float(policy.get('club_international_weight',10))
            club_points*=confidence
            # A former club is historical context, not a current appointment.
            if not appointment or (appointment['end_date'] is not None and appointment['end_date']<today):club_points*=.5
            coach = coaches[coach_id]
            stable_id = _coach_key(coach_id, used)
            id_map[coach_id] = stable_id
            recent = sorted(record['recent'], key=lambda m: m['date'])[-5:]
            by_key[coach_id] = dict(
                id=stable_id, nation=int(club_id or 0), confederation=0,
                name=coach.get('name') or coach_id,
                country=coach.get('nationality') or 'Nacionalidade não informada',
                countryName=coach.get('nationality') or 'Nacionalidade não informada',
                league=club.get('name') or 'Sem clube registrado',
                leagueName=club.get('name') or 'Sem clube registrado',
                points=round(1000 + club_points + performance + volume + title_points, 2),
                initial=round(1000+club_points,2), matchPoints=round(performance + volume, 2),
                titlePoints=round(title_points, 2), games=games,
                wins=record['wins'], draws=record['draws'], losses=record['losses'],
                titles=titles, form=''.join('V' if m['delta'] == 3 else 'E' if m['delta'] == 1 else 'D' for m in recent),
                campaignPoints=0.0, campaignGames=0, recent=recent,
                percentage=round(observed * 100, 2),
            )

        ordered = sorted(
            by_key.values(),
            key=lambda row: (-row['points'], -row['wins'], -row['games'], row['name'].casefold(), row['id']),
        )
        for index, row in enumerate(ordered, 1):
            row['rank'] = index
            row['movement'] = 0
        mine = 0
        active = [a for a in appointments if a['club_id'] == snapshot['club']
                  and a['start_date'] <= today and (a['end_date'] is None or a['end_date'] >= today)]
        if active:
            mine = id_map.get(active[-1]['coach_id'], 0)
        return dict(rows=ordered, mine=mine, matches=tracked_matches,
                    branch_date=int(branch_row['game_date']), branch=branch)
    except (sqlite3.Error, KeyError, TypeError, ValueError, OverflowError):
        return empty
    finally:
        connection.close()
