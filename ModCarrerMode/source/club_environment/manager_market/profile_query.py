"""Read one coach's CV without projecting all clubs, coaches and movements."""
from collections import defaultdict
from model import enrich_profile
from evidence_ownership import complete_campaigns,without_complete


def build(market,base_person,user_confidence=None):
    coach=base_person['id'];person=market.one('coaches','coach_id',coach)
    if not person:raise ValueError('Técnico fora desta carreira')
    visits=market.rows('appointments','coach_id=?',(coach,))
    ids=tuple(a['id'] for a in visits)
    from coach_titles import read as read_titles
    honours=read_titles(market,coach)
    clubs={a['club_id'] for a in visits}|{h['club_id'] for h in honours}
    club_rows={r['club_id']:r for r in market.rows('clubs','club_id IN ('+','.join('?' for _ in clubs)+')',tuple(clubs))} if clubs else {}
    results=market.rows('results','(home_coach=? OR away_coach=?)',(coach,coach))
    moves=market.rows('movements','coach_id=?',(coach,))
    renewals={m['id'] for m in moves if m['kind']=='renewal'}
    for a in visits:a['renewal']=a['id'] in renewals
    def counters(table):
        return market.rows(table,'appointment IN ('+','.join('?' for _ in ids)+')',ids) if ids else []
    campaigns=counters('appointment_campaigns');annual=counters('annual_campaigns')
    complete=complete_campaigns(visits,results,campaigns)
    campaigns=without_complete(visits,campaigns,complete);annual=without_complete(visits,annual,complete)
    reviews=defaultdict(list)
    if clubs:
        for row in market.rows('reviews','club_id IN ('+','.join('?' for _ in clubs)+')',tuple(clubs)):reviews[row['club_id']].append(row)
    from competition_labels import resolve
    game=market.catalog.parents[3]
    honours=[dict(h,name=resolve(game,h['competition_id'],h['name'])) for h in honours]
    return enrich_profile(dict(base_person,profilePending=False),person,visits,results,honours,reviews,club_rows,market.info()['game_date'],campaigns,moves,annual,user_confidence)
