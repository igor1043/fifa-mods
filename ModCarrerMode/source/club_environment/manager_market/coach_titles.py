"""Read confirmed coach honours without rewarding or rewriting career history."""
from datetime import date


def canonical(rows,today):
    events={}
    for original in rows:
        row=dict(original)
        try:
            won=int(row['game_date']);club=int(row['club_id']);competition=int(row['competition_id'])
            root=int(row.get('root') or competition)
            date(won//10000,won//100%100,won%100)
        except (KeyError,TypeError,ValueError):continue
        if won>today or club<=0 or competition<=0 or not str(row.get('name','')).strip():continue
        # Legacy rows used the activation day (e.g. 20260109) as the season
        # key. It must not create another trophy for the same dated event.
        season=int(row.get('season') or won//10000*10000+101)
        key=(club,root,competition,season//100)
        name=str(row['name']).strip()
        source=row.get('source','legacy_honour')
        rank=0 if source.startswith('completed_native_table:') or source.endswith(':season') else 1 if source in ('legacy_honour','coach_journal') else 2
        quality=(rank,bool(row.get('coach_id')),
                 not name.casefold().startswith(('competição ','competition ')))
        if key not in events or quality>events[key][0]:events[key]=(quality,row)
    return sorted((row for _,row in events.values()),key=lambda row:(-row['game_date'],row['competition_id'],row['club_id']))


def read(market,coach=None,today=None):
    today=today or market.info()['game_date']
    where='game_date<=?';args=(today,)
    if coach is not None:where+=' AND coach_id=?';args+=(coach,)
    legacy=market.rows('honours',where,args)
    if coach is None:
        gallery=market.rows('trophy_history','game_date<=?',(today,))
    else:
        # Also consult the dated events for these few clubs. If a confirmed
        # gallery event belongs to another coach, a stale legacy row cannot
        # grant that same trophy to the selected coach too.
        clubs=sorted({row['club_id'] for row in legacy})
        scope='coach_id=?';values=(coach,)
        if clubs:scope+=' OR club_id IN ('+','.join('?' for _ in clubs)+')';values+=tuple(clubs)
        gallery=market.rows('trophy_history','game_date<=? AND ('+scope+')',(today,*values))
    rows=canonical([*legacy,*gallery],today)
    return [row for row in rows if row.get('coach_id') and (coach is None or row['coach_id']==coach)]
