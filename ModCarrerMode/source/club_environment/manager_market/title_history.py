"""A separate gallery ledger carried by the existing exact-save checkpoints."""
from datetime import date

def owner(market,context,title):
    """Use the actual tenure, never today's replacement for an old trophy."""
    won=int(title['date']);club=int(title['club'])
    lower=max(int(title.get('ownership_start',won)),int(context.get('title_start',context.get('career_start_date',0))))
    rows=market.db.execute('''SELECT * FROM appointments WHERE branch=? AND club_id=?
        AND start_date<=? AND (end_date IS NULL OR end_date>?) ORDER BY start_date''',
        (market.branch,club,won,lower)).fetchall()
    covered={}
    for row in rows:
        coach=row['coach_id'];start=row['start_date'];end=row['end_date'] or won+1
        if (str(title.get('evidence_source','')).endswith(':season') and start//100==lower//100
                and row['origin']=='Vínculo inicial desde o início da carreira'):
            # The native creation date can be Jan 9 while the season key is
            # Jan 1. This is the initial tenure, not a later appointment.
            start=lower
        if start<=lower or start<=covered.get(coach,0):covered[coach]=max(end,covered.get(coach,0))
    coaches=[coach for coach,end in covered.items() if end>won]
    users=[coach for coach in coaches if coach.startswith('USER-')]
    return users[0] if len(users)==1 else coaches[0] if len(coaches)==1 else None

def national_tenures(market,context):
    coach='USER-'+str(context.get('userid',0));teams=set(context.get('national_teams',[]))
    for job in sorted(context.get('national_jobs',[]),key=lambda r:r['date']):
        at=int(job['date']);team=int(job['team'])
        if at>context['date'] or team and team not in teams:continue
        date(at//10000,at//100%100,at%100)
        # Repeated saved metadata must not reopen an ended job, nor overwrite
        # the dated live observation that already exists later in the journal.
        latest=market.db.execute('''SELECT * FROM trophy_national_tenures WHERE branch=? AND coach_id=?
            ORDER BY start_date DESC,rowid DESC LIMIT 1''',(market.branch,coach)).fetchone()
        if latest and (at<latest['start_date'] or at==latest['start_date'] and job['source']!='live_context' or latest['team_id']==team):continue
        if latest:market.db.execute('UPDATE trophy_national_tenures SET end_date=? WHERE branch=? AND coach_id=? AND end_date IS NULL',(at,market.branch,coach))
        market.db.execute('INSERT OR IGNORE INTO trophy_national_tenures VALUES(?,?,?,?,?,?)',(market.branch,coach,team,at,None,job['source']))

def record(market,context):
    today=int(context['date'])
    national_tenures(market,context)
    # Old versions already recorded some verified honours. Import facts only;
    # this does not award reputation, money or simulate old appointments.
    market.db.execute('''INSERT OR IGNORE INTO trophy_history
        (branch,coach_id,club_id,season,competition_id,root,game_date,name,source)
        SELECT branch,coach_id,club_id,
        (CAST(game_date/10000 AS INT)-CASE WHEN CAST(game_date/100 AS INT)%100<CAST(season/100 AS INT)%100 THEN 1 ELSE 0 END)*10000+(CAST(season/100 AS INT)%100)*100+1,
        competition_id,root,game_date,name,'coach_journal'
        FROM honours WHERE branch=? AND game_date<=?''',(market.branch,today))
    from league_title_receipts import receipts
    from cup_title_receipts import receipts as cup_receipts
    for t in [*context.get('titles',[]),*cup_receipts(market,context),*receipts(market,context)]:
        if t.get('origin')=='preview':continue
        won=int(t['date']);club=int(t['club']);asset=int(t['asset']);root=int(t['root']);season=int(t['season'])
        date(won//10000,won//100%100,won%100)
        if won>today or club<=0 or asset<=0 or root<0 or not str(t['name']).strip():continue
        source=str(t.get('evidence_source',''));native=source.startswith('completed_native_table:');approximate=source.endswith(':season')
        if native or approximate:
            # A dated final / previously verified winner is stronger than a
            # table observation. Preserve it, including its exact award day.
            known=market.db.execute('''SELECT 1 FROM trophy_history WHERE branch=? AND root=? AND competition_id=?
                AND CAST(season/100 AS INT)=? AND source NOT LIKE 'completed_native_table:%'
                AND source NOT LIKE '%:season' LIMIT 1''',
                (market.branch,root,asset,season//100)).fetchone()
            if known:continue
        evidence=None if native or approximate else market.db.execute('''SELECT home,home_coach,away_coach FROM results
            WHERE branch=? AND root=? AND competition_id=? AND game_date<=? AND (home=? OR away=?)
            ORDER BY game_date DESC LIMIT 1''',(market.branch,root,asset,won,club,club)).fetchone()
        coach=(evidence['home_coach'] if evidence['home']==club else evidence['away_coach']) if evidence else None
        national=club in set(context.get('national_teams',[]))
        if national:
            tenure=market.db.execute('''SELECT coach_id FROM trophy_national_tenures WHERE branch=? AND team_id=?
                AND start_date<=? AND (end_date IS NULL OR end_date>?) ORDER BY start_date DESC LIMIT 1''',(market.branch,club,won,won)).fetchone()
            coach=tenure['coach_id'] if tenure else None
        elif not coach:coach=owner(market,context,t)
        market.db.execute('''INSERT INTO trophy_history
            (branch,coach_id,club_id,season,competition_id,root,game_date,name,source,team_kind)
            VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(branch,season,root,competition_id,club_id)
            DO UPDATE SET coach_id=COALESCE(excluded.coach_id,trophy_history.coach_id),name=excluded.name,team_kind=excluded.team_kind,
                game_date=excluded.game_date,source=excluded.source
            WHERE (trophy_history.coach_id IS NULL AND excluded.coach_id IS NOT NULL)
               OR trophy_history.name<>excluded.name OR trophy_history.team_kind<>excluded.team_kind
               OR ((trophy_history.source LIKE 'completed_native_table:%' OR trophy_history.source LIKE '%:season')
                   AND excluded.source NOT LIKE 'completed_native_table:%' AND excluded.source NOT LIKE '%:season')''',
            (market.branch,coach,club,season,asset,root,won,t['name'],t.get('evidence_source','confirmed_calendar'),'national' if national else 'club'))
