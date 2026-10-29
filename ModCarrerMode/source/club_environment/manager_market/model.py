"""Compact display model; all amounts are simulated career currency units."""
from datetime import date
from engine import day,elapsed,score
from catalog_meta import Labels
from career_profile import build as career_profile

MONTHS=('Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro')

def money(n):return f'{int(n or 0):,}'.replace(',','.')
def stamp(n):return f'{n%100:02d}/{n//100%100:02d}/{n//10000}' if n else 'Atual'
def years(birth,today):
 try:
  b=date.fromisoformat(birth);d=day(today);return d.year-b.year-((d.month,d.day)<(b.month,b.day))
 except (ValueError,TypeError):return -1
def summary(s):return f"{s['games']} J · {s['wins']} V · {s['draws']} E · {s['losses']} D · {s['percentage']}% · GP {s['gf']} / GC {s['ga']}"
def brief(s):return f"{s['games']} J · {s['wins']} V · {s['draws']} E · {s['losses']} D · GP {s['gf']} / GC {s['ga']}"
def decimal(value):return f'{value:.1f}'.replace('.',',')
def venue_detail(s):return f"{s['games']} partidas · {s['wins']} V · {s['draws']} E · {s['losses']} D"
def visual_data(profile):
 from profile_art import formation
 rich=profile['career'];s=rich['total'];last=rich['spells'][0] if rich['spells'] else None
 notes=['']+[decimal(s[k]*100/s['games'])+'%' if s['games'] else '—' for k in ('wins','draws','losses')]+[decimal(s[k]/s['games'])+' por jogo' if s['games'] else '—' for k in ('gf','ga')]
 return notes+[venue_detail(rich[k]) for k in ('total','home','away')]+[rich['recent'][k] for k in ('all','home','away')]+[last['club'] if last else 'Nenhuma passagem registrada',last['crest'] if last else '',('Desde ' if last and last['current'] else 'Início: ')+last['since'] if last else '',('Atual' if last['current'] else 'Encerrada') if last else '']+[str(last['total'][k]) if last else '—' for k in ('games','wins','draws','losses','gf','ga')]+[profile['style'],profile['secondaryStyle'] or 'Preferência complementar não cadastrada',profile['formation'],last['duration'] if last else 'Aguardando primeiro vínculo','profile_pitch_'+profile['formation'].replace('-','_').replace('–','_') if formation(profile['formation']) else 'profile_pitch_empty']

