"""Hard career-market eligibility before nationality and weighted selection."""
from math import ceil


DEFAULTS = dict(max_coach_club_gap=1.5, max_coach_league_gap=3.0,
                elite_coach_threshold=8.0, elite_min_league_attraction=5.5,
                minimum_salary_retention_bps=8000, salary_capacity_bps=3000)


def league_attraction(club, clubs):
    peers=[float(c['reputation']) for c in clubs.values() if c['league_id']==club['league_id']]
    if not peers:
        return float(club['reputation'])
    peers.sort(reverse=True);top=peers[:max(1,ceil(len(peers)/4))]
    value=.65*sum(top)/len(top)+.35*sum(peers)/len(peers)
    return max(1,value-max(0,club.get('level',1)-1)*.75)


def offer(coach, club, clubs, proposed, policy, *, attraction=None):
    rep=float(coach['reputation']);attraction=league_attraction(club,clubs) if attraction is None else attraction
    if rep>club['reputation']+policy['max_coach_club_gap']:
        return None
    if rep>attraction+policy['max_coach_league_gap']:
        return None
    if rep>=policy['elite_coach_threshold'] and attraction<policy['elite_min_league_attraction']:
        return None
    salary=max(proposed,round(max(0,coach.get('salary') or 0)*policy['minimum_salary_retention_bps']/10000))
    capacity=max(120000,max(0,club['budget'])*policy['salary_capacity_bps']/10000+300000)
    return salary if salary*12<=capacity else None
