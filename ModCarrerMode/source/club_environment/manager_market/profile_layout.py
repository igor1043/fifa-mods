"""Reference-led native coach profile, with real metrics and reusable artwork."""
from layout import Scene
from profile_art import assets as profile_assets,pitch
INK='#102f46';MUTED='#718797';LIGHT='#eaf0f4';PAPER='#f3f7fa'
TAB_X=(490,824,1158,1492);TAB_W=318

def profile_scene(assets):
 assets.update(profile_assets());p=Scene('profile','Perfil do técnico')
 def text(name,x,y,w,h,value='',size=22,color=INK,section=None):
  p.text(x,y,w,h,value,size,color);p.nodes[-1]['name']=name
  if section is not None:p.nodes[-1]['section']=section
 def image(key,name,x,y,w,h,section=None):
  p.image(key,x,y,w,h);p.nodes[-1]['name']=name
  if section is not None:p.nodes[-1]['section']=section
 def button(x,y,w,h,code,asset='profile_clear'):
  p.action(x,y,w,h,'',str(code),LIGHT,INK,22);p.nodes[-1]['background_asset']=asset
 p.rect(60,90,1800,828,PAPER)
 text('name',96,106,1700,68,size=43)
 image('profile_identity','identityCard',96,190,366,719);image('profile_icon_coach','trainerIcon',118,207,24,24);text('identityHeading',152,207,288,27,'TREINADOR',19,MUTED)
 image('profile_photo','photoMatte',118,244,322,202)
 for n in range(11):image('stars_'+str(n),'rating'+str(n),176,457,204,38)
 # Portraits keep a square aspect ratio over a separate decorative backdrop.
 for key in list(assets):
  if key.startswith('head_'):image(key,'img_'+key,178,244,202,202)
  elif key.startswith('flag_'):image(key,'img_'+key,118,519,34,23)
  elif key.startswith('crest_'):image(key,'current_'+key,118,594,55,59)
 text('nationality',164,510,276,34,size=24);text('bio',118,550,320,28,size=20,color=MUTED)
 text('currentClub',188,594,252,36,size=23);text('clubStatus',188,631,252,25,size=17,color=MUTED)
 text('salaryLabel',118,670,320,23,'SALÁRIO MENSAL',17,MUTED);text('salary',118,698,320,38,size=30);text('salaryUnit',118,737,320,23,'/ mês',19,MUTED)
 text('style',118,776,320,29,size=23);text('formation',118,809,320,24,size=17,color=MUTED)
 text('trustLabel',118,844,248,26,'Confiança da diretoria',18);text('trust',369,842,71,28,size=23)
 image('profile_track','trustTrack',118,874,322,9);image('profile_gold_bar','trustFill',118,874,322,9);text('trustStatus',118,889,320,18,size=14,color=MUTED)
 # This label also serves as the native screen-ready sentinel.
 text('profileCaption',490,276,1320,27,size=19,color=MUTED)
 for tab,title in enumerate(('Visão geral','Passagem pelos clubes','Títulos','Estilo de jogo')):
  x=TAB_X[tab];button(x,190,TAB_W,52,80+tab,'profile_tab_off');image('profile_tab_on','profileMark'+str(tab),x,190,TAB_W,52)
  text('profileTabOff'+str(tab),x+8,203,TAB_W-16,30,title,21);p.nodes[-1]['align']=2
  text('profileTabOn'+str(tab),x+8,203,TAB_W-16,30,title,21,INK);p.nodes[-1]['align']=2
 # Keep the existing named scope for dynamic career coverage.
 text('scope',490,267,1320,30,size=20,color=MUTED)
 metrics=(('Jogos','pitch'),('Vitórias','trophy'),('Empates','handshake'),('Derrotas','cross'),('Gols pró','ball'),('Gols contra','shield'))
 for i,(label,icon) in enumerate(metrics):
  x=490+i*222;image('profile_metric','metricCard'+str(i),x,313,210,150,0);image('profile_icon_'+icon,'metricIcon'+str(i),x+19,354,49,49,0)
  text('metricLabel'+str(i),x+87,333,112,28,label,18,MUTED,0);text('metric'+str(i),x+87,368,112,49,size=38,section=0);text('metricNote'+str(i),x+87,422,112,24,size=17,color=MUTED,section=0)
 for i,label in enumerate(('Aproveitamento geral','Desempenho em casa','Desempenho fora de casa')):
  x=490+i*444;image('profile_venue','venueCard'+str(i),x,483,432,180,0);text('venueLabel'+str(i),x+22,500,388,29,label,21,INK,0);text('venuePercent'+str(i),x+22,542,388,47,size=39,section=0)
  image('profile_track','venueTrack'+str(i),x+22,602,388,12,0);image('profile_navy_bar' if i==1 else 'profile_gold_bar','venueFill'+str(i),x+22,602,388,12,0);text('venueDetail'+str(i),x+22,631,388,23,size=16,color=MUTED,section=0)
 image('profile_summary','summaryCard',490,683,1320,226,0);text('careerHeading',514,703,970,30,'TRAJETÓRIA NESTA CARREIRA',24,INK,0);text('careerCounts',514,741,1000,29,size=20,color=MUTED,section=0)
 button(1550,704,236,36,90,'profile_filter');text('filterName',1570,711,184,25,size=17,section=0);image('profile_icon_arrow','filterArrow',1757,714,18,18,0)
 image('track','timelineRail',515,784,2,112,0);image('profile_dot','timelinePoint',506,805,20,20,0)
 image('profile_timeline','latestCard',536,781,670,113,0)
 for key in list(assets):
  if key.startswith('crest_'):image(key,'latest_'+key,552,791,57,59)
 text('latestClub',625,791,360,31,size=23,section=0);text('latestSince',625,825,350,25,size=17,color=MUTED,section=0);image('profile_tag','latestTag',1098,794,90,30,0);text('latestStatus',1105,799,77,23,size=16,color='#76623d',section=0)
 for i,label in enumerate(('Jogos','Vitórias','Empates','Derrotas','Gols pró','Gols contra')):
  x=552+i*106;text('latestMetric'+str(i),x,853,98,25,size=22,section=0);text('latestLabel'+str(i),x,878,98,18,label,14,MUTED,0)
 text('recentHeading',1235,791,550,27,'Últimas partidas',19,INK,0);image('track','recentRail',1251,843,497,2,0)
 for i in range(10):
  x=1237+i*54
  for code in ('V','E','D'):image('profile_form_'+code,'recent'+str(i)+'_'+code,x,828,38,38)
  text('recentLetter'+str(i),x,834,38,24,size=17,color='#ffffff',section=0);p.nodes[-1]['align']=2
 text('coverage',1235,879,550,21,'Partidas e títulos confirmados na carreira.',14,MUTED,0)
 text('recentEmpty',1235,831,550,30,'Nenhuma partida registrada para este filtro.',17,MUTED)
 # History / titles retain independent pagination and competition artwork.
 for i in range(3):
  y=315+i*182;image('profile_entry','entryCard'+str(i),490,y,1320,166)
  for key in list(assets):
   if key.startswith('crest_'):image(key,'entry'+str(i)+'_'+key,510,y+18,74,74)
   elif key.startswith('competition_'):image(key,'trophy'+str(i)+'_'+key,510,y+18,86,90)
  text('entryName'+str(i),609,y+11,920,35,size=26);text('entryStatus'+str(i),1564,y+14,220,30,size=19,color=MUTED);text('entryDates'+str(i),609,y+51,1180,28,size=19,color=MUTED);text('entryTotal'+str(i),609,y+88,1180,28,size=21)
  text('entryHome'+str(i),609,y+122,556,24,size=16,color=MUTED);text('entryAway'+str(i),1220,y+122,556,24,size=16,color=MUTED)
  image('profile_track','entryHomeTrack'+str(i),609,y+151,556,6);image('profile_gold_bar','entryHomeFill'+str(i),609,y+151,556,6);image('profile_track','entryAwayTrack'+str(i),1220,y+151,556,6);image('profile_gold_bar','entryAwayFill'+str(i),1220,y+151,556,6)
 text('emptyProfile',510,482,1280,70,size=25,color=MUTED);button(490,879,65,29,70,'profile_filter');button(1745,879,65,29,71,'profile_filter');text('historyLeft',511,879,24,28,'‹',23);text('historyRight',1767,879,24,28,'›',23);text('historyPage',577,882,1140,27,size=18,color=MUTED)
 # The fourth tab shows catalogue preferences, never invented tactical ratings.
 for i in range(2):image('profile_style','styleCard'+str(i),490+i*670,315,650,171,3)
 image('profile_icon_tactics','styleIcon',514,342,58,58,3);text('stylePrimaryLabel',594,334,520,27,'IDENTIDADE DE JOGO',19,MUTED,3);text('stylePrimary',594,378,520,45,size=33,section=3);text('stylePrimaryNote',514,449,600,25,'Preferência do técnico registrada na carreira',17,MUTED,3)
 text('styleSecondaryLabel',1184,334,600,27,'PREFERÊNCIA COMPLEMENTAR',19,MUTED,3);text('styleSecondary',1184,378,600,45,size=27,section=3)
 image('profile_style','formationCard',490,506,650,389,3);text('formationHeading',514,522,600,29,'FORMAÇÃO PREFERIDA',21,INK,3);text('styleFormation',514,559,600,30,size=24,section=3)
 for key in list(assets):
  if key.startswith('profile_pitch_') and key!='profile_pitch_empty':image(key,'tactic_'+key,640,601,350,275)
 image('profile_pitch_empty','tacticPending',640,601,350,275)
 image('profile_style','styleContextCard',1160,506,650,389,3);text('styleClubLabel',1184,531,600,27,'VÍNCULO MAIS RECENTE',19,MUTED,3);text('styleClub',1184,573,600,39,size=30,section=3);text('styleTenure',1184,620,600,27,size=21,color=MUTED,section=3)
 text('styleNote',1184,704,600,30,'Uma identidade para cada treinador.',24,INK,3);text('styleNote2',1184,752,600,30,'As preferências acompanham os novos vínculos.',19,MUTED,3);text('styleNote3',1184,800,600,30,'A formação aparece quando houver cadastro.',19,MUTED,3)
 return p