def project(market,user_confidence=None):
 labels=Labels(market.catalog)
 info=market.info();today=info['game_date'];people=market.rows('coaches');clubs={r['club_id']:r for r in market.rows('clubs')};appointments=market.rows('appointments');active={r['club_id']:r for r in appointments if r['end_date'] is None};occupied={a['coach_id'] for a in active.values()}
 history={};games={};home={};away={};clubgames={};passages={}
 for a in appointments:history.setdefault(a['coach_id'],[]).append(a)
 results=market.rows('results')
 for r in results:
  for ident,club,gf,ga,is_home in ((r['home_coach'],r['home'],r['hg'],r['ag'],True),(r['away_coach'],r['away'],r['ag'],r['hg'],False)):
   if not ident:continue
   games.setdefault(ident,[]).append((gf,ga));(home if is_home else away).setdefault(ident,[]).append((gf,ga));clubgames.setdefault((ident,club),[]).append((gf,ga))
   appointment=r.get('home_appointment' if is_home else 'away_appointment')
   if appointment:passages.setdefault(appointment,[]).append((gf,ga))
 honours={}
 all_honours=market.rows('honours')
 for h in all_honours:honours.setdefault(h['coach_id'],[]).append(h)
 renewals={r['id'] for r in market.rows('movements',"kind='renewal'")}
 for a in appointments:a['renewal']=a['id'] in renewals
 reviews={}
 for row in market.rows('reviews'):reviews.setdefault(row['club_id'],[]).append(row)
 people.sort(key=lambda p:p['coach_id']);indices={p['coach_id']:i for i,p in enumerate(people)};profiles=[]
 for p in people:
  ident=p['coach_id'];age=years(p['birth_date'],today);visits=sorted(history.get(ident,[]),key=lambda a:a['start_date'],reverse=True);current=next((a for a in visits if a['end_date'] is None),None);club=clubs.get(current['club_id'],{}) if current else {}
  title=sorted(honours.get(ident,[]),key=lambda h:h['game_date'],reverse=True)
  lines=[]
  for a in visits:
   cs=score(passages.get(a['id'],[]));lines.append(clubs.get(a['club_id'],{}).get('name','Clube')+' · '+stamp(a['start_date'])+' a '+stamp(a['end_date'])+' · '+summary(cs))
  nationality,flag=labels.nationality(p['nationality']);preferences=labels.preferences.get(ident,{})
  free_since=max((a['end_date'] for a in visits if a['end_date']),default=info['start_date'])
  profiles.append(dict(id=ident,name=p['name'],nationality=nationality,flag=flag,style=p['style'],formation=preferences.get('formation') or 'Não informada',secondaryStyle=preferences.get('secondary_style') or '',freeDays=str(max(0,elapsed(free_since,today)))+' dias no mercado',age=age,reputation=max(0,min(10,round(p['reputation']))),head='head_'+p['image'].split('/')[-1].split('.')[0],image=p['image'],salary=current['monthly_wage'] if current else p['salary'],eligible=p['eligible'],club=club.get('name','Livre no mercado'),league=club.get('league_id',0),details=[nationality+' · '+(str(age)+' anos' if age>=0 else 'Idade pendente')+' · '+p['style'],club.get('name','Livre no mercado')+' · '+money(current['monthly_wage'] if current else p['salary'])+' / mês',summary(score(games.get(ident,[]))),'Em casa: '+summary(score(home.get(ident,[]))),'Fora: '+summary(score(away.get(ident,[]))),('Nome fictício · ' if p['fictional'] else '')+('Estatísticas registradas desde '+stamp(info['start_date']))],history=lines or ['Sem passagem registrada desde a ativação do mercado.'],titles=[h['name']+' · '+str(h['season']//10000)+' · ID '+str(h['competition_id'])+' · '+clubs.get(h['club_id'],{}).get('name','Clube') for h in title] or ['Nenhum título confirmado pelo calendário até esta data.']))
  rich=career_profile(p,appointments,results,all_honours,reviews,clubs,today,stamp);s=rich['total'];hs=rich['home'];aws=rich['away'];current_spell=next((v for v in rich['spells'] if v['current']),None);confidence=current_spell['confidence'] if current_spell else dict(value=-1,label='Sem vínculo atual')
  if ident.startswith('USER-') and type(user_confidence)==int and 0<=user_confidence<=100:confidence=dict(value=user_confidence,label='Avaliação da diretoria no FIFA')
  profiles[-1].update(career=rich,confidence=confidence,overview=[s[k] for k in ('games','wins','draws','losses','gf','ga')]+[s['percentage'],hs['percentage'],aws['percentage'],brief(hs),brief(aws),rich['clubs'],len(rich['spells']),len(rich['titles']),'Registros da carreira desde '+stamp(info['start_date']),club.get('name','Livre no mercado'),'crest_'+str(club['club_id']) if club else '',confidence['value'],confidence['label'],stamp(current['start_date']) if current else 'Sem contrato'],spellCards=[[v['club'],v['crest'],v['dates'],v['duration'],'Atual' if v['current'] else 'Encerrada',summary(v['total']),v['total']['percentage'],summary(v['home']),v['home']['percentage'],summary(v['away']),v['away']['percentage'],str(v['titles'])+' títulos confirmados'] for v in rich['spells']],titleCards=[[v['name'],v['competitionArt'],v['club'],v['crest'],v['year'],v['date']] for v in rich['titles']])
  for card in profiles[-1]['spellCards']:card[11]=card[11].replace(' títulos confirmados',' títulos')
  profiles[-1]['overview'] += [f"{v['percentage']:.1f}".replace('.',',')+'%' for v in (s,hs,aws)]
  profiles[-1]['overview'].append(f"{rich['clubs']} "+('clube' if rich['clubs']==1 else 'clubes')+f" · {len(rich['spells'])} "+('passagem' if len(rich['spells'])==1 else 'passagens')+f" · {len(rich['titles'])} "+('título confirmado' if len(rich['titles'])==1 else 'títulos confirmados'))
  profiles[-1]['visualData']=visual_data(profiles[-1])
 def row_for(club,a):
  i=indices[a['coach_id']];p=profiles[i];tenure=str(max(0,elapsed(a['start_date'],today)))+' dias · desde '+stamp(a['start_date'])
  return [club['name'],p['name'],tenure,money(a['monthly_wage'])+' / mês','crest_'+str(club['club_id']),p['head'],p['reputation'],i,club['league_id']]
 clubrows=[row_for(c,active[c['club_id']]) for c in sorted(clubs.values(),key=lambda c:c['name']) if c['club_id'] in active]
 free=[]
 for i,p in sorted(enumerate(profiles),key=lambda x:(-x[1]['reputation'],x[1]['name'])):
  if p['id'] in occupied:continue
  visits=sorted(history.get(p['id'],[]),key=lambda x:x['start_date'],reverse=True);last=clubs.get(visits[0]['club_id'],{}).get('name','Sem clube registrado') if visits else 'Primeiro projeto no mercado'
  free.append([p['name'],p['nationality']+' · '+(str(p['age'])+' anos' if p['age']>=0 else 'Idade pendente'),last,money(p['salary'])+' / mês','',p['head'],p['reputation'],i,0,p['age'],p['nationality'],p['eligible']])
 moves=[]
 for e in sorted(market.rows('movements','kind=\'dismissal\''),key=lambda e:(e['game_date'],e['club_id'],e['coach_id']),reverse=True):
  if e['coach_id'] not in indices:continue
  i=indices[e['coach_id']];p=profiles[i];c=clubs.get(e['club_id'],{});moves.append([c.get('name','Clube'),p['name'],stamp(e['game_date'])+' · '+e['reason'],'Demissão','crest_'+str(e['club_id']),p['head'],p['reputation'],i,0,e['game_date'],stamp(e['game_date'])])
 hires=[]
 poached={(e['coach_id'],e['to_club'],e['game_date']):e['from_club'] for e in market.rows('movements',"kind='poached'")}
 for e in sorted(market.rows('movements',"kind IN ('hired','interim_appointed')"),key=lambda e:(e['game_date'],e['club_id'],e['coach_id']),reverse=True):
  if e['coach_id'] not in indices:continue
  i=indices[e['coach_id']];p=profiles[i];c=clubs.get(e['club_id'],{});origin=poached.get((e['coach_id'],e['club_id'],e['game_date']))
  source='Comissão técnica' if e['kind']=='interim_appointed' else clubs.get(origin,{}).get('name','Livre no mercado')
  hires.append([c.get('name','Clube'),p['name'],stamp(e['game_date'])+' · Origem: '+source,money(e['new_salary'])+' / mês','crest_'+str(e['club_id']),p['head'],p['reputation'],i,0,e['game_date'],stamp(e['game_date'])])
 leagues={}
 for c in clubs.values():
  if c['club_id'] not in active:continue
  lid=c['league_id'];meta=labels.leagues.get(lid,{});country=labels.countries.get(meta.get('country_id'),{})
  name,nid=(country['name'],country['nation_id']) if country else labels.country(c['country'])
  leagues[lid]=dict(id=lid,name=meta.get('name',c['league_name']),country=name,countryId=nid,level=meta.get('level',c['level']),image='league_'+str(lid))
 leagues=sorted(leagues.values(),key=lambda l:(l['country'],l['level'],l['name']));countries=sorted({(l['country'],l['countryId']) for l in leagues})
 countries=[dict(name=name,id=nid,flag='flag_'+str(nid)) for name,nid in countries];mine=clubs.get(info['user_club'],{});mine_l=mine.get('league_id',0);mine_country=leagues[next((i for i,l in enumerate(leagues) if l['id']==mine_l),0)]['country'] if leagues else ''
 initial_country=next((i for i,c in enumerate(countries) if c['name']==mine_country),0)
 start=min([info['start_date'],today]+[a['start_date'] for a in appointments]);first=(start//10000)*12+(start//100%100)-1;last=(today//10000)*12+(today//100%100)-1
 months=[[y*100+m+1,MONTHS[m]+' '+str(y)] for n in range(first,last+1) for y,m in [divmod(n,12)]]
 return dict(date=today,start=start,ready=True,club=info['user_club'],clubName=mine.get('name','Carreira'),people=profiles,clubRows=clubrows,freeRows=free,moveRows=moves,hireRows=hires,leagues=leagues,countries=countries,months=months,nationalities=['Todas']+sorted({p['nationality'] for p in profiles if p['nationality']!='Não informada'}),initialLeague=mine_l,initialCountry=initial_country,initialMonth=len(months)-1)
