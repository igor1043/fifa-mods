"""Save-bound publication of FIFA's own foreign standings calculation.

The engine synthesizes these tables when no scored FCE campaign was retained.
They are derived evidence, not invented fixtures or additional competitions.
"""
from pathlib import Path
import hashlib,json,os

def ready(game,saved,profile,today,snapshot):
    """Wait for the owner-thread batch before displaying an incomplete career."""
    try:
        path=Path(game)/'ModCarrerMode/runtime/career_derived_standings.json'
        if path.stat().st_size>8*1024*1024:return False
        d=json.loads(path.read_text(encoding='utf8'));save=Path(saved['path']).resolve();st=save.stat()
        return (snapshot.get('schema')==3 and snapshot.get('pid')==saved['pid']
            and snapshot.get('processCreated100ns')==saved['process_created_100ns'] and snapshot.get('date')==today
            and Path(snapshot['savePath']).resolve()==save and snapshot.get('saveSize')==st.st_size
            and snapshot.get('saveWriteTime100ns')==st.st_mtime_ns//100+116444736000000000
            and d.get('schema')==1 and d.get('pid')==saved['pid'] and d.get('created')==saved['process_created_100ns']
            and d.get('epoch')==snapshot.get('fceContextEpoch')==profile.get('context_epoch') and d.get('date')==today
            and isinstance(d.get('rows'),list))
    except (OSError,ValueError,KeyError,TypeError):return False

def augment(game,save,raw,snapshot,today=None,pid=None,created=None,epoch=None):
    save=Path(save).resolve();today=today or snapshot['date'];digest=hashlib.sha256(raw).hexdigest()
    cache=save.parent.parent/'server16_competition_views'/(digest+'_'+str(today)+'.json')
    publication=None
    if pid is not None and created is not None:
        try:
            from career_publication import read
            candidate=read(game,dict(path=save,pid=pid,process_created_100ns=created),today,epoch=epoch)
            if candidate is not None:
                publication=candidate
                # The background calculation publishes independently of the
                # Statistics UI, so opening a custom screen cannot stall it.
                try:
                    extra=Path(game)/'ModCarrerMode/runtime/career_derived_standings.json'
                    if extra.stat().st_size>8*1024*1024:raise ValueError('Oversized supplement')
                    derived=json.loads(extra.read_text(encoding='utf8'))
                    if (derived.get('schema')==1 and derived.get('pid')==pid and derived.get('created')==created
                        and derived.get('date')==today and derived.get('epoch')==candidate.get('fceContextEpoch') and type(derived.get('epoch'))==int):
                        publication=dict(candidate,derivedStandings=derived['rows'])
                except (OSError,ValueError,KeyError,TypeError):pass
        except (OSError,ValueError,KeyError,TypeError):pass
    if publication is None and pid is None and created is None:
        try:
            data=json.loads(cache.read_text(encoding='utf8'))
            if data.get('save_hash')==digest and data.get('date')==today:publication=data['publication']
        except (OSError,ValueError,KeyError,TypeError):pass
    if publication is None:return snapshot
    # Validate the entire supplement before accepting any row. Every slot,
    # club and competition must exist in this career's competition graph.
    try:
        slots={r[0]:(r[1],r[2]) for r in publication['standings'] if len(r)==10}
        nodes={r[0]:r for r in publication['nodes'] if len(r)==5}
        supplements={}
        for r in publication.get('derivedStandings',[]):
            if len(r)!=14 or any(type(v)!=int for v in r) or min(r)<0:raise ValueError('Invalid derived campaign')
            if slots.get(r[0])!=(r[1],r[2]) or r[1] not in nodes:raise ValueError('Different career graph')
            if sum(r[3:9])!=r[9] or max(r[3:9])>255 or max(r[10:])>65535:raise ValueError('Invalid counters')
            if r[0] in supplements:raise ValueError('Duplicate standing slot')
            supplements[r[0]]=r
        result=dict(snapshot,date=today)
        # Current native scores are also authoritative for unsaved progress.
        result['standings']=[supplements.get(r[0],r)[:10] for r in publication['standings'] if len(r)==10]
        result['nodes']=publication['nodes'];result['fixtures']=publication['fixtures'];result['stats']=publication.get('stats',[])
        # Disk goal totals belong to disk counters. A January zero must not be
        # attached to a December row merely because the standing ID survived.
        saved_rows={r[0]:r for r in snapshot['standings']}
        result['standingGoals']={str(r[0]):snapshot['standingGoals'][str(r[0])] for r in publication['standings']
            if saved_rows.get(r[0])==r and str(r[0]) in snapshot.get('standingGoals',{})}
        result['standingGoals'].update({str(k):v[10:] for k,v in supplements.items()})
        result['derived_slots']=sorted(supplements);result['source']='save_bound_native'
        if supplements:
            try:
                encoded=json.dumps(dict(save_hash=digest,date=today,publication=publication),separators=(',',':')).encode('utf8')
                if not cache.exists() or cache.read_bytes()!=encoded:
                    cache.parent.mkdir(parents=True,exist_ok=True)
                    temporary=cache.with_name(cache.name+'.'+str(os.getpid())+'.tmp')
                    temporary.write_bytes(encoded);os.replace(temporary,cache)
            except OSError:pass  # A cache write cannot make a valid profile fail.
        return result
    except (ValueError,KeyError,TypeError):return snapshot
