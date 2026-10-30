from ui_theme import ACCENT, argb
import portable_paths as portable
"""Native FIFA card geometry for the venue and recent-results carousel pages."""
import textwrap
PAGE_NAMES=('ESCALAÇÕES','DADOS DA PARTIDA','ÚLTIMAS PARTIDAS')
CARD_X,CARD_Y,CARD_W,CARD_H=204,28,1512,818
CARD_RIGHT=CARD_X+CARD_W
CARD_BOTTOM=CARD_Y+CARD_H
PITCH_SCALE=.9
PITCH_Y=118
PITCH_X=(216,1106)
SUMMARY_X,SUMMARY_Y,SUMMARY_W,SUMMARY_H=826,118,264,641
CONTENT_BOTTOM=780
BAR_X,BAR_Y= CARD_RIGHT-270,CARD_BOTTOM-40
TEXT_BINDINGS=[]


def colors_by_result(result):
    return {'V':0xff277048,'E':0xff7b858c,'D':0xffc82d3d}[result]


def graphics(payload,place,text,sprite,shape_id,solid_shape,dot_shape,arrows,native_art):
    TEXT_BINDINGS.clear();label_owner='venuePage'
    details=payload.get('details',{});gate=details.get('gate',{})
    ink=0xff334b56;muted=0xff647982;gold=argb(ACCENT)
    def label(depth,x,y,w,h,size,name,value,color=0xff334b56,align=0):
        TEXT_BINDINGS.append((label_owner,name,str(value)))
        return text(depth,x,y,w,h,size,name,color,align=align,value=str(value))
    # Match details page: one readable metadata rail, one stadium hero and a
    # gate estimate using the club-finance rule for the actual home/away state.
    venue=[place(shape_id,1,0,0,1468,640,color=0xffedf1f2),
           place(shape_id,2,16,16,370,608,color=0xfffafcfb),
           place(shape_id,3,402,16,1050,404,color=0xffd7e0df),
           place(shape_id,4,402,432,1050,174,color=0xfffafcfb)]
    comp_art=native_art('S16Competition_'+str(details.get('competition_id',0)),58,'venueCompetitionArt')
    if comp_art is not None:venue.append(place(comp_art,5,32,32,label='venueCompetitionIcon'))
    venue.extend([label(6,104 if comp_art is not None else 32,29,260,25,16,'competitionKey','COMPETIÇÃO',muted),
                  label(7,104 if comp_art is not None else 32,56,260,54,25,'competitionValue',details.get('competition','Não informada'),ink),
                  place(shape_id,8,30,117,340,2,color=0xffd5dddd),
                  label(9,32,136,330,24,16,'dateKey','DATA',muted),
                  label(10,32,162,330,38,28,'dateValue',details.get('date','Não informada'),ink),
                  label(11,32,218,330,24,16,'timeKey','HORÁRIO',muted),
                  label(12,32,244,330,38,28,'timeValue',details.get('time','Não informado'),ink),
                  label(13,32,300,330,24,16,'capacityKey','CAPACIDADE',muted),
                  label(14,32,326,330,38,26,'capacityValue',details.get('capacity','Não informada'),ink),
                  place(shape_id,15,30,383,340,2,color=0xffd5dddd)])
    host=native_art('S16Crest_'+str(details.get('home_id',0)),58,'hostCrest')
    if host is not None:venue.append(place(host,16,32,412,label='hostCrestArt'))
    venue.extend([label(17,104 if host is not None else 32,411,260,24,16,'hostKey','MANDANTE',muted),
                  label(18,104 if host is not None else 32,438,260,54,25,'hostValue',details.get('home_name','Não informado'),ink),
                  label(19,32,524,330,72,17,'gateReason',gate.get('reason','Estimativa indisponível.'),muted)])
    stadium_art=native_art('S16StadiumPreview',1050,'stadiumPhoto')
    if stadium_art is not None:venue.append(place(stadium_art,20,402,16,label='stadiumPhotoArt'))
    else:
        venue.extend([place(shape_id,20,402,16,1050,404,color=0xffcedbd9),
                      place(shape_id,21,434,48,986,338,color=0xffbfcfcb),
                      label(34,434,163,986,45,28,'stadiumPhotoUnavailable','Imagem deste estádio indisponível',ink,2)])
    venue.extend([place(shape_id,22,402,314,1050,106,color=0xb51c2830),
                  label(23,430,330,982,42,33,'stadiumTitle',details.get('stadium','Estádio não informado'),0xffffffff),
                  label(24,432,371,980,28,20,'stadiumLocation',details.get('location','Local da partida'),0xffe4e8e7),
                  label(25,430,448,572,24,17,'gateKey','BILHETERIA ESTIMADA',muted),
                  label(26,430,480,572,51,40,'gateValue',''),
                  place(shape_id,27,430,545,590,16,color=0xffe2e8e7),
                  place(shape_id,28,430,545,590*max(0,min(10000,int(gate.get('occupancy_bps',0))))/10000,16,color=gold),
                  label(29,430,565,590,25,17,'gateOccupancy',str(round(gate.get('occupancy_bps',0)/100))+'% da capacidade',muted),
                  place(shape_id,30,1052,452,2,132,color=0xffd5dddd),
                  label(31,1080,448,330,24,17,'attendanceKey','PÚBLICO ESTIMADO',muted),
                  label(32,1080,480,330,50,38,'attendanceValue',
                        (str(details.get('crowd_percent'))+'%') if details.get('crowd_percent') is not None else 'Não disponível',ink),
                  label(33,1080,533,330,28,17,'attendanceUnit',
                        (f"≈ {int(details['expected_attendance']):,}".replace(',','.')+' torcedores')
                        if details.get('expected_attendance') is not None else 'Estimativa da Central indisponível',muted)])
    venue=sprite(venue)

    histories=[]
    for side in ('user','opponent'):
        label_owner='userHistory' if side=='user' else 'opponentHistory'
        team=payload[side];primary=team.get('header_color',argb(ACCENT));fg=0xff000000|team.get('header_ink',0xffffff)
        controls=[place(shape_id,1,0,0,704,640,color=0xffedf0ed),place(shape_id,2,0,0,704,84,color=primary),
                  label(3,90,19,586,46,32,'teamName',team['name'],fg),place(sprite([]),4,18,13,label='crest'),
                  label(5,26,105,650,32,23,'subtitle','ÚLTIMOS 5 JOGOS NESTA CARREIRA')]
        games=team.get('recent',[])
        colors={'V':0xff277048,'E':0xff6c747c,'D':0xffae3544}
        for i,game in enumerate(games):
            y=146+i*90;depth=20+i*10
            crest=native_art('S16Crest_'+str(game['opponent_id']),44,'opponentArt'+str(i))
            controls.extend([place(shape_id,depth,24,y,656,82,color=0xfffafbf9),
                             place(shape_id,depth+1,36,y+23,36,36,color=colors[game['result']]),
                             label(depth+2,36,y+24,36,35,23,'result'+str(i),game['result'],0xffffffff,align=2),
                             place(crest,depth+3,90,y+18,label='opponentCrest'+str(i)),
                             label(depth+4,150,y+5,388,30,24 if len(game['opponent'])<26 else 21,'opponent'+str(i),game['opponent']),
                             label(depth+5,150,y+35,388,23,17,'date'+str(i),game['date_text']+' · '+game['venue'],0xff647982),
                             label(depth+6,550,y+18,116,40,29,'score'+str(i),game['score'],align=2)])
            competition='S16Competition_'+str(game.get('competition_id',0))
            icon=native_art(competition,18,'competitionArt'+str(i))
            if icon is not None:controls.append(place(icon,depth+7,150,y+59,label='competitionIcon'+str(i)))
            controls.append(label(depth+8,176 if icon is not None else 150,y+58,474,23,17,'competition'+str(i),game.get('competition','Competição não informada'),0xff647982))
        if not games:controls.append(label(60,32,260,640,140,27,'empty','Ainda não há resultados concluídos disponíveis.'))
        controls.append(label(80,26,610,650,30,17,'legend','V: vitória   E: empate   D: derrota'))
        histories.append(sprite(controls))

    # Three columns share a baseline. Every label is inside a real MovieClip,
    # so the native runtime and the offline renderer use identical bindings.
    label_owner='lineupSummary'
    navy=0xff163652;muted=0xff6b7d86
    center=[place(shape_id,1,0,0,SUMMARY_W,SUMMARY_H,color=0xfff1f3f0)]
    def center_label(depth,x,y,w,h,size,name,value,color=navy,align=0):
        return label(depth,x,y,w,h,size,name,value,color,align)
    competition=native_art('S16Competition_'+str(details.get('competition_id',0)),64,'competitionIcon')
    if competition is not None:center.append(place(competition,2,9,16,label='competitionLogo'))
    title=details.get('competition','Calendário da carreira')
    title_lines=textwrap.wrap(title,width=15 if competition is not None else 24,break_long_words=False) or ['']
    for i,line in enumerate(title_lines[:3]):
        center.append(center_label(3+i,82 if competition is not None else 10,18+i*26,
            172 if competition is not None else 244,28,22 if len(line)<17 else 18,
            'competitionName' if i==0 else 'competitionLine'+str(i),line))
    for i,y in enumerate((108,326,506)):
        center.append(place(shape_id,10+i,10,y,244,2,color=0xffd5dddd))
    # Native vector cues keep the date and venue legible without relying on
    # fonts containing emoji or external icon files.
    center.extend([place(shape_id,14,15,135,19,18,color=navy),
                   place(shape_id,15,17,141,15,10,color=0xfff1f3f0),
                   place(shape_id,16,19,132,3,7,color=navy),
                   place(shape_id,17,27,132,3,7,color=navy)])
    center.extend([center_label(20,46,122,210,23,15,'dateLabel','DATA / HORÁRIO',muted),
                   center_label(21,46,149,210,32,20,'dateTime',details.get('date','Não informada')+' · '+details.get('time','')),
                   center_label(22,14,195,236,22,15,'stadiumLabel','ESTÁDIO',muted)])
    stadium=details.get('stadium','Não informado')
    for i,line in enumerate(textwrap.wrap(stadium,width=24,break_long_words=False)[:2]):
        center.append(center_label(23+i,14,221+i*28,236,30,22 if len(stadium)<24 else 19,
            'stadiumName' if i==0 else 'stadiumLine'+str(i),line))
    location=details.get('location','')
    if location:center.append(center_label(25,14,283,236,38,17,'location',location,muted))
    h2h=payload.get('head_to_head',{});total=h2h.get('games',0)
    center.append(center_label(30,10,343,244,30,22,'h2hTitle','CONFRONTO DIRETO',align=2))
    # Use a dark neutral on this light panel even for white club lettering.
    tally=(h2h.get('user_wins',0),h2h.get('draws',0),h2h.get('opponent_wins',0))
    for i,(value,caption,color) in enumerate(zip(tally,('VITÓRIAS','EMPATES','VITÓRIAS'),(0xffb9303b,0xff6e7d88,navy))):
        x=10+i*82
        center.extend([center_label(31+i*2,x,384,80,42,35,'h2hCount'+str(i),str(value) if total else '—',color,2),
                       center_label(32+i*2,x,426,80,22,14,'h2hLabel'+str(i),caption,muted,2)])
    center.append(place(shape_id,40,16,459,232,10,color=0xffd5dddd))
    if total:
        x=16
        for i,(count,color) in enumerate(zip(tally,(0xffb9303b,0xff9ba5ab,navy))):
            width=232*count/total
            if width:center.append(place(shape_id,41+i,x,459,width,10,color=color))
            x+=width
    center.append(center_label(44,10,480,244,22,14,'h2hScope',
        str(total)+' jogo'+('s' if total!=1 else '')+' registrado'+('s' if total!=1 else '')+' na carreira' if total else 'Sem confrontos registrados',muted,2))
    center.append(center_label(50,10,522,244,25,19,'formTitle','ÚLTIMOS 5 JOGOS',align=2))
    for row,side in enumerate(('user','opponent')):
        team=payload[side];y=558+row*43
        crest=native_art('S16Crest_'+str(team['team_id']),30,'formCrestArt'+str(row))
        if crest is not None:center.append(place(crest,51+row*20,10,y,label='formCrest'+str(row)))
        games=team.get('recent',[])[:5]
        if not games:center.append(center_label(52+row*20,52,y+3,200,28,15,'formEmpty'+str(row),'Sem jogos concluídos',muted))
        for i,game in enumerate(games):
            x=52+i*39;depth=53+row*20+i*2
            center.extend([place(shape_id,depth,x,y,34,32,color=colors_by_result(game['result'])),
                           center_label(depth+1,x,y+1,34,31,22,'form'+str(row)+'_'+str(i),game['result'],0xffffffff,2)])

    # Same sloped dark footer and lime/grey pagination cues as career cards.
    bar=solid_shape(((0,1),(44/270,0),(1,0),(1,0),(1,1),(0,1)))
    left,right=arrows
    circle=dot_shape
    def button(arrow):
        return sprite([place(shape_id,1,0,0,34,32,color=0xff26343c),place(arrow,2,12,10,9,12,color=0xffe4ebeb)])
    # Native shapes are not addressable MovieClips. Use root strip instances
    # with baked colors so the selected dot never depends on a shape setter.
    strips=[sprite([place(circle,1+i,146+i*34,12,16,16,color=argb(ACCENT) if i==page else 0xff839196) for i in range(3)]) for page in range(3)]
    dot=sprite([place(shape_id,1,0,0,18,18,color=0x01ffffff)])
    label_owner=None
    return [place(sprite(center),9,SUMMARY_X,SUMMARY_Y,label='lineupSummary'),
            place(venue,10,226,118,label='venuePage',color=0x00ffffff),
            place(histories[0],11,226,118,label='userHistory',color=0x00ffffff),
            place(histories[1],12,990,118,label='opponentHistory',color=0x00ffffff),
            place(bar,19,BAR_X,BAR_Y,270,40,label='paginationBar',color=0xff26343c),
            *[place(strip,30+i,BAR_X,BAR_Y,label='pageStrip'+str(i),color=0xffffffff if i==0 else 0x00ffffff) for i,strip in enumerate(strips)],
            place(button(left),20,BAR_X+47,BAR_Y+4,label='previousPage'),
            place(button(right),21,BAR_X+85,BAR_Y+4,label='nextPage'),
            *[place(dot,23+i,BAR_X+146+i*34,BAR_Y+12,label='pageDot'+str(i)) for i in range(3)]]


