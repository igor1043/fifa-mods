"""Build the 96-club migration from a preserved snapshot; never edit the game.

Only league-link history/ranks and the affected competition rules are changed.
Existing object IDs remain stable because V12 and the other competitions use them.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import struct
from collections import Counter
from pathlib import Path


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(data):
    return hashlib.sha256(data).hexdigest()


def migrate_db(raw, meta, reader, checksum):
    db = reader.FifaDatabase(Path('.'), raw, meta, include_all_tables=True)
    table = db.tables['leagueteamlinks']
    cols = ['teamid', 'leagueid', 'secondarytable', 'prevleagueid',
            'currenttableposition', 'previousyeartableposition']
    rows = db.rows('leagueteamlinks', cols)
    leagues = {r['leagueid'] for r in db.rows('leagues', ['leagueid'])}
    assert {351, 354} <= leagues and not ({352, 355, 356} & leagues)
    rank = {}
    for league, count in ((351, 96), (354, 30)):
        members = [(i, r) for i, r in enumerate(rows)
                   if r['leagueid'] == league and not r['secondarytable']]
        assert len(members) == count
        # Stable merge of the user's old rankings, with team ID as tie breaker.
        members.sort(key=lambda ir: (ir[1]['previousyeartableposition'],
                                     ir[1]['currenttableposition'], ir[1]['teamid']))
        rank.update({i: p for p, (i, _) in enumerate(members, 1)})
    out = bytearray(raw)
    edits = []
    for i, r in enumerate(rows):
        changes = {}
        if r['prevleagueid'] in (352, 355, 356):
            changes['prevleagueid'] = 351
        if i in rank:
            changes['currenttableposition'] = rank[i]
            changes['previousyeartableposition'] = rank[i]
        for field, value in changes.items():
            if r[field] == value:
                continue
            kind, bit, depth, low = table['fields'][field]
            assert kind in (3, 4) and 0 <= value-low < 1 << depth
            start = table['records'] + i * table['stride']
            for k in range(depth):
                byte, shift = start + (bit+k)//8, (bit+k)%8
                out[byte] = (out[byte] & ~(1 << shift)) | (((value-low) >> k & 1) << shift)
            edits.append(dict(row=i, teamid=r['teamid'], field=field,
                              before=r[field], after=value))
    _, _, entries = checksum.lade_db(out)
    offsets = sorted(o for _, o in entries)
    for i, start in enumerate(offsets):
        end = offsets[i+1] if i+1 < len(offsets) else len(out)-4
        struct.pack_into('<I', out, end, checksum.crc(out[start+0x28:end]))
    assert not checksum.pruefe_crc(out)
    changed = reader.FifaDatabase(Path('.'), bytes(out), meta, include_all_tables=True)
    expected = {(e['row'], e['field']): e['after'] for e in edits}
    for i, r in enumerate(rows):
        for field in table['fields']:
            old = db.value(table, i, field)
            new = changed.value(changed.tables['leagueteamlinks'], i, field)
            assert new == expected.get((i, field), old), (i, field)
    # Every other table, including the new players, kits and formations, is exact.
    for short, start in entries:
        if start+4 == table['records']-36-len(table['fields'])*16:
            continue
        i = offsets.index(start)
        end = offsets[i+1] if i+1 < len(offsets) else len(out)-4
        assert out[start+4:end] == raw[start+4:end], short
    return bytes(out), edits, rows


def calendar(blocked, rounds, first=71, last=354):
    """Pick a full season with >=2 days between rounds and no cup match date.

    Dynamic programming minimizes departure from an evenly distributed calendar.
    It does not change dates in any other competition.
    """
    available = [d for d in range(first, last+1) if d not in blocked]
    states = {d: ((d-first)**2, [d]) for d in available}
    for r in range(1, rounds):
        target = first + (last-first)*r/(rounds-1)
        new = {}
        best = None
        cursor = 0
        prior = sorted(states)
        for d in available:
            while cursor < len(prior) and prior[cursor] <= d-2:
                item = states[prior[cursor]]
                if best is None or item[0] < best[0]:
                    best = item
                cursor += 1
            if best is not None:
                new[d] = (best[0] + (d-target)**2, best[1]+[d])
        states = new
        assert states, 'Calendar cannot contain every round'
    dates = min(states.values(), key=lambda item: item[0])[1]
    assert len(dates) == rounds and all(b-a >= 2 for a, b in zip(dates, dates[1:]))
    assert not set(dates) & blocked
    return dates


def migrate_compdata(source, db_rows):
    names = ['compobj', 'compids', 'settings', 'tasks', 'standings',
             'advancement', 'schedule', 'initteams', 'weather', 'activeteams']
    raw = {n: (source/(n+'.txt')).read_bytes() for n in names}
    rows = {n: list(csv.reader(b.decode('utf-8-sig').splitlines())) for n, b in raw.items()}
    objects = {int(r[0]): r for r in rows['compobj']}
    assert objects[1680][2] == 'C351' and objects[1771][2] == 'C354'
    ids = {r['teamid'] for r in db_rows if r['leagueid'] == 351 and not r['secondarytable']}
    cup_roots = {1474, 1634, 1752} | {int(r[0]) for r in rows['initteams'] if int(r[2]) in ids}
    cup_roots -= set(range(1680, 1752))
    def competition(node):
        while int(objects[node][1]) > 3:
            node = int(objects[node][4])
        return node
    blocked = {int(r[1]) for r in rows['schedule'] if competition(int(r[0])) in cup_roots}
    dates = calendar(blocked, 95)
    retired = set(range(1683, 1752))
    # Retain ID placeholders to avoid shifting every other V12 competition.
    # All their execution data is removed, and their roots are explicitly NONE.
    for r in rows['compobj']:
        node = int(r[0])
        if node in (1680, 1771):
            r[4] = '1473'
        elif node == 1681:
            r[3] = 'FCE_League_Stage'
        elif node in (1683, 1688, 1693, 1696):
            r[4] = '1698'
    rows['compids'] = [r for r in rows['compids'] if int(r[0]) not in (1698, 1716, 1734)]
    rows['settings'] = [r for r in rows['settings'] if int(r[0]) not in retired | {1681, 1682}]
    for r in rows['settings']:
        if r[:2] == ['1680', 'info_league_releg']:
            r[2] = '354'
        elif r[:2] == ['1771', 'info_league_promo']:
            r[2] = '351'
    for node in (1698, 1716, 1734):
        rows['settings'] += [[str(node), 'comp_type', 'NONE'], [str(node), 'asset_id', '0']]
    rows['settings'] += [
        ['1681', 'match_stagetype', 'LEAGUE'],
        ['1681', 'match_matchsituation', 'LEAGUE'],
        ['1681', 'info_prize_money', '245000'],
        ['1681', 'info_prize_money_drop', '35'],
        ['1682', 'num_games', '1'],
        ['1682', 'info_slot_champ', '1'],
        ['1682', 'info_color_slot_champ', '1']]
    for p in range(1, 5):
        rows['settings'] += [['1682', k, str(p)] for k in ('info_slot_promo', 'info_color_slot_promo')]
    for p in range(93, 97):
        rows['settings'] += [['1682', k, str(p)] for k in ('info_slot_releg', 'info_color_slot_releg')]
    rows['tasks'] = [r for r in rows['tasks'] if int(r[0]) not in retired | {1680}]
    for r in rows['tasks']:
        # V12's Italian cup already uses consecutive FillFromLeagueInOrder
        # tasks into separate setup pools for the SAME league (780/781, league31).
        # Native ProcessLogic announces every accepted team to the shared filter;
        # this keeps the bracket and excludes teams selected by preceding pools.
        if r[0] == '1474' and r[2] in ('FillFromLeague', 'FillFromLeagueInOrder') and int(r[4]) in (351, 352, 355, 356):
            r[2], r[4] = 'FillFromLeagueInOrder', '351'
    rows['tasks'] += [
        ['1680', 'start', 'FillFromLeague', '1682', '351', '0', '0'],
        ['1680', 'start', 'ClearLeagueStats', '1681', '351', '0', '0'],
        ['1680', 'end', 'UpdateLeagueStats', '1681', '351', '0', '0']]
    rows['tasks'] += [['1680', 'end', 'UpdateTable', '1680', '1682', str(p), str(p)] for p in range(1, 97)]
    for name in ('standings', 'schedule', 'initteams', 'weather'):
        rows[name] = [r for r in rows[name] if int(r[0]) not in retired | {1681, 1682}]
    rows['standings'] += [['1682', str(p)] for p in range(96)]
    rows['schedule'] += [['1681', str(day), str(r), '48', '48', '1600'] for r, day in enumerate(dates, 1)]
    rows['advancement'] = [r for r in rows['advancement']
                           if int(r[0]) not in retired | {1682} and int(r[2]) not in retired | {1682}]
    # Sort stably by object ID. Repeated settings/task order is significant.
    outputs = {}
    for name, records in rows.items():
        if name != 'activeteams':
            records.sort(key=lambda r: int(r[0]))
        encoded = ('\r\n'.join(','.join(r) for r in records)+'\r\n').encode('utf-8')
        if encoded != raw[name]:
            outputs[name+'.txt'] = encoded
    active = {int(r[0]) for r in rows['compids']}
    assert not active & retired
    assert [int(r[1]) for r in rows['standings'] if r[0] == '1682'] == list(range(96))
    assert [int(r[2]) for r in rows['schedule'] if r[0] == '1681'] == list(range(1, 96))
    for name in ('settings', 'tasks', 'standings', 'advancement', 'schedule', 'initteams', 'weather'):
        for r in rows[name]:
            assert int(r[0]) in objects
            if int(r[0]) in retired:
                assert name == 'settings' and r[1] in ('comp_type', 'asset_id')
    for r in rows['advancement']:
        assert int(r[2]) in objects and int(r[2]) not in retired
    for r in rows['tasks']:
        if r[2] in ('FillFromLeague', 'FillFromLeagueInOrder', 'UpdateLeagueStats', 'ClearLeagueStats'):
            assert int(r[4]) not in (352, 355, 356)
        assert int(r[3]) in objects
        assert int(r[3]) not in retired
        if r[2] in ('FillFromCompTable', 'UpdateTable', 'FillFromCompTableBackup'):
            assert int(r[4]) not in retired
    for r in rows['settings']:
        if r[1] in ('info_league_promo', 'info_league_releg'):
            assert int(r[2]) not in (352, 355, 356)
    return outputs, dict(line_counts={n:len(r) for n,r in rows.items()},
                        dates=dates, excluded_cup_dates=sorted(blocked),
                        excluded_cup_competitions=sorted(cup_roots),
                        fixture_count=96*95//2, retired_objects=sorted(retired),
                        retained_placeholder_reason='Preserve existing object IDs and V12 references',
                        cup_pool_selection='Sequential native FillFromLeagueInOrder; existing bracket retained')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--backup', type=Path, required=True)
    p.add_argument('--reader', type=Path, required=True)
    args = p.parse_args()
    reader = import_file('dbreader', args.reader)
    checksum = import_file('dbcrc', Path(__file__).with_name('fifa_db_l9schema.py'))
    backup = args.backup.resolve()
    candidate = backup/'candidate'
    meta = backup/'game-db/fifa_ng_db-meta.xml'
    original = (backup/'game-db/fifa_ng_db.db').read_bytes()
    assert sha(original) == 'b87c98cc201e5f0d2e29941c3dc63fa301bb3572e09d4de2009507f20239f44d'
    migrated, edits, db_rows = migrate_db(original, meta, reader, checksum)
    comp, audit = migrate_compdata(backup/'game-compdata', db_rows)
    files = {'data/db/fifa_ng_db.db': migrated, 'data/db/fifa_ng_db-meta.xml':meta.read_bytes()}
    prefix = 'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata/'
    files.update({prefix+n:b for n,b in comp.items()})
    manifest = []
    for name, content in files.items():
        target = candidate/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        manifest.append(dict(relative=name, sha256=sha(content), size=len(content)))
    audit.update(database_before=sha(original), database_after=sha(migrated),
                 database_edits=edits, files=manifest,
                 runtime_verified=False, source_backup=str(backup),
                 remaining_runtime_audit='Observe 95-game stats and season transition in FIFA: input DB fields have 6-bit matches and 5-bit home/away results; FCE uses separate standings structures, native persistence is not runtime verified')
    (candidate/'repair-manifest.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(dict(candidate=str(candidate), database_edits=len(edits),
                          line_counts=audit['line_counts'], rounds=len(audit['dates']),
                          fixture_count=audit['fixture_count'], files=len(manifest)), indent=2))


if __name__ == '__main__':
    main()
