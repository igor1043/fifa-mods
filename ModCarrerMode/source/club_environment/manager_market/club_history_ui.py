"""Native club picker and a bounded three-row timeline, loaded on demand."""
def scenes(model,assets,shell,card,text,image,action,pager,club_xy,*,INK,MUTED,LIGHT):
    from profile_art import STATUS_TONES
    clubs=shell(model,'clubHistory','Histórico do clube')
    from manager_layout import country_league_selector
    country_league_selector(clubs)
    text(clubs,'clubCount',110,622,330,32,'',22,MUTED)
    for key in assets:
        if key.startswith('flag_'):image(clubs,key,'country_'+key,151,365,48,30)
        elif key.startswith('league_'):image(clubs,key,'league_'+key,147,523,60,68)
        elif key.startswith('crest_'):image(clubs,key,'hc_'+key,0,0,96,100)
    for i in range(6):
        x,y=club_xy(i);card(clubs,x,y,654,180,40+i);text(clubs,'historyClub'+str(i),x+150,y+33,478,42,'',27)
        clubs.text(x+150,y+91,478,48,'Técnicos, aproveitamento e títulos nesta carreira',18,MUTED);clubs.nodes[-1].update(slot=i,name='historyNote'+str(i))
        clubs.text(x+150,y+143,470,25,'Ver histórico do clube  ›',18,INK);clubs.nodes[-1].update(slot=i,name='historyLink'+str(i))
    pager(clubs);text(clubs,'empty',520,560,1200,80,'',25,MUTED)
    timeline=shell(model,'clubTimeline','Histórico do clube')
    text(timeline,'timelineClub',182,275,1350,42,'',30);text(timeline,'timelineCaption',182,321,1300,27,'',19,MUTED)
    action(timeline,1620,279,180,44,583,'‹  Clubes',size=22)
    for key in assets:
        if key.startswith('crest_'):image(timeline,key,'history_'+key,96,275,66,70)
    for i in range(3):
        y=365+i*179;card(timeline,118,y,1660,164,540+i)
        for key in assets:
            if key.startswith('head_'):image(timeline,key,'tl'+str(i)+'_'+key,142,y+18,124,124)
        for tone in set(STATUS_TONES.values()):image(timeline,'status_'+tone,'timelineBadge'+str(i)+'_'+tone,1454,y+16,300,36)
        text(timeline,'tlName'+str(i),290,y+15,1120,37,'',28)
        text(timeline,'tlStatus'+str(i),1470,y+23,270,26,'',18)
        text(timeline,'tlDates'+str(i),290,y+59,1440,27,'',20,MUTED)
        text(timeline,'tlNumbers'+str(i),290,y+98,1100,29,'',22)
        text(timeline,'tlTitles'+str(i),1470,y+106,270,29,'',22)
        text(timeline,'tlEfficiency'+str(i),290,y+132,350,24,'',18,MUTED)
        image(timeline,'track','tlTrack'+str(i),640,y+143,760,7)
        image(timeline,'accent','tlBar'+str(i),640,y+143,760,7)
    text(timeline,'timelineEmpty',160,530,1600,60,'Nenhum vínculo registrado para este clube.',27,MUTED)
    text(timeline,'timelineCount',170,929,1350,30,'',19,MUTED)
    action(timeline,1620,921,65,37,581,'‹',size=25);action(timeline,1713,921,65,37,582,'›',size=25)
    action(timeline,1814,365,28,522,203);timeline.nodes[-1]['background_asset']='profile_clear'
    image(timeline,'track','timelineScrollTrack',1824,365,6,522);image(timeline,'accent','timelineScrollThumb',1824,365,6,522)
    return clubs.pack(),timeline.pack()

