"""Emit the profile's native AVM controller using the common screen helpers."""
from profile_layout import TAB_X

def emit(a,scenes,*,R,T,P,ix,add,mul,lt,EQ,both,either,clamp,div,CALL,PATH,field,show):
 root=T('scene1');p=ix(T('people'),T('person'));ov=ix(p,23);visual=ix(p,26);tab=T('profileTab');history=either(EQ(tab,1),EQ(tab,2))
 for node in scenes[1]['nodes']:
  if node.get('section') is not None:a.set(P(root,node['name']),'_visible',EQ(tab,node['section']))
 for j,button in enumerate(scenes[1]['actions']):
  code=int(button['target']);btn=P(root,'action'+str(j))
  a.set(P(btn,'selected'),'_alpha',mul(EQ(T('focus'),code),60))
  if code in (70,71):a.set(btn,'_visible',history)
  elif code==90:a.set(btn,'_visible',EQ(tab,0))
  if 80<=code<=83:a.set(P(btn,'selected'),'_alpha',0)
 for i in range(4):
  field(a,root,'profileTabOff'+str(i),('Visão geral','Passagem pelos clubes','Títulos','Estilo de jogo')[i],('not',EQ(tab,i)))
  field(a,root,'profileTabOn'+str(i),('Visão geral','Passagem pelos clubes','Títulos','Estilo de jogo')[i],EQ(tab,i))
  a.when(EQ(tab,i),lambda a,i=i:show(a,root,'profileMark'+str(i),TAB_X[i],190))
 field(a,root,'name',ix(p,0));field(a,root,'nationality',ix(p,11));field(a,root,'bio',add(ix(p,13),' anos'),lt(-1,ix(p,13)));field(a,root,'currentClub',ix(ov,15));field(a,root,'clubStatus','Clube atual');a.when(('not',ix(ov,16)),lambda a:field(a,root,'clubStatus','Livre no mercado'))
 field(a,root,'salary',ix(p,17));field(a,root,'style',ix(p,14));field(a,root,'formation',ix(p,15));field(a,root,'profileCaption','');field(a,root,'scope',ix(ov,14))
 field(a,root,'trust',add(ix(ov,17),'%'),lt(-1,ix(ov,17)));a.when(lt(ix(ov,17),0),lambda a:field(a,root,'trust','—'));field(a,root,'trustStatus',ix(ov,18))
 for name,x,y in (('identityCard',96,190),('photoMatte',118,244),('trustTrack',118,874),('trainerIcon',118,207)):show(a,root,name,x,y)
 show(a,root,add('img_',ix(p,9)),178,244);show(a,root,add('img_',ix(p,12)),118,519);show(a,root,add('rating',ix(p,10)),176,457)
 a.when(lt(0,ix(ov,17)),lambda a:(show(a,root,'trustFill',118,874),a.set(P(root,'trustFill'),'_width',mul(3.22,ix(ov,17)))))
 a.when(ix(ov,16),lambda a:show(a,root,add('current_',ix(ov,16)),118,594))
 def overview(a):
  for i in range(6):field(a,root,'metric'+str(i),add('',ix(ov,i)));field(a,root,'metricNote'+str(i),ix(visual,i))
  for i in range(3):
   percent=ix(ov,6+i);field(a,root,'venuePercent'+str(i),ix(ov,20+i));field(a,root,'venueDetail'+str(i),ix(visual,6+i));a.set(P(root,'venueFill'+str(i)),'_width',mul(3.88,percent))
  field(a,root,'careerCounts',ix(ov,23));field(a,root,'latestClub',ix(visual,12));field(a,root,'latestSince',ix(visual,14));field(a,root,'latestStatus',ix(visual,15))
  a.when(ix(visual,13),lambda a:show(a,root,add('latest_',ix(visual,13)),552,791))
  for i in range(6):field(a,root,'latestMetric'+str(i),ix(visual,16+i))
  a.set(R(1),'profileRecent',ix(visual,add(9,T('profileVenue'))));forms=T('profileRecent')
  field(a,root,'filterName',ix(('array',('Todos os jogos','Em casa','Fora de casa')),T('profileVenue')))
  field(a,root,'recentEmpty','Nenhuma partida registrada para este filtro.',EQ(P(forms,'length'),0))
  for i in range(10):
   code=CALL(forms,'charAt',i);present=lt(i,P(forms,'length'));field(a,root,'recentLetter'+str(i),code,present)
   a.when(present,lambda a,i=i,code=code:show(a,root,add('recent'+str(i)+'_',code),1237+i*54,828))
 a.when(EQ(tab,0),overview,lambda a:field(a,root,'recentEmpty','',False))
 def style(a):
  for name,col in (('stylePrimary',22),('styleSecondary',23),('styleFormation',24),('styleClub',12),('styleTenure',25)):field(a,root,name,ix(visual,col))
  a.when(EQ(ix(visual,26),'profile_pitch_empty'),lambda a:show(a,root,'tacticPending',640,601),lambda a:show(a,root,add('tactic_',ix(visual,26)),640,601))
 a.when(EQ(tab,3),style)
 a.when(EQ(tab,2),lambda a:a.set(R(1),'profileRows',ix(p,25)),lambda a:a.set(R(1),'profileRows',ix(p,24)))
 a.set(R(1),'historyPages',CALL(PATH('Math'),'max',1,CALL(PATH('Math'),'ceil',div(P(T('profileRows'),'length'),3))));a.set(R(1),'historyPage',clamp(T('historyPage'),0,('bin',11,T('historyPages'),1)))
 field(a,root,'historyPage',add(add(add('Página ',add(T('historyPage'),1)),add(' de ',T('historyPages'))),add(' · ',add(P(T('profileRows'),'length'),' registros'))),history)
 field(a,root,'historyLeft','‹',history);field(a,root,'historyRight','›',history)
 field(a,root,'emptyProfile','Nenhuma passagem registrada nesta carreira.',both(EQ(tab,1),EQ(P(T('profileRows'),'length'),0)))
 a.when(EQ(tab,2),lambda a:field(a,root,'emptyProfile','Nenhum título confirmado nesta carreira.',EQ(P(T('profileRows'),'length'),0)))
 for i in range(3):
  idx=add(mul(T('historyPage'),3),i);r=ix(T('profileRows'),idx);present=both(history,lt(idx,P(T('profileRows'),'length')));y=315+i*182
  for name in ('entryName','entryStatus','entryDates','entryTotal','entryHome','entryAway'):field(a,root,name+str(i),'',False)
  def row(a,i=i,r=r,y=y):
   show(a,root,'entryCard'+str(i),490,y)
   def passage(a):
    show(a,root,add('entry'+str(i)+'_',ix(r,1)),510,y+18)
    for name,value in (('entryName',ix(r,0)),('entryStatus',add(ix(r,4),add(' · ',ix(r,11)))),('entryDates',add(ix(r,2),add(' · ',ix(r,3)))),('entryTotal',ix(r,5)),('entryHome',add('Casa: ',ix(r,7))),('entryAway',add('Fora: ',ix(r,9)))):field(a,root,name+str(i),value)
    for side,col,x in (('Home',8,609),('Away',10,1220)):
     show(a,root,'entry'+side+'Track'+str(i),x,y+151);show(a,root,'entry'+side+'Fill'+str(i),x,y+151);a.set(P(root,'entry'+side+'Fill'+str(i)),'_width',mul(5.56,ix(r,col)))
   def title(a):
    show(a,root,add('trophy'+str(i)+'_',ix(r,1)),510,y+18)
    for name,value in (('entryName',ix(r,0)),('entryStatus',ix(r,4)),('entryDates',add(ix(r,2),add(' · ',ix(r,5)))),('entryTotal','Título confirmado pelos resultados da carreira.')):field(a,root,name+str(i),value)
   a.when(EQ(tab,1),passage,title)
  a.when(present,row)
