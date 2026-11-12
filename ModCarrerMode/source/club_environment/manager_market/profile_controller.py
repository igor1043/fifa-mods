"""Emit the profile's native AVM controller using the common screen helpers."""
from profile_layout import TAB_X,TITLE_TOP,TITLE_STEP,HISTORY_THUMB_MIN
from profile_art import STATUS_TONES

def emit(a,scenes,*,R,T,P,ix,add,mul,lt,EQ,both,either,clamp,div,CALL,PATH,field,show):
 root=T('scene1');p=ix(T('people'),T('person'));ov=ix(p,23);visual=ix(p,26);tab=T('profileTab');history=either(either(EQ(tab,1),EQ(tab,2)),EQ(tab,4))
 for node in scenes[1]['nodes']:
  if node.get('section') is not None:a.set(P(root,node['name']),'_visible',EQ(tab,node['section']))
 for j,button in enumerate(scenes[1]['actions']):
  code=int(button['target']);btn=P(root,'action'+str(j))
  a.set(P(btn,'selected'),'_alpha',mul(EQ(T('focus'),code),60))
  if code in (70,71):a.set(btn,'_visible',history)
  elif code==202:a.set(btn,'_visible',history)
  elif code==90:a.set(btn,'_visible',EQ(tab,0))
  if 80<=code<=84:a.set(P(btn,'selected'),'_alpha',0)
 for i in range(5):
  field(a,root,'profileTabOff'+str(i),('Visão geral','Passagens','Títulos','Estilo de jogo','Histórico anual')[i],('not',EQ(tab,i)))
  field(a,root,'profileTabOn'+str(i),('Visão geral','Passagens','Títulos','Estilo de jogo','Histórico anual')[i],EQ(tab,i))
  a.when(EQ(tab,i),lambda a,i=i:show(a,root,'profileMark'+str(i),TAB_X[i],190))
 field(a,root,'name',ix(p,0));field(a,root,'nationality',ix(p,11));field(a,root,'bio',add(ix(p,13),' anos'),lt(-1,ix(p,13)));field(a,root,'currentClub',ix(ov,15));field(a,root,'clubStatus','Clube atual');a.when(('not',ix(ov,16)),lambda a:field(a,root,'clubStatus','',False))
 field(a,root,'salary',ix(p,17));field(a,root,'style',ix(p,14));field(a,root,'formation',ix(p,15));field(a,root,'profileCaption','');field(a,root,'scope',ix(ov,14))
 for name,col in (('contractUntil',27),('contractRemaining',28),('contractSince',29),('contractState',30)):field(a,root,name,ix(visual,col))
 a.when(('not',ix(ov,16)),lambda a:(field(a,root,'contractInfoHeading','DISPONIBILIDADE'),field(a,root,'contractSince','Pode assumir um novo clube'),field(a,root,'contractState',ix(p,16))))
 field(a,root,'trust',add(ix(ov,17),'%'),lt(-1,ix(ov,17)));a.when(lt(ix(ov,17),0),lambda a:field(a,root,'trust','—'));field(a,root,'trustStatus',ix(ov,18))
 for name,x,y in (('identityCard',96,190),('trustTrack',118,703)):show(a,root,name,x,y)
 for i,(x,y) in enumerate(((112,426),(112,523),(285,523))):show(a,root,'identityTile'+str(i),x,y)
 show(a,root,add('img_',ix(p,9)),112,218);show(a,root,add('img_',ix(p,12)),286,219);show(a,root,add('rating',ix(p,10)),286,390)
 a.when(lt(0,ix(ov,17)),lambda a:(show(a,root,'trustFill',118,703),a.set(P(root,'trustFill'),'_width',mul(3.22,ix(ov,17)))))
 a.when(ix(ov,16),lambda a:show(a,root,add('current_',ix(ov,16)),286,294))
 def overview(a):
  for i in range(6):field(a,root,'metric'+str(i),add('',ix(ov,i)));field(a,root,'metricNote'+str(i),ix(visual,i))
  for i in range(3):
   percent=ix(ov,6+i);field(a,root,'venuePercent'+str(i),ix(ov,20+i));field(a,root,'venueDetail'+str(i),ix(visual,6+i));a.set(P(root,'venueFill'+str(i)),'_width',mul(3.88,percent))
  a.set(R(1),'profileRecent',ix(visual,add(9,T('profileVenue'))));forms=T('profileRecent')
  field(a,root,'filterName',ix(('array',('Todos os jogos','Em casa','Fora de casa')),T('profileVenue')))
  field(a,root,'recentEmpty','Nenhum placar individual disponível para este filtro.',EQ(P(forms,'length'),0))
  for i in range(10):
   code=CALL(forms,'charAt',i);present=lt(i,P(forms,'length'));field(a,root,'recentLetter'+str(i),code,present)
   a.when(present,lambda a,i=i,code=code:show(a,root,add('recent'+str(i)+'_',code),550+i*117,779))
 a.when(EQ(tab,0),overview,lambda a:field(a,root,'recentEmpty','',False))
 def style(a):
  for name,col in (('stylePrimary',22),('styleSecondary',23),('styleClub',12),('styleTenure',25)):field(a,root,name,ix(visual,col))

 a.when(EQ(tab,3),style)
 a.when(EQ(tab,2),lambda a:a.set(R(1),'profileRows',ix(p,25)),lambda a:a.when(EQ(tab,4),lambda a:a.set(R(1),'profileRows',ix(p,27)),lambda a:a.set(R(1),'profileRows',ix(p,24))))
 a.set(R(1),'historyPages',CALL(PATH('Math'),'max',1,('bin',11,P(T('profileRows'),'length'),2)));a.set(R(1),'historyPage',clamp(T('historyPage'),0,('bin',11,T('historyPages'),1)))
 field(a,root,'historyPage',add(add(add('Página ',add(T('historyPage'),1)),add(' de ',T('historyPages'))),add(' · ',add(P(T('profileRows'),'length'),' registros'))),history)
 def title_caption(a):
  count=P(T('profileRows'),'length')
  field(a,root,'scope',add(count,' títulos conquistados nesta carreira · Mais recentes primeiro'))
  first=CALL(PATH('Math'),'min',count,add(T('historyPage'),1));last=CALL(PATH('Math'),'min',count,add(T('historyPage'),3))
  field(a,root,'historyPage',add(add(add(add(first,'–'),last),' de '),add(count,' títulos')))
 a.when(EQ(tab,2),title_caption)
 field(a,root,'historyLeft','‹',history);field(a,root,'historyRight','›',history)
 field(a,root,'emptyProfile','Nenhuma passagem registrada nesta carreira.',both(EQ(tab,1),EQ(P(T('profileRows'),'length'),0)))
 a.when(EQ(tab,2),lambda a:field(a,root,'emptyProfile','Nenhum título confirmado nesta carreira.',EQ(P(T('profileRows'),'length'),0)))
 for i in range(3):
  idx=add(T('historyPage'),i);r=ix(T('profileRows'),idx);present=both(history,lt(idx,P(T('profileRows'),'length')));y=315+i*182
  for name in ('entryName','entryStatus','entryDates','entryTotal','entryHome','entryAway'):field(a,root,name+str(i),'',False)
  for name in ('titleName','titleDate','titleClub','titleYear'):field(a,root,name+str(i),'',False)
  for j in range(6):
   field(a,root,'entryValue'+str(i)+'_'+str(j),'',False);a.set(P(root,'entryLabel'+str(i)+'_'+str(j)),'_visible',False)
  def row(a,i=i,r=r,y=y):
   def passage(a):
    show(a,root,'entryCard'+str(i),490,y)
    show(a,root,add('entry'+str(i)+'_',ix(r,1)),510,y+18)
    for name,value in (('entryName',ix(r,0)),('entryStatus',add(ix(r,4),add(' · ',ix(r,11)))),('entryDates',add(ix(r,2),add(' · ',ix(r,3)))),('entryHome',ix(r,12))):field(a,root,name+str(i),value)
    def status_tag(a):
     field(a,root,'entryStatus'+str(i),ix(r,4));field(a,root,'entryDates'+str(i),add(ix(r,2),add(' · ',add(ix(r,3),add(' · ',ix(r,11))))))
     for label,tone in STATUS_TONES.items():a.when(EQ(ix(r,4),label),lambda a,tone=tone:show(a,root,'entryBadge'+str(i)+'_'+tone,1486,y+11))
    a.when(EQ(tab,1),status_tag)
    for j in range(6):field(a,root,'entryValue'+str(i)+'_'+str(j),ix(r,13+j));a.set(P(root,'entryLabel'+str(i)+'_'+str(j)),'_visible',True)
    for side,col,x in (('Home',6,609),):
     show(a,root,'entry'+side+'Track'+str(i),x,y+151);show(a,root,'entry'+side+'Fill'+str(i),x,y+151);a.set(P(root,'entry'+side+'Fill'+str(i)),'_width',mul(11.67,ix(r,col)))
   def title(a):
    ty=TITLE_TOP+i*TITLE_STEP
    for name,x,offset in (('titleCard',530,0),('titleWell',548,15),('titleYearBadge',1680,18),('titleTimelineDot',494,66)):
     show(a,root,name+str(i),x,ty+offset)
    show(a,root,add('titleCompetition'+str(i)+'_',ix(r,1)),696,ty+20)
    show(a,root,add('titleCup'+str(i)+'_',add('cup_',CALL(ix(r,1),'substr',12))),554,ty+20)
    show(a,root,add('titleCrest'+str(i)+'_',ix(r,3)),696,ty+101)
    for name,value in (('titleName',ix(r,0)),('titleYear',ix(r,4)),('titleDate',ix(r,6)),('titleClub',ix(r,2))):field(a,root,name+str(i),value)
   a.when(EQ(tab,2),title,passage)
  a.when(present,row)

 def timeline_rail(a):
  show(a,root,'titleTimelineRail',504,TITLE_TOP+77)
  remaining=('bin',11,P(T('profileRows'),'length'),T('historyPage'))
  a.set(P(root,'titleTimelineRail'),'_height',mul(TITLE_STEP,('bin',11,CALL(PATH('Math'),'min',3,remaining),1)))
 a.when(both(EQ(tab,2),lt(1,P(T('profileRows'),'length'))),timeline_rail)
 def scrollbar(a):
  thumb=CALL(PATH('Math'),'max',HISTORY_THUMB_MIN,div(1590,CALL(PATH('Math'),'max',3,P(T('profileRows'),'length'))))
  show(a,root,'historyScrollTrack',1822,315);show(a,root,'historyScrollThumb',1822,315)
  a.set(P(root,'historyScrollThumb'),'_height',thumb)
  a.set(P(root,'historyScrollThumb'),'_y',add(315,mul(div(T('historyPage'),CALL(PATH('Math'),'max',1,('bin',11,T('historyPages'),1))),('bin',11,530,thumb))))
 a.when(both(history,lt(3,P(T('profileRows'),'length'))),scrollbar)
