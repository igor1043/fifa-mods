"""Current career availability and observed injury countdown, no save writes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,re,math
import portable_paths as portable


def remaining_days(injury,today):
    if injury.get('source')=='native_InjuryList':
        text=injury.get('return','').casefold()
        match=re.search(r'(\d+)\s*(dias?|days?|semanas?|weeks?|meses?|mês|months?)',text)
        if match:
            n=int(match[1]);unit=match[2];return n*(7 if unit.startswith(('seman','week')) else 30 if unit.startswith(('m','month')) else 1)
        date=re.search(r'\b(\d{2}/\d{2}/\d{4})\b',text)
        if date:
            try:return max(0,(datetime.strptime(date[1],'%d/%m/%Y')-datetime.strptime(str(today),'%Y%m%d')).days)
            except ValueError:pass
    weeks=injury.get('weeks',0)
    return weeks*7 if type(weeks)==int and 0<weeks<=35 else None


def enrich(context,snapshot,roster,rows):
    medical=context['medical'];players={r.value('playerid'):r for r in rows('players')};injured={p['player']:p for p in medical['players']}
    today=context['date'];calendar=rows('career_calendar');start=calendar[0].value('startdate') if len(calendar)==1 and 'startdate' in calendar[0].fields else 0
    key=hashlib.sha256((str(Path(snapshot['savePath']).resolve()).casefold()+f'|{context["club"]}|{start}').encode()).hexdigest()[:20]
    path=portable.ROOM/'runtime'/f'medical_observed_r77_{key}.json'
    try:
        if path.stat().st_size>256000:raise ValueError('Oversized history')
        state=json.loads(path.read_text(encoding='utf8'))
        if state.get('schema')!=1 or state.get('scope')!=key or state.get('date',0)>today or not isinstance(state.get('episodes'),dict) or not isinstance(state.get('history'),list):raise ValueError('Different career timeline')
    except (OSError,ValueError,TypeError):state=dict(schema=1,scope=key,date=today,episodes={},history=[])
    episodes=state['episodes'];active=set();condition=[]
    for p in roster:
        record=players.get(p['id']);stamina=record.value('stamina') if record and 'stamina' in record.fields else None
        condition.append(dict(player=p['id'],name=p['name'],stamina=stamina if type(stamina)==int and 0<=stamina<=99 else None,available=p['id'] not in injured))
        injury=injured.get(p['id'])
        if not injury:continue
        ident=str(p['id']);active.add(ident);remaining=remaining_days(injury,today)
        old=episodes.get(ident)
        if old is None or (remaining is not None and old.get('baseline') is not None and remaining>old['baseline']):
            old=dict(first=today,name=p['name'],injury=injury['injury'],baseline=remaining);episodes[ident]=old
        if old.get('baseline') is None and remaining is not None:old['baseline']=remaining
        baseline=old.get('baseline');injury['observedSince']=old['first']
        injury['recovery']=round(max(0,min(100,100*(baseline-remaining)/baseline))) if baseline and remaining is not None else None
        injury['remainingDays']=remaining
    for ident in list(episodes):
        if ident not in active:
            old=episodes.pop(ident);state['history'].append(dict(player=int(ident),name=old['name'],injury=old['injury'],first=old['first'],last=today))
    state.update(date=today,history=state['history'][-48:]);path.parent.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(state,ensure_ascii=False,sort_keys=True)
    if not path.exists() or path.read_text(encoding='utf8')!=encoded:
        temp=path.with_name(path.name+'.'+str(os.getpid())+'.tmp');temp.write_text(encoded,encoding='utf8');os.replace(temp,path)
    values=[p['stamina'] for p in condition if p['stamina'] is not None]
    medical.update(rosterCount=len(roster),availableCount=len(roster)-len(injured),unavailableCount=len(injured),
        condition=condition,averageStamina=round(sum(values)/len(values),1) if values else None,observedHistory=state['history'][-5:],
        recoverySource='Observed remaining-time countdown, not a medical measurement',historyScope=key,
        fatigue=None,workload=None,injuryRisk=None)
    medical['pageSize']=max(6,math.ceil(len(injured)/6))
    medical['pages']=max(1,math.ceil(len(injured)/medical['pageSize']))
    return medical
