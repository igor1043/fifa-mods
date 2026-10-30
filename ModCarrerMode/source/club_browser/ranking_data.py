"""Rankings from the installed patch, saved schedule and validated live results.

No FIFA database/table is patched and no native save is ever opened for writing.
"""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json
from lineup_data import ProjectionCache
from world_catalog import build as catalog
from competition_schedule import read_schedule
from competition_formats import read_formats
from ranking_core import calculate,confirmed_titles,reconcile

def snapshot_key(snapshot):
    # generation is a polling counter, not a new sporting result.
    return hashlib.sha256(json.dumps({k:snapshot.get(k) for k in ('club','date','fixtures','nodes','standings')},sort_keys=True,separators=(',',':')).encode()).hexdigest()

def competition_metadata(game,schedule,teams,extra=()):
    folder=Path(game)/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata'
    def read(name):return list(csv.reader((folder/(name+'.txt')).read_text(encoding='utf-8-sig').splitlines()))
    objects={int(r[0]):r for r in read('compobj') if len(r)>=5 and r[0].isdigit()}
    settings=defaultdict(dict)
    for r in read('settings'):
        if len(r)>=3 and r[0].isdigit():settings[int(r[0])][r[1]]=r[2]
    members=defaultdict(set)
    for m in schedule:members[m['root']].update((m['home'],m['away']))
    for p in extra:
        if p['root']>0:members[p['root']].add(p['club'])
    metadata={}
    for root,ids in members.items():
        row=objects.get(root)
        asset=next((m.get('asset') for m in schedule if m['root']==root and m.get('asset')),0)
        if not asset:asset=next((p['asset'] for p in extra if p['root']==root),0)
        if not row or row[1]!='3' or (asset and row[2]!='C'+str(asset)):
            candidates=[r for r in objects.values() if r[1]=='3' and r[2]=='C'+str(asset)]
            row=candidates[0] if len(candidates)==1 else None
        metadata_root=int(row[0]) if row else root
        parent=objects.get(int(row[4])) if row else None
        scope='domestic' if parent and parent[1]=='2' else 'continental' if parent and parent[1]=='1' else 'world'
        ratings=[teams[t]['overall'] for t in ids if t in teams and teams[t].get('overall',0)>0]
        metadata[root]=dict(type=settings[metadata_root].get('comp_type','NONE'),scope=scope,strength=sum(ratings)/len(ratings) if ratings else 65)
    return metadata

def merge_schedule(saved,snapshot,formats):
    nodes={r[0]:r for r in snapshot['nodes'] if len(r)==5}
    def root(n):
        seen=set()
        while n in nodes and n not in seen:
            seen.add(n);r=nodes[n]
            if r[2]==3:return r[0],r[3]
            n=r[1]
        return None
    matches={(m['date'],m['root'],m['id']):dict(m) for m in saved}
    for f in snapshot['fixtures']:
        if len(f)<10:continue
        ident=root(f[1])
        if not ident:continue
        key=(f[3],ident[0],f[0]);old=matches.get(key)
        if old and (old['home'],old['away'])!=(f[5],f[6]):continue
        phase=f[2];n=nodes.get(phase)
        if n and n[2]==5:phase=n[1]
        kind=formats.get(phase,{}).get('kind',nodes.get(phase,[0,0,0,0,0])[4])
        matches[key]=dict(old or {},id=f[0],date=f[3],root=ident[0],asset=ident[1],stage=(old or {}).get('stage',phase),stageKind=(old or {}).get('stageKind',kind),home=f[5],away=f[6],homeScore=f[7] if f[9] else None,awayScore=f[8] if f[9] else None,played=bool(f[9]))
    return list(matches.values())

def project(game,save,snapshot,cache=None,live=None,process_pid=0):
    game=Path(game);cache=cache or ProjectionCache();raw,dbs,base=cache.load(game,Path(save))
    rules=json.loads((game/'ModCarrerMode/data/club_browser/ranking_rules.json').read_text(encoding='utf8'))
    if rules.get('schema')!=1 or not 1<=rules.get('years',0)<=10:raise ValueError('Regras do ranking incompatíveis.')
    rows,audit=catalog(game,base)
    excluded={int(value) for value in rules.get('excluded_clubs',[]) if str(value).isdigit()}
    excluded_names=[r['name'] for r in rows if r['kind']=='clubs' and r['id'] in excluded]
    rows=[r for r in rows if not (r['kind']=='clubs' and r['id'] in excluded)]
    teams={r['id']:r for r in rows}
    # Display edited/promoted teams from this save while keeping the baseline
    # strength anchored in the installed DB, so every refresh has the same seed.
    for db in dbs:
        if 'teams' in db.tables:
            for t in cache.table(db,'teams',['teamid','teamname']):
                if t['teamid'] in teams and t['teamname']:teams[t['teamid']]['name']=t['teamname']
    formats=read_formats(game);schedule=merge_schedule(read_schedule(raw,formats),snapshot,formats)
    from career_results import from_career
    evidence=from_career(game,cache,dbs,base,snapshot,schedule,live)
    metadata=competition_metadata(game,schedule,teams,evidence['performance'])
    titles=confirmed_titles(schedule,teams,metadata,snapshot['date'],formats)
    result=calculate(rows,schedule,metadata,snapshot['date'],rules,titles)
    result=reconcile(result,schedule,evidence,metadata,rules)
    from coach_ranking import project as project_coaches
    coaches=project_coaches(game,save,snapshot,pid=process_pid,rules=rules,teams=teams)
    result['groups']['coaches']=coaches['rows']
    result['coachMine']=coaches['mine']
    result['coachMatches']=coaches['matches']
    result['coachBranchDate']=coaches['branch_date']
    audit['excludedFromClubRanking']=excluded_names
    result.update(leagueTables=evidence['tables'],tableDates=evidence['table_dates'],liveLeagueRevision=evidence['liveRevision'])
    club=snapshot['club'];nation=teams.get(club,{}).get('nation',0)
    national=next((r['id'] for r in rows if r['kind']=='nations' and r['nation']==nation),0)
    # A manager who also coaches a national side focuses that actual side.
    for db in dbs:
        if 'career_users' not in db.tables:continue
        users=cache.table(db,'career_users',['clubteamid','nationalteamid','usertype'])
        own=[r for r in users if r['clubteamid']==club and r['usertype']==1 and r['nationalteamid'] in teams and teams[r['nationalteamid']]['kind']=='nations']
        if len(own)==1:national=own[0]['nationalteamid']
    result.update(club=club,clubName=teams.get(club,{}).get('name','Clube da carreira'),national=national,audit=audit,years=rules['years'],saveHash=cache.save_hash,source='active-career-save-and-live-results')
    return result