def emit(a,model,scenes,*,R,T,P,ix,add,sub,mul,div,lt,EQ,both,clamp,CALL,PATH,arr,loop,field,show,pages,dots,club_xy):
    from profile_art import STATUS_TONES
    def picker(a):
        root=T('scene6');a.set(R(1),'leagueRows',arr([]))
        loop(a,'i',P(T('leagues'),'length'),lambda a:a.when(EQ(ix(ix(T('leagues'),T('i')),2),ix(ix(T('countries'),T('country')),0)),lambda a:a.do(T('leagueRows'),'push',ix(T('leagues'),T('i')))))
        a.set(R(1),'leagueIndex',0);loop(a,'i',P(T('leagueRows'),'length'),lambda a:a.when(EQ(ix(ix(T('leagueRows'),T('i')),0),T('league')),lambda a:a.set(R(1),'leagueIndex',T('i'))))
        l=ix(T('leagueRows'),T('leagueIndex'));a.set(R(1),'filtered',arr([]))
        loop(a,'i',P(T('historyClubs'),'length'),lambda a:a.when(EQ(ix(ix(T('historyClubs'),T('i')),3),T('league')),lambda a:a.do(T('filtered'),'push',ix(T('historyClubs'),T('i')))))
        pages(a,T('filtered'),'page',6)
        for name,value in (('countryName',ix(ix(T('countries'),T('country')),0)),('countryCount',add(add(add(T('country'),1),' / '),P(T('countries'),'length'))),('leagueName',ix(l,1)),('leagueCount',add(add(add(T('leagueIndex'),1),' / '),P(T('leagueRows'),'length'))),('leagueLevel',add(ix(l,3),'ª divisão')),('clubCount',add(P(T('filtered'),'length'),' clubes'))):field(a,root,name,value)
        show(a,root,add('country_',ix(ix(T('countries'),T('country')),1)),151,365);show(a,root,add('league_',ix(l,4)),147,523)
        for i in range(6):
            idx=add(mul(T('page'),6),i);r=ix(T('filtered'),idx);present=lt(idx,P(T('filtered'),'length'));x,y=club_xy(i)
            field(a,root,'historyClub'+str(i),ix(r,0),present)
            a.when(present,lambda a,r=r,x=x,y=y:show(a,root,add('hc_',ix(r,1)),x+25,y+29))
        dots(a,root,'page',T('pageCount'),'',1100)
        field(a,root,'pageText',add(add(add('Página ',add(T('page'),1)),add(' de ',T('pageCount'))),add(' · ',add(P(T('filtered'),'length'),' clubes'))))
        field(a,root,'empty','Nenhum clube nesta liga.',EQ(P(T('filtered'),'length'),0))
    a.function('RefreshHistoryClubs',0,picker)
    def request(a):
        a.set(R(1),'clubTimeline',True);a.set(R(1),'timelinePage',0)
        a.when(EQ(R(2),T('historyLoadedClub')),lambda a:(a.set(R(1),'historyPending',False),a.ret()))
        a.set(R(1),'requestedHistoryClub',R(2));a.set(R(1),'historyRetry',0)
        a.set(R(1),'historyPending',True)
        wire=add('S16MGRH1|'+model.get('profileToken','')+'|',R(2))
        for key in ('country','league','page','focus'):wire=add(add(wire,'|'),T(key))
        wire=add(wire,'|END');a.do(PATH('ION_CareerMode'),'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ClubHistory',wire)
    a.function('RequestClubHistory',1,request)
    from live_payload import emit as live_emit
    def received(a,payload):
        data=P(payload,'data')
        for key,source in (('timelineRows','rows'),('historyClubName','name'),('historyClubCrest','crest'),('historyLoadedClub','club')):a.set(R(1),key,P(data,source))
        a.set(R(1),'historyPending',False);a.set(R(1),'timelinePage',0);a.set(R(1),'focus',540);a.do(R(1),'Refresh')
    live_emit(a,'history','managerhistory',lambda d:both(both(EQ(P(d,'kind'),'history'),EQ(P(d,'token'),model.get('profileToken',''))),both(EQ(P(d,'club'),T('requestedHistoryClub')),EQ(P(d,'date'),model['date']))),received,interval=6)
    def timeline(a):
        from manager_layout import TAB_STEP
        root=T('scene7');data=model.get('clubHistory') or {};rows=T('timelineRows');length=P(rows,'length')
        show(a,root,'tabMark3',96+3*TAB_STEP,203)
        pages(a,rows,'timelinePage',1);a.set(R(1),'timelinePageCount',CALL(PATH('Math'),'max',1,sub(length,2)));a.set(R(1),'timelinePage',clamp(T('timelinePage'),0,sub(T('timelinePageCount'),1)))
        field(a,root,'timelineClub',T('historyClubName'));field(a,root,'timelineCaption','Técnicos que comandaram o clube · Todos os anos desta carreira')
        a.when(T('historyClubCrest'),lambda a:show(a,root,add('history_',T('historyClubCrest')),96,275))
        field(a,root,'timelineEmpty','Nenhum vínculo registrado para este clube.',EQ(length,0))
        a.when(lt(T('focus'),540),lambda a:a.set(R(1),'focus',540))
        a.when(EQ(length,0),lambda a:a.set(R(1),'focus',583))
        for i in range(3):
            row=ix(rows,add(T('timelinePage'),i));present=lt(add(T('timelinePage'),i),length);y=365+i*179
            for name,value in (('tlName',ix(row,0)),('tlDates',add(ix(row,2),add(' - ',ix(row,3)))),('tlStatus',ix(row,4)),('tlNumbers',add(add(add(add(add(add(add(ix(row,5),' jogos  ·  '),ix(row,6)),' V  ·  '),ix(row,7)),' E  ·  '),ix(row,8)),' D')),('tlTitles',add(ix(row,10),' títulos'))):field(a,root,name+str(i),value,present)
            a.when(present,lambda a,row=row,i=i,y=y:show(a,root,add('tl'+str(i)+'_',ix(row,1)),142,y+18))
            field(a,root,'tlEfficiency'+str(i),add('Aproveitamento ',ix(row,9)),present)
            for name in ('tlTrack','tlBar'):a.set(P(root,name+str(i)),'_visible',present)
            a.set(P(root,'tlBar'+str(i)),'_width',mul(7.6,clamp(ix(row,12),0,100)))
            for label,tone in STATUS_TONES.items():a.when(both(present,EQ(ix(row,4),label)),lambda a,i=i,tone=tone,y=y:show(a,root,'timelineBadge'+str(i)+'_'+tone,1454,y+16))
            a.when(both(present,EQ(ix(row,10),'1')),lambda a,i=i:field(a,root,'tlTitles'+str(i),'1 título'))
        a.set(R(1),'focusable',arr([583,581,582]))
        for j,button in enumerate(scenes[7]['actions']):
            code=int(button['target']);visible=lt(add(T('timelinePage'),code-540),length) if 540<=code<=542 else lt(3,length) if code==203 else True
            a.set(P(root,'action'+str(j)),'_visible',visible)
            a.set(P(P(root,'action'+str(j)),'selected'),'_alpha',mul(EQ(T('focus'),code),100))
            if 540<=code<=542:a.when(visible,lambda a,code=code:a.do(T('focusable'),'push',code))
        field(a,root,'timelineCount',add(add(add(T('timelinePage'),1),'–'),add(CALL(PATH('Math'),'min',add(T('timelinePage'),3),length),add(' de ',add(length,' passagens')))),lt(0,length))
        show(a,root,'timelineScrollTrack',1824,365);show(a,root,'timelineScrollThumb',1824,365);a.set(P(root,'timelineScrollThumb'),'_height',div(1566,CALL(PATH('Math'),'max',3,length)));a.set(P(root,'timelineScrollThumb'),'_y',add(365,mul(div(T('timelinePage'),CALL(PATH('Math'),'max',1,sub(length,3))),sub(522,div(1566,CALL(PATH('Math'),'max',3,length))))))
        for name in ('timelineScrollTrack','timelineScrollThumb'):a.set(P(root,name),'_visible',lt(3,length))
    a.function('RefreshClubTimeline',0,timeline)
    def move(a):
        a.set(R(1),'timelineFocusBefore',T('focus'));focus=T('timelineFocusBefore')
        def down(a):
            a.when(EQ(focus,583),lambda a:a.set(R(1),'focus',540))
            a.when(both(both(lt(539,focus),lt(focus,542)),lt(add(T('timelinePage'),sub(focus,539)),P(T('timelineRows'),'length'))),lambda a:a.set(R(1),'focus',add(focus,1)))
            a.when(EQ(focus,542),lambda a:a.do(R(1),'Command',582))
        def up(a):
            a.when(both(lt(540,focus),lt(focus,543)),lambda a:a.set(R(1),'focus',sub(focus,1)))
            a.when(EQ(focus,540),lambda a:a.when(lt(0,T('timelinePage')),lambda a:a.do(R(1),'Command',581),lambda a:a.set(R(1),'focus',583)))
        a.when(EQ(R(2),3),down);a.when(EQ(R(2),2),up)
        a.when(lt(R(2),2),lambda a:a.do(R(1),'Command',add(581,EQ(R(2),1))))
        a.do(R(1),'Refresh')
    a.function('TimelineMove',1,move)