def methods(a,payload,b):
    R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;M=b.MANAGER;EQ=b.equal
    def init(a):
        for parent,name,value in TEXT_BINDINGS:a.set(P(T(parent),name) if parent else T(name),'text',value)
        for name in ('previousPage','nextPage'):
            a.set(T(name),'owner',R(1))
            a.set(T(name),'onRelease',T('PreviousPageClick' if name=='previousPage' else 'NextPageClick'))
        for i in range(3):
            a.set(T('pageDot'+str(i)),'owner',R(1));a.set(T('pageDot'+str(i)),'pageIndex',i);a.set(T('pageDot'+str(i)),'onRelease',T('PageDotClick'))
        for side,key in (('userHistory','user'),('opponentHistory','opponent')):
            a.do(R(1),'LoadCrest',P(T(side),'crest'),payload[key]['team_id'])
        details=payload.get('details',{});gate=details.get('gate',{})
        from career_currency import format_money
        a.set(P(T('venuePage'),'gateValue'),'text',format_money(gate.get('gross',0),details.get('currency'),symbol=details.get('currency_symbol')))
        a.do(R(1),'ShowPage',0)
    a.function('InitCarousel',0,init)
    def show(a):
        a.set(R(1),'carouselPage',R(2))
        a.when(('bin',72,T('carouselPage'),0),lambda a:a.set(R(1),'carouselPage',2))
        a.when(('bin',103,T('carouselPage'),2),lambda a:a.set(R(1),'carouselPage',0))
        for child,index in (('userPitch',0),('opponentPitch',0),('lineupSummary',0),('venuePage',1),('userHistory',2),('opponentHistory',2)):
            a.set(T(child),'_visible',EQ(T('carouselPage'),index));a.set(T(child),'_alpha',100)
        for i in range(3):
            a.set(T('pageStrip'+str(i)),'_visible',EQ(T('carouselPage'),i));a.set(T('pageStrip'+str(i)),'_alpha',100)
        a.set(T('screenTitle'),'text',('index',('array',PAGE_NAMES),T('carouselPage')))
        statuses=('Provável escalação adversária. As escolhas finais podem mudar até a partida.',
                  'Estádio, capacidade e bilheteria estimada da próxima partida.',
                  'Resultados desta carreira, do mais recente ao mais antigo.')
        a.set(T('status'),'text',('index',('array',statuses),T('carouselPage')))
        if not payload.get('available',True):
            for child in ('userPitch','opponentPitch','lineupSummary','venuePage'):a.set(T(child),'_visible',False)
            a.set(T('status'),'text','Não há próxima partida agendada nesta carreira.')
    a.function('ShowPage',1,show)
    a.function('PreviousPageClick',0,lambda a:a.do(P(R(1),'owner'),'ShowPage',('bin',11,P(P(R(1),'owner'),'carouselPage'),1)))
    a.function('NextPageClick',0,lambda a:a.do(P(R(1),'owner'),'ShowPage',('bin',71,P(P(R(1),'owner'),'carouselPage'),1)))
    a.function('PageDotClick',0,lambda a:a.do(P(R(1),'owner'),'ShowPage',P(R(1),'pageIndex')))
    def key(a):
        a.when(EQ(R(2),P(M('InputCodes'),'BACK')),lambda a:(a.do(b.ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''),a.do(M('InputManager'),'DisableCurrentLocalEventHandler'),a.ret(True)))
        for name,delta in (('LAS_LEFT',-1),('LAS_RIGHT',1),('UI_LEFT',-1),('UI_RIGHT',1),('UILEFT',-1),('UIRIGHT',1),('PREVIOUS',-1),('NEXT',1)):
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,delta=delta:(a.do(R(1),'ShowPage',('bin',71,T('carouselPage'),delta)),a.ret(True)))
        a.ret(True)
    a.function('LocalEventHandler',2,key)
