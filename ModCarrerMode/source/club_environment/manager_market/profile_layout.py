"""Reference-led native coach profile, with real metrics and reusable artwork."""
from layout import Scene
from profile_art import assets as profile_assets,pitch
INK='#102f46';MUTED='#718797';LIGHT='#eaf0f4';PAPER='#f3f7fa'
TAB_X=(490,757,1024,1291,1558);TAB_W=251

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
 image('profile_identity','identityCard',96,190,366,719)
 # The team-coloured portrait is the only photograph background.
 for n in range(11):image('stars_'+str(n),'rating'+str(n),278,374,162,31)
 # Portraits keep a square aspect ratio over a separate decorative backdrop.
 for key in list(assets):
  if key.startswith('head_'):image(key,'img_'+key,112,235,146,146)
  elif key.startswith('flag_'):image(key,'img_'+key,278,216,28,19)
  elif key.startswith('crest_'):image(key,'current_'+key,278,289,38,42)
 text('nationality',315,211,132,29,size=20);text('bio',278,247,160,25,size=17,color=MUTED)
 text('currentClub',323,289,124,45,size=19);text('clubStatus',278,341,167,24,size=15,color=MUTED)
 for i in range(3):image('profile_metric','identityTile'+str(i),108+i*116,436,110,148)
 text('salaryLabel',118,450,94,32,'SALÁRIO MENSAL',12,MUTED);text('salary',118,493,94,35,size=23);text('salaryUnit',118,544,94,23,'/ mês',16,MUTED)
 text('styleLabel',234,450,92,25,'SITUAÇÃO',12,MUTED);text('style',234,487,92,47,size=17);text('formation',234,544,92,30,size=13,color=MUTED)
 text('contractLabel',350,450,94,25,'VÍNCULO',12,MUTED);text('contractUntil',350,486,94,46,size=17);text('contractRemaining',350,540,94,35,size=13,color=MUTED)
 text('trustLabel',118,612,248,26,'Confiança da diretoria',18);text('trust',369,610,71,28,size=23)
 image('profile_track','trustTrack',118,653,322,10);image('profile_gold_bar','trustFill',118,653,322,10);text('trustStatus',118,675,320,24,size=15,color=MUTED)
 text('contractInfoHeading',118,733,320,28,'CONTRATO COM O CLUBE',17,MUTED)
 text('contractSince',118,776,320,28,size=18);text('contractState',118,821,320,55,size=17,color=MUTED)
 # This label also serves as the native screen-ready sentinel.
 text('profileCaption',490,276,1320,27,size=19,color=MUTED)
 for tab,title in enumerate(('Visão geral','Passagens','Títulos','Estilo de jogo','Histórico anual')):
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
 image('profile_summary','summaryCard',490,683,1320,226,0);text('careerHeading',514,703,970,30,'ÚLTIMAS PARTIDAS',24,INK,0)
 button(1550,704,236,36,90,'profile_filter');text('filterName',1570,711,184,25,size=17,section=0);image('profile_icon_arrow','filterArrow',1757,714,18,18,0)
 image('track','recentRail',550,802,1170,2,0)
 for i in range(10):
  x=550+i*117
  for code in ('V','E','D'):image('profile_form_'+code,'recent'+str(i)+'_'+code,x,779,46,46)
  text('recentLetter'+str(i),x,788,46,26,size=19,color='#ffffff',section=0);p.nodes[-1]['align']=2
 text('coverage',514,863,1250,24,'Placares individuais confirmados. A campanha total inclui os contadores da competição.',16,MUTED,0)
 text('recentEmpty',550,781,1170,36,'Nenhum placar individual disponível para este filtro.',21,MUTED)
 # History / titles retain independent pagination and competition artwork.
 for i in range(3):
  y=315+i*182;image('profile_entry','entryCard'+str(i),490,y,1320,166)
  for key in list(assets):
   if key.startswith('crest_'):image(key,'entry'+str(i)+'_'+key,510,y+18,74,74)
   elif key.startswith('competition_'):image(key,'trophy'+str(i)+'_'+key,510,y+18,86,90)
  text('entryName'+str(i),609,y+11,920,35,size=26);text('entryStatus'+str(i),1564,y+14,220,30,size=19,color=MUTED);text('entryDates'+str(i),609,y+51,1180,28,size=19,color=MUTED);text('entryTotal'+str(i),609,y+88,1180,28,size=21)
  for j,label in enumerate(('JOGOS','VITÓRIAS','EMPATES','DERROTAS','GOLS PRÓ','GOLS CONTRA')):
   x=609+j*195;text('entryValue'+str(i)+'_'+str(j),x,y+83,180,29,size=24);text('entryLabel'+str(i)+'_'+str(j),x,y+113,180,19,label,12,MUTED)
  text('entryHome'+str(i),510,y+113,86,23,size=17,color=INK);text('entryAway'+str(i),1220,y+122,556,24,size=16,color=MUTED)
  image('profile_track','entryHomeTrack'+str(i),609,y+151,1167,6);image('profile_gold_bar','entryHomeFill'+str(i),609,y+151,556,6);image('profile_track','entryAwayTrack'+str(i),1220,y+151,556,6);image('profile_gold_bar','entryAwayFill'+str(i),1220,y+151,556,6)
 text('emptyProfile',510,482,1280,70,size=25,color=MUTED);button(490,879,65,29,70,'profile_filter');button(1745,879,65,29,71,'profile_filter');text('historyLeft',511,879,24,28,'‹',23);text('historyRight',1767,879,24,28,'›',23);text('historyPage',577,882,1140,27,size=18,color=MUTED)
 image('profile_track','historyScrollTrack',1824,315,6,530);image('profile_gold_bar','historyScrollThumb',1824,315,6,530)
 # The fourth tab shows catalogue preferences, never invented tactical ratings.
 for i in range(2):image('profile_style','styleCard'+str(i),490+i*670,315,650,171,3)
 image('profile_icon_tactics','styleIcon',514,342,58,58,3);text('stylePrimaryLabel',594,334,520,27,'IDENTIDADE DE JOGO',19,MUTED,3);text('stylePrimary',594,378,520,45,size=33,section=3);text('stylePrimaryNote',514,449,600,25,'Preferência do técnico registrada na carreira',17,MUTED,3)
 text('styleSecondaryLabel',1184,334,600,27,'PREFERÊNCIA COMPLEMENTAR',19,MUTED,3);text('styleSecondary',1184,378,600,45,size=27,section=3)
 image('profile_style','styleContextCard',1160,506,650,389,3);text('styleClubLabel',1184,531,600,27,'VÍNCULO MAIS RECENTE',19,MUTED,3);text('styleClub',1184,573,600,39,size=30,section=3);text('styleTenure',1184,620,600,27,size=21,color=MUTED,section=3)
 text('styleNote',1184,704,600,30,'Uma identidade para cada treinador.',24,INK,3);text('styleNote2',1184,752,600,30,'As preferências acompanham os novos vínculos.',19,MUTED,3);text('styleNote3',1184,800,600,30,'Dados do vínculo atual desta carreira.',19,MUTED,3)
 button(1812,315,30,530,202,'profile_clear')
 return p
