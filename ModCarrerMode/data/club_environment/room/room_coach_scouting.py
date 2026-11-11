"""Bounded, read-only views of FIFA 16's GTN save serializers and youth missions.

GTN scouts are not career_scouts (the youth academy), and career_transferlist
is a global selling list, not the user's watched players. Never conflate them.
Unsupported serializers leave just these optional panels unavailable.
"""
from datetime import datetime
import struct


def date_ok(value):
    try:return 20000101<=value<=20991231 and bool(datetime.strptime(str(value),'%Y%m%d'))
    except ValueError:return False


def unavailable():return dict(recognized=False,scouts=[],reports=[],source='unavailable')


def read_network(data,player_ids=()):
    if not isinstance(data,(bytes,bytearray)):return unavailable()
    def marker(token):
        start=data.find(token)
        if start<160 or data.find(token,start+len(token))!=-1:raise ValueError('Missing or ambiguous GTN marker')
        return start+len(token)
    try:
        scout_start=marker(b'gtn02\0');report_start=marker(b'gtn05\0')
        if not scout_start<report_start:raise ValueError('GTN section order')
        # Record: id:i32, UTF8 given/family names:45+45, nine i32 fields.
        pos=scout_start+4;hired=[]
        for group in range(2):
            count=struct.unpack_from('<i',data,pos)[0];pos+=4
            if not 0<=count<=32 or pos+count*130>report_start-6:raise ValueError('Scout vector bounds')
            used=set()
            for i in range(count):
                ident=struct.unpack_from('<i',data,pos)[0]
                def name(offset):
                    raw=data[offset:offset+45].split(b'\0',1)[0]
                    try:label=raw.decode('utf8')
                    except UnicodeDecodeError:label=raw.decode('cp1252')
                    if not label or any(ord(c)<32 for c in label):raise ValueError('Scout name')
                    return label.strip()
                given,family=name(pos+4),name(pos+49)
                country,nationality,*other=struct.unpack_from('<9i',data,pos+94)
                if not 0<=ident<64 or ident in used or not 0<=country<=1000 or not 0<nationality<=1000:
                    raise ValueError('Scout identity')
                used.add(ident)
                if group==0:hired.append(dict(id=ident,name=(given+' '+family).strip(),country=country,nationality=nationality))
                pos+=130
        # gtn05: two seed words, last-processing day/month/year, report vector.
        count=struct.unpack_from('<i',data,report_start+20)[0];pos=report_start+24
        if not 0<=count<=4096 or pos+count*20>len(data):raise ValueError('Report vector bounds')
        day,month,year=struct.unpack_from('<3i',data,report_start+8)
        if not date_ok(year*10000+month*100+day) and not (count==0 and day==month==year==0):
            raise ValueError('GTN processing date')
        reports=[];used=set();known=set(player_ids)
        for i in range(count):
            player,flags,_,date,_=struct.unpack_from('<5i',data,pos+i*20)
            if not 0<player<2_000_000 or player in used or flags<0 or (date and not date_ok(date)):
                raise ValueError('GTN report record')
            used.add(player)
            # Deleted/expired players cannot become a different player's report.
            if known and player not in known:continue
            reports.append(dict(id=player,date=date))
        return dict(recognized=True,scouts=hired,reports=reports,source='save_gtn02_gtn05')
    except (ValueError,struct.error,UnicodeError):return unavailable()


def from_tables(rows,saved_tables,player_ids=()):
    calendar=rows('career_calendar') if 'career_calendar' in saved_tables else []
    if len(calendar)!=1:return unavailable()
    return read_network(getattr(calendar[0],'data',None),player_ids)


def enrich(context,rows,saved_tables,network,names):
    from room_dynamic_context_20261022 import clean
    from manager_market.catalog_meta import TRANSLATIONS
    nations={r.value('nationid'):r for r in rows('nations')}
    def country(ident):
        r=nations.get(ident)
        if not r:return dict(id=ident,name='Não informado',iso='')
        name=clean(r.value('nationname'))
        return dict(id=ident,name=TRANSLATIONS.get(name,name),iso=r.value('isocountrycode') if 'isocountrycode' in r.fields else '')
    scouts=[dict(s,country=country(s['country']),nationality=country(s['nationality'])) for s in network['scouts']]
    players={r.value('playerid'):r for r in rows('players')}
    teams={r.value('teamid'):clean(r.value('teamname')) for r in rows('teams')}
    national_teams={r.value('teamid') for table in ('teamnationlinks','rowteamnationlinks') for r in rows(table) if 'teamid' in r.fields}
    wanted={r['id'] for r in network['reports']};clubs={}
    for r in rows('teamplayerlinks'):
        pid,team=r.value('playerid'),r.value('teamid')
        if pid in wanted and team not in national_teams:clubs.setdefault(pid,set()).add(team)
    edits={r.value('playerid'):r for r in rows('editedplayernames') if r.value('playerid') in wanted}
    reports=[]
    for raw in network['reports']:
        pid=raw['id'];p=players.get(pid)
        if not p:continue
        def value(key,default=0):return p.value(key) if key in p.fields else default
        label=next((names.get(value(k)) for k in ('playerjerseynameid','commonnameid') if names.get(value(k))),'')
        if not label:label=' '.join(names.get(value(k),'') for k in ('firstnameid','lastnameid')).strip()
        if pid in edits:
            e=edits[pid];label=next((e.value(k) for k in ('playerjerseyname','commonname','surname') if k in e.fields and e.value(k)),label)
        club_ids=clubs.get(pid,set());team=next(iter(club_ids)) if len(club_ids)==1 else 0
        reports.append(dict(raw,name=clean(label) or f'Jogador {pid}',club=team,club_name=teams.get(team,'Clube não identificado'),
                            position=value('preferredposition1'),nationality=country(value('nationality'))))
    reports.sort(key=lambda p:(-p['date'],p['name'],p['id']))
    youth=[]
    # These tables are career-local. Never fall back to a base/default mission.
    if {'career_scouts','career_scoutmission'}<=saved_tables:
        hired={r.value('scoutid'):r for r in rows('career_scouts')}
        for r in rows('career_scoutmission'):
            s=hired.get(r.value('scoutid'))
            if not s:continue
            youth.append(dict(id=r.value('scoutid'),country=country(r.value('nationality')),return_date=r.value('returningdate')))
    return dict(recognized=network['recognized'],scouts=scouts,reports=reports,youth=youth,source=network['source'])
