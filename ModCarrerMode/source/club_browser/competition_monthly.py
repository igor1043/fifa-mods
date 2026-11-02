"""Monthly awards from dated evidence and career-isolated cumulative snapshots.

Only this additional sidecar is written. Native saves and the coach ledger are
read-only; manager-market branch/checkpoint IDs prevent mixing career loads.
"""
from pathlib import Path
from contextlib import closing
from collections import defaultdict
import hashlib,json,os,sqlite3,zlib


def totals(snapshot):
    nodes={int(r[0]):r for r in snapshot.get('nodes',[]) if len(r)>=3}
    def root(node):
        seen=set()
        while node in nodes and node not in seen:
            seen.add(node);row=nodes[node]
            if row[2]==3:return node
            node=row[1]
        return 0
    unique={}
    for row in snapshot.get('stats',[]):
        if len(row)<10:continue
        sid,comp,club,player,*values=map(int,row[:10]);r=root(comp)
        if not r or min(club,player)<=0 or any(v<0 for v in values[:5]):continue
        key=r,club,player,comp;value=[sid,*values]
        if key not in unique or tuple(value[1:3]+value[:1])>tuple(unique[key][1:3]+unique[key][:1]):unique[key]=value
    by=defaultdict(list)
    for (r,club,player,comp),value in unique.items():by[r,club,player].append((comp,value))
    rows=[]
    for (r,club,player),items in sorted(by.items()):
        selected=[v for c,v in items if c==r] or [v for _,v in items]
        rows.append([r,club,player,*[sum(v[i] for v in selected) for i in range(1,6)],int(all(v[6]&2 for v in selected))])
    games=[]
    for f in snapshot.get('fixtures',[]):
        if len(f)>=10 and f[9] and f[3]<=snapshot['date']:
            r=root(f[1])
            if r:games.append([r,f[0],f[3],f[5],f[6]])
    return dict(date=int(snapshot['date']),rows=rows,games=sorted(games))


def store_path(database):return Path(database).with_name('competition_monthly.sqlite3')


def capture(database,branch,snapshot,digest='',*,checkpoint=False):
    path=store_path(database);path.parent.mkdir(parents=True,exist_ok=True)
    value=totals(snapshot);raw=json.dumps(value,separators=(',',':')).encode();signature=hashlib.sha256(raw).hexdigest()
    with closing(sqlite3.connect(path,timeout=.25)) as db, db:
        db.executescript('CREATE TABLE IF NOT EXISTS observations_v2(branch TEXT,day INT,signature TEXT,payload BLOB,PRIMARY KEY(branch,day,signature));CREATE TABLE IF NOT EXISTS checkpoints(save_hash TEXT PRIMARY KEY,payload BLOB);')
        known=db.execute('SELECT 1 FROM observations_v2 WHERE branch=? LIMIT 1',(branch,)).fetchone()
        if not known and digest:
            saved=db.execute('SELECT payload FROM checkpoints WHERE save_hash=?',(digest,)).fetchone()
            if saved:
                for row in json.loads(zlib.decompress(saved[0])):
                    if row['date']<=value['date']:
                        body=json.dumps(row,separators=(',',':')).encode();db.execute('INSERT OR IGNORE INTO observations_v2 VALUES(?,?,?,?)',(branch,row['date'],hashlib.sha256(body).hexdigest(),zlib.compress(body)))
        old=db.execute('SELECT 1 FROM observations_v2 WHERE branch=? AND day=? AND signature=?',(branch,value['date'],signature)).fetchone()
        if not old:db.execute('INSERT OR IGNORE INTO observations_v2 VALUES(?,?,?,?)',(branch,value['date'],signature,zlib.compress(raw)))
        # The current award needs three anchors, not a full copy of every FCE
        # publication: last observation before the month, first in the month,
        # and the latest. Saved checkpoints retain their own immutable anchors.
        first=value['date']//100*100+1
        anchors=[r[0] for r in db.execute('SELECT rowid FROM observations_v2 WHERE branch=? AND day<? ORDER BY day DESC,rowid DESC LIMIT 1',(branch,first))]
        anchors.extend(r[0] for r in db.execute('SELECT rowid FROM observations_v2 WHERE branch=? AND day>=? ORDER BY day,rowid LIMIT 1',(branch,first)))
        anchors.extend(r[0] for r in db.execute('SELECT rowid FROM observations_v2 WHERE branch=? ORDER BY day DESC,rowid DESC LIMIT 1',(branch,)))
        if anchors:db.execute('DELETE FROM observations_v2 WHERE branch=? AND rowid NOT IN ('+','.join('?' for _ in anchors)+')',(branch,*anchors))
        # A saved checkpoint owns its captured evidence. Reopening the same
        # native save in a new market branch restores that evidence, not future
        # unsaved observations_v2 from the branch that was left behind.
        if checkpoint and digest:
            content=[json.loads(zlib.decompress(r[0])) for r in db.execute('SELECT payload FROM observations_v2 WHERE branch=? AND day<=? ORDER BY day,rowid',(branch,value['date']))]
            db.execute('INSERT OR REPLACE INTO checkpoints VALUES(?,?)',(digest,zlib.compress(json.dumps(content,separators=(',',':')).encode())))


