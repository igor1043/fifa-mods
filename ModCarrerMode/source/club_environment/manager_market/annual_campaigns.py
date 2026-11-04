"""Calendar-year history without resetting appointments or inventing fixtures."""
from collections import defaultdict
import json

KEYS=('hw','hd','hl','aw','ad','al')


def seed(market,campaigns,*,appointments=None,known=None):
    """Upgrade existing spells only when their whole observed span is one year."""
    appointments={a['id']:a for a in (appointments if appointments is not None else market.rows('appointments'))}
    known=known if known is not None else {(r['appointment'],r['year'],r['competition_key']):r for r in market.rows('annual_campaigns')}
    original_known=set(known)
    for r in campaigns:
        a=appointments.get(r['appointment']);year=r['game_date']//10000;key=(r['appointment'],year,r['competition_key'])
        if not a or a['start_date']//10000!=year or key in known:continue
        if '#cycle:' in r['competition_key'] and (r['appointment'],year,r['competition_key'].split('#cycle:')[0]) in original_known:continue
        market.db.execute('INSERT OR IGNORE INTO annual_campaigns VALUES(?,?,?,?,?,?,?,?,?,?)',
            (market.branch,r['appointment'],year,r['competition_key'],r['root'],r['asset'],r['game_date'],r['baseline'],r['counters'],r['source']))
        known[key]=dict(r,year=year)


def observe(market,appointment,row,previous,lifetime_base,*,known=None):
    year=row['date']//10000;key=row['key'];values=[row[k] for k in KEYS]
    if all(k in row for k in ('hgf','hga','agf','aga')):values.extend(row[k] for k in ('hgf','hga','agf','aga'))
    identity=(appointment['id'],year,key)
    old=known.get(identity) if known is not None else market.db.execute('SELECT * FROM annual_campaigns WHERE branch=? AND appointment=? AND year=? AND competition_key=?',
        (market.branch,appointment['id'],year,key)).fetchone()
    if old and old['game_date']>row['date']:return
    if old:
        base=json.loads(old['baseline']);last=json.loads(old['counters'])
        if row['date']>old['game_date'] and sum(values[:6])<sum(last[:6]):
            archived=dict(old);archived['competition_key']=key+'#cycle:'+str(row['date'])
            market.add('annual_campaigns',{k:v for k,v in archived.items() if k!='branch'})
            base=[0]*len(values)
        elif len(values)>len(base):
            initial=appointment['origin'] in ('Vínculo inicial desde o início da carreira','Estimado a partir da ativação do mod') and appointment['start_date']//10000==year
            base.extend([0]*(len(values)-len(base)) if initial else values[len(base):])
    elif previous and previous['game_date']//10000<year:
        last=json.loads(previous['counters'])
        base=last[:] if sum(values[:6])>=sum(last[:6]) else [0]*len(values)
        if len(values)>len(base):base.extend(values[len(base):])
    elif appointment['start_date']//10000<year and not previous:
        # No last-year observation: do not call an entire accumulated foreign
        # league table this year's matches. Dated scores are still displayed.
        base=values[:]
    else:base=lifetime_base[:]
    market.db.execute('INSERT OR REPLACE INTO annual_campaigns VALUES(?,?,?,?,?,?,?,?,?,?)',
        (market.branch,appointment['id'],year,key,row['root'],row['asset'],row['date'],json.dumps(base),json.dumps(values),row['source']))
    if known is not None:known[identity]=dict(appointment=appointment['id'],year=year,competition_key=key,root=row['root'],asset=row['asset'],game_date=row['date'],baseline=json.dumps(base),counters=json.dumps(values),source=row['source'])


def project(appointments,results,annual,clubs,today):
    own={a['id']:a for a in appointments};buckets={}
    def bucket(club,year,root,asset):
        return buckets.setdefault((club,year,root,asset),dict(actual=[0]*6,goals=[0]*4,aggregate=[0]*6,aggregate_goals=[0]*4,has_aggregate=False,has_goals=False))
    for r in results:
        for side,offset in (('home',0),('away',3)):
            if r.get(side+'_appointment') not in own:continue
            gf,ga=(r['hg'],r['ag']) if side=='home' else (r['ag'],r['hg'])
            b=bucket(r[side],r['game_date']//10000,r['root'],r['competition_id'])
            b['actual'][offset+(0 if gf>ga else 1 if gf==ga else 2)]+=1
            at=0 if side=='home' else 2;b['goals'][at]+=gf;b['goals'][at+1]+=ga
    native={(r['appointment'],r['year'],r['asset']) for r in annual if r['root'] and r['appointment'] in own}
    for r in annual:
        a=own.get(r['appointment'])
        if not a or r['year']>today//10000 or (not r['root'] and (r['appointment'],r['year'],r['asset']) in native):continue
        b=bucket(a['club_id'],r['year'],r['root'],r['asset']);values=json.loads(r['counters']);base=json.loads(r['baseline']);b['has_aggregate']=True
        for i in range(6):b['aggregate'][i]+=values[i]-base[i]
        if len(values)==len(base)==10:
            b['has_goals']=True
            for i in range(4):b['aggregate_goals'][i]+=max(0,values[i+6]-base[i+6])
    totals={}
    for (club,year,root,asset),b in buckets.items():
        out=totals.setdefault((club,year),dict(club=club,year=year,name=clubs.get(club,{}).get('name','Clube'),counts=[0]*6,goals=[0]*4,goals_known=True))
        counts=b['aggregate'] if b['has_aggregate'] and sum(b['aggregate'])>=sum(b['actual']) else b['actual']
        for i in range(6):out['counts'][i]+=max(0,counts[i])
        goals=b['aggregate_goals'] if b['has_goals'] and sum(counts)>sum(b['actual']) else b['goals']
        out['goals_known'] &= b['has_goals'] or sum(counts)<=sum(b['actual'])
        for i in range(4):out['goals'][i]+=goals[i]
    def stats(c,g,known):
        wins=c[0]+c[3];draws=c[1]+c[4];losses=c[2]+c[5];games=wins+draws+losses
        return dict(games=games,wins=wins,draws=draws,losses=losses,points=3*wins+draws,gf=g[0]+g[2] if known else -1,ga=g[1]+g[3] if known else -1,percentage=round(100*(3*wins+draws)/(3*games),1) if games else 0)
    result=[]
    for out in totals.values():
        c=out.pop('counts');g=out.pop('goals');known=out.pop('goals_known');out['total']=stats(c,g,known)
        out['home']=stats(c[:3]+[0]*3,g[:2]+[0]*2,known);out['away']=stats([0]*3+c[3:],[0]*2+g[2:],known)
        result.append(out)
    return sorted(result,key=lambda r:(-r['year'],r['name']))


def cards(years,today):
    def number(n):return str(n) if n>=0 else '—'
    result=[]
    for r in years:
        s=r['total'];hs=r['home'];aws=r['away']
        result.append([str(r['year'])+' · '+r['name'],'crest_'+str(r['club']),str(r['year']),
            'Resultados por ano civil','Em andamento' if r['year']==today//10000 else 'Ano anterior',
            f"{s['games']} jogos · {s['wins']} V · {s['draws']} E · {s['losses']} D",s['percentage'],
            str(hs['games'])+' jogos em casa',hs['percentage'],str(aws['games'])+' jogos fora',aws['percentage'],
            'Histórico anual',f"{s['percentage']:.1f}%".replace('.',',')]+[number(s[k]) for k in ('games','wins','draws','losses','gf','ga')])
    return result
