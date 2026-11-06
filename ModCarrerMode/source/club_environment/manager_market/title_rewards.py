"""Prestige-weighted valuation; signed appointment salaries stay immutable."""
def reward(prestige):
    prestige=max(1,min(10,float(prestige or 5)))
    return round(.08+.055*prestige,3), .01+.0075*prestige

def prestige(market,asset):
    row=market.one('competition_policies','competition_id',asset)
    return row['prestige'] if row else 5

def renewal_bonus(market,appointment,today):
    titles=market.rows('honours','coach_id=? AND club_id=? AND game_date>=? AND game_date<=?',(appointment['coach_id'],appointment['club_id'],appointment['start_date'],today))
    return min(.20,sum(reward(prestige(market,t['competition_id']))[1] for t in titles))
