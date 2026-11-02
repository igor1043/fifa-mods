"""Annual financial history; reports never move money or overwrite old terms."""
from copy import deepcopy


def period(book,day,context_season=None,*,remember=True):
    periods=book.setdefault('periods',{}) if remember else dict(book.get('periods',{}))
    start_year=book['start']//10000
    original=book.get('initial_season',book['season'])
    periods.setdefault(str(start_year),original if original//10000==start_year else start_year*10000+101)
    year=day//10000;key=str(year)
    if key not in periods:
        periods[key]=year*10000+101
    return periods[key]


def observe(book,context,before,after):
    year=context['date']//10000;years=book.setdefault('years',{});key=str(year)
    row=years.setdefault(key,dict(year=year,club=book['club'],start=context['date'],opening_budget=before,
        opening_date=context['date'],transfers=[],native_finance={}))
    row.update(last_date=context['date'],closing_budget=after,
        player_weekly=context.get('player_weekly'),wage_margin=context.get('wage_margin'),
        budget_initial=context.get('budget_initial'))
    # Unknown native totals must not erase a previously verified total.
    native=row.setdefault('native_finance',{})
    for k,v in context.get('native_finance',{}).items():
        if v is not None or k not in native:native[k]=deepcopy(v)
    transactions={tuple(t.get(k) for k in ('id','date','player','direction','fee','club','from','to')):t for t in row.get('transfers',[])}
    for t in context.get('transfers',[]):
        if t['date']//10000==year:
            transactions[tuple(t.get(k) for k in ('id','date','player','direction','fee','club','from','to'))]=deepcopy(t)
    row['transfers']=list(transactions.values())


def years(state):
    from club_finance import monthly
    book=state.get('finance',{});rows=monthly(state);stored=book.get('years',{})
    available={r['month']//100 for r in rows}|{int(y) for y in stored}
    out=[]
    for year in sorted(available,reverse=True):
        months=[deepcopy(r) for r in rows if r['month']//100==year]
        row=deepcopy(stored.get(str(year),dict(year=year,club=state['club'],opening_budget=None,closing_budget=None,last_date=None,transfers=[],native_finance={})))
        row.update(months=months,income=sum(r['income'] for r in months),
            expenses=sum(-r['coach']-r['staff']-r['facilities']-r['match_costs']-r['interest'] for r in months))
        row['result']=row['income']-row['expenses'];out.append(row)
    return out
