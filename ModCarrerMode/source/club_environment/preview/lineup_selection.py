"""Keep valid saved starters; repair a probable XI from this club's real roster.

No save is modified. A repaired lineup is explicitly marked probable; the
existing StartingXIDP can still replace the user's projection with the live XI.
"""
import math

DEFAULT=((0,.5,.04),(3,.85,.25),(5,.65,.23),(6,.35,.23),(7,.15,.25),
         (12,.85,.55),(14,.65,.5),(15,.35,.5),(16,.15,.55),(24,.65,.85),(25,.35,.85))

def value(row,key,default=0):
    return row.value(key) if key in row.fields else default

def family(position):return 0 if position==0 else 1 if position<9 else 2 if position<20 else 3

def select(team,sheets,defaults,players,members):
    members=set(members)&players.keys()
    options=[(0 if value(r,'isfavourite') else 1,'teamsheets',r) for r in sheets if value(r,'teamid')==team]
    options += [(2,'default_teamsheets',r) for r in defaults if value(r,'teamid')==team]
    def ids(row):return [value(row,'playerid'+str(i),-1) for i in range(11)]
    def good(row):return len(set(ids(row))&members)
    options.sort(key=lambda item:(item[0],-good(item[2]),ids(item[2])))
    full=next((item for item in options if good(item[2])==11),None)
    selected=full or (max(options,key=lambda item:(good(item[2]),-item[0])) if options else None)
    row=selected[2] if selected else None;used=set();slots=[];repaired=not bool(full)
    for i,(position,x,y) in enumerate(DEFAULT):
        position=value(row,'position'+str(i),position) if row else position
        if not isinstance(position,int) or not 0<=position<28:position=DEFAULT[i][0];repaired=True
        xx=value(row,'offset'+str(i)+'x',x) if row else x;yy=value(row,'offset'+str(i)+'y',y) if row else y
        if not all(isinstance(n,(int,float)) and math.isfinite(n) and 0<=n<=1 for n in (xx,yy)):xx,yy=x,y;repaired=True
        pid=value(row,'playerid'+str(i),-1) if row else -1
        if pid not in members or pid in used:pid=None
        else:used.add(pid)
        slots.append(dict(id=pid,position=position,x=xx,y=yy))
    # Reserve every valid saved starter before choosing replacements, so an
    # early vacancy never steals a valid player from a later saved position.
    for slot in slots:
        if slot['id'] is not None:continue
        available=members-used
        if not available:break
        def rank(pid):
            p=players[pid];position=value(p,'preferredposition1',slot['position'])
            return (position!=slot['position'],family(position)!=family(slot['position']),
                    position==0 if slot['position'] else position!=0,-value(p,'overallrating'),pid)
        pid=min(available,key=rank);slot['id']=pid;used.add(pid)
    if any(slot['id'] is None for slot in slots):slots=[]
    return dict(slots=slots,probable=repaired,source='probable-roster' if repaired else selected[1])
