"""A separate gallery ledger carried by the existing exact-save checkpoints."""
from datetime import date

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
    for t in context.get('titles',[]):
        if t.get('origin')=='preview':continue
        won=int(t['date']);club=int(t['club']);asset=int(t['asset']);root=int(t['root']);season=int(t['season'])
        date(won//10000,won//100%100,won%100)
        if won>today or club<=0 or asset<=0 or root<0 or not str(t['name']).strip():continue
        evidence=market.db.execute('''SELECT home,home_coach,away_coach FROM results
            WHERE branch=? AND root=? AND competition_id=? AND game_date<=? AND (home=? OR away=?)
            ORDER BY game_date DESC LIMIT 1''',(market.branch,root,asset,won,club,club)).fetchone()
        coach=(evidence['home_coach'] if evidence['home']==club else evidence['away_coach']) if evidence else None
        national=club in set(context.get('national_teams',[]))
        if national:
            tenure=market.db.execute('''SELECT coach_id FROM trophy_national_tenures WHERE branch=? AND team_id=?
                AND start_date<=? AND (end_date IS NULL OR end_date>?) ORDER BY start_date DESC LIMIT 1''',(market.branch,club,won,won)).fetchone()
            coach=tenure['coach_id'] if tenure else None
        elif not coach:
            appointments=market.db.execute('''SELECT coach_id FROM appointments WHERE branch=? AND club_id=?
                AND start_date<=? AND (end_date IS NULL OR end_date>?)''',(market.branch,club,won,won)).fetchall()
            users=[r['coach_id'] for r in appointments if r['coach_id'].startswith('USER-')]
            # Initial catalogue appointments can overlap a backdated native
            # user tenure. The human's verified interval owns those trophies.
            if len(users)==1:coach=users[0]
            elif len(appointments)==1:coach=appointments[0]['coach_id']
        market.db.execute('''INSERT INTO trophy_history
            (branch,coach_id,club_id,season,competition_id,root,game_date,name,source,team_kind)
            VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(branch,season,root,competition_id,club_id)
            DO UPDATE SET coach_id=COALESCE(trophy_history.coach_id,excluded.coach_id),name=excluded.name,team_kind=excluded.team_kind
            WHERE (trophy_history.coach_id IS NULL AND excluded.coach_id IS NOT NULL)
               OR trophy_history.name<>excluded.name OR trophy_history.team_kind<>excluded.team_kind''',
            (market.branch,coach,club,season,asset,root,won,t['name'],t.get('evidence_source','confirmed_calendar'),'national' if national else 'club'))
