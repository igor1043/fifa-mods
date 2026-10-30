"""Publish only current, complete rankings; bounded automatic retry on late RAM."""
from pathlib import Path
import json,time
from ranking_data import project,snapshot_key
from season_stats import current
from server16_py.career_context import competition_session

def tsv(data,seq):
    coverage=data.get('coverage',{})
    rows=[['H',1,seq,data['club'],data['date'],data['national'],data['clubName'],data['matches'],data['years'],data['referenceDate'],
        coverage.get('live_league_tables',coverage.get('leagues_with_tables',0)),coverage.get('clubs_with_games',0),data.get('coachMatches',0),data.get('coachMine',0),data.get('coachBranchDate',0)]]
    for kind in ('clubs','nations','coaches'):
        for r in data['groups'][kind]:
            rows.append(['T',kind,r['id'],r['nation'],r['confederation'],r['rank'],r['movement'],r['name'],r['countryName'],r['leagueName'],r['points'],r['initial'],r['matchPoints'],r['titlePoints'],r['games'],r['wins'],r['draws'],r['losses'],r['titles'],''.join(r['form']),r.get('campaignPoints',0),r.get('campaignGames',0)])
            for m in r['recent']:rows.append(['M',kind,r['id'],m['date'],m['opponent'],m['score'],m['delta'],m['importance']])
    def value(v):return str(v).replace('\t',' ').replace('\n',' ').replace('\r',' ')
    return ('\n'.join('\t'.join(map(value,r)) for r in rows)+'\n').encode('utf8')

def generate(game,folder,req,memory,cache):
    from lineup_worker import observe,request,atomic,publish
    saved,context=observe(memory,game);began=time.monotonic();snapshot=None
    while time.monotonic()-began<12:
        if request(folder/'request.tsv',req['pid'])!=req:return False
        snapshot=current(game,memory,saved,competition_session(memory,True))
        if snapshot:break
        after,ctx=observe(memory,game)
        if ctx!=context or (after['path'],after['mtime_ns'])!=(saved['path'],saved['mtime_ns']):break
        time.sleep(.1)
    if not snapshot:
        publish(folder,req,'error',kind='rankings',retry=1,message='Aguardando os resultados atuais da carreira.');return True
    if snapshot['club']!=req['club']:
        publish(folder,req,'error',kind='rankings',retry=1,message='A carreira mudou. Atualizando o ranking.');return True
    from career_results import live_leagues
    signature=snapshot_key(snapshot);live=live_leagues(game,saved,competition_session(memory,True),snapshot['date']);data=project(game,Path(saved['path']),snapshot,cache,live,req['pid'])
    after,ctx=observe(memory,game);latest_profile=competition_session(memory,True);latest=current(game,memory,after,latest_profile)
    latest_live=live_leagues(game,after,latest_profile,latest['date']) if latest else None
    if request(folder/'request.tsv',req['pid'])!=req:return False
    if ctx!=context or (after['path'],after['mtime_ns'])!=(saved['path'],saved['mtime_ns']) or latest is None or snapshot_key(latest)!=signature or (latest_live and (not live or latest_live['revision']!=live['revision'])):
        publish(folder,req,'error',kind='rankings',retry=1,message='Novos resultados recebidos. Atualizando o ranking.');return True
    atomic(folder/'rankings.tsv',tsv(data,req['seq']))
    atomic(folder/'rankings.json',json.dumps(data,ensure_ascii=False,indent=2).encode('utf8'))
    publish(folder,req,'ready',kind='rankings',date=data['date'],matches=data['matches'])
    return True