def player_awards(baseline,latest,today,players,display,teams):
    if not baseline or not latest:return {}
    month=today//100;start=month*100+1;before={tuple(r[:3]):r for r in baseline['rows']};changes=defaultdict(list)
    old_games={tuple(g) for g in baseline['games']};new_games=[g for g in latest['games'] if tuple(g) not in old_games]
    mixed={g[0] for g in new_games if g[2]//100!=month}
    for row in latest['rows']:
        root,club,player=row[:3]
        if root in mixed or player not in players:continue
        old=before.get((root,club,player),[root,club,player,0,0,0,0,0,1])
        games,minutes,goals,assists,rating=[a-b for a,b in zip(row[3:8],old[3:8])]
        dated=sum(g[0]==root and club in g[3:5] for g in new_games)
        if not row[8] or not old[8] or games<=0 or games>dated or min(minutes,goals,assists,rating)<0 or not 0<rating<=games*100:continue
        average=rating/(10*games);score=(average*games+12)/(games+2)+min(.75,.15*goals+.10*assists)
        changes[root].append(dict(id=player,club=club,name=display(players[player]),clubName=teams.get(club,'Clube'),games=games,average=average,score=score,goals=goals,assists=assists))
    out={}
    for root,rows in changes.items():
        ranked=sorted(rows,key=lambda r:(-r['score'],-r['games'],-r['average'],r['id']));winner=ranked[0]
        winner.update(available=True,month=month,partial=baseline['date']>=start,fromDate=baseline['date'],
                      note=('Acompanhado desde '+stamp(baseline['date']) if baseline['date']>=start else 'Desempenho deste mês'))
        out[root]=winner
    return out


def stamp(day):return f'{day%100:02d}/{day//100%100:02d}/{day//10000}'


def project(game,save,snapshot,roots,players,display,teams,save_hash=None):
    empty={root:dict(month=snapshot['date']//100,player=dict(available=False,note='Aguardando histórico de notas deste mês'),coach=dict(available=False,note='Sem partidas com técnico identificado no mês')) for root in roots}
    try:
        state=json.loads((Path(game)/'ModCarrerMode/runtime/manager_market/state_ready.json').read_text(encoding='utf8'))
        normal=lambda p:os.path.normcase(os.path.abspath(str(p).removeprefix('\\\\?\\')))
        if state.get('pid')!=snapshot.get('pid') or str(state.get('created'))!=str(snapshot.get('processCreated100ns')) or state.get('club')!=snapshot['club'] or state['date']>snapshot['date'] or normal(state['save'])!=normal(save):return empty
        if save_hash is not None and state.get('digest')!=save_hash:return empty
        database=Path(str(state['database']).removeprefix('\\\\?\\'));branch=state['branch'];today=snapshot['date'];first=today//100*100+1
        with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True,timeout=.25)) as db:
            db.row_factory=sqlite3.Row
            coaches={r['coach_id']:dict(r) for r in db.execute('SELECT coach_id,name,image FROM coaches WHERE branch=?',(branch,))}
            scores=defaultdict(lambda:dict(games=0,wins=0,draws=0,gf=0,ga=0))
            for m in db.execute('SELECT root,game_date,home,away,hg,ag,home_coach,away_coach FROM results WHERE branch=? AND game_date BETWEEN ? AND ?',(branch,first,today)):
                if m['root'] not in roots:continue
                for club,coach,gf,ga in ((m['home'],m['home_coach'],m['hg'],m['ag']),(m['away'],m['away_coach'],m['ag'],m['hg'])):
                    if coach not in coaches or gf is None or ga is None:continue
                    s=scores[m['root'],club,coach];s['games']+=1;s['wins']+=gf>ga;s['draws']+=gf==ga;s['gf']+=gf;s['ga']+=ga
            for root in roots:
                candidates=[(key,s) for key,s in scores.items() if key[0]==root]
                if candidates:
                    (r,club,coach),s=max(candidates,key=lambda v:((v[1]['wins']*3+v[1]['draws']+3)/(v[1]['games']+2),v[1]['games'],v[1]['gf']-v[1]['ga'],-v[0][1],v[0][2]))
                    c=coaches[coach];empty[root]['coach']=dict(available=True,name=c['name'],image=c.get('image',''),club=club,clubName=teams.get(club,'Clube'),games=s['games'],wins=s['wins'],draws=s['draws'],points=s['wins']*3+s['draws'],note='Campanha do mês · partidas com técnico registrado')
        path=store_path(database)
        if path.is_file():
            with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.25)) as db:
                old=db.execute('SELECT payload FROM observations_v2 WHERE branch=? AND day<? ORDER BY day DESC,rowid DESC LIMIT 1',(branch,first)).fetchone()
                if old is None:old=db.execute('SELECT payload FROM observations_v2 WHERE branch=? AND day<=? ORDER BY day,rowid LIMIT 1',(branch,today)).fetchone()
                latest=db.execute('SELECT payload FROM observations_v2 WHERE branch=? AND day<=? ORDER BY day DESC,rowid DESC LIMIT 1',(branch,today)).fetchone()
                partial=db.execute('SELECT payload FROM observations_v2 WHERE branch=? AND day BETWEEN ? AND ? ORDER BY day,rowid LIMIT 1',(branch,first,today)).fetchone()
            p=player_awards(json.loads(zlib.decompress(old[0])) if old else None,json.loads(zlib.decompress(latest[0])) if latest else None,today,players,display,teams)
            # A calendar jump can cross a month without a boundary observation.
            # Start a clearly labelled partial month rather than attributing
            # late games from the previous month to the current award.
            fallback=player_awards(json.loads(zlib.decompress(partial[0])) if partial else None,json.loads(zlib.decompress(latest[0])) if latest else None,today,players,display,teams)
            for root,award in fallback.items():p.setdefault(root,award)
            for root,award in p.items():
                if root in empty:empty[root]['player']=award
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error,zlib.error):return empty
    return empty
