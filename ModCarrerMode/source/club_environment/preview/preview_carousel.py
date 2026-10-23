import portable_paths as portable
"""Native FIFA card geometry for the venue and recent-results carousel pages."""
PAGE_NAMES=('ESCALAÇÕES','DADOS DA PARTIDA','ÚLTIMAS PARTIDAS')
CARD_X,CARD_Y,CARD_W,CARD_H=204,148,1512,742
CARD_RIGHT=CARD_X+CARD_W
CARD_BOTTOM=CARD_Y+CARD_H
PITCH_SCALE=.75
PITCH_Y=166
PITCH_X=(308,1112)
CONTENT_BOTTOM=808
BAR_X,BAR_Y= CARD_RIGHT-270,CARD_BOTTOM-40
TEXT_BINDINGS=[]


def graphics(payload,place,text,sprite,shape_id,solid_shape,dot_shape,arrows,native_art):
    TEXT_BINDINGS.clear();label_owner='venuePage'
    def card(items,primary,ink):
        return sprite([place(shape_id,1,0,0,1468,640,color=0xffedf0ed),
                       place(shape_id,2,0,0,1468,84,color=primary)]+items)
    user=payload['user'];details=payload.get('details',{})
    color=0xffd9e0e1;ink=0xff334b56
    def label(depth,x,y,w,h,size,name,value,color=0xff334b56,align=0):
        TEXT_BINDINGS.append((label_owner,name,str(value)))
        return text(depth,x,y,w,h,size,name,color,align=align,value=str(value))
    items=[label(3,32,20,1380,52,34,'heading','DADOS DA PARTIDA',ink)]
    labels=(('COMPETIÇÃO',details.get('competition','Não informada')),
            ('DATA',details.get('date','Não informada')),
            ('HORÁRIO',details.get('time','Não informado')),
            ('ESTÁDIO',details.get('stadium','Não informado')),
            ('CAPACIDADE',details.get('capacity','Não informada')),
            ('MANDANTE',details.get('home_name','Não informado')))
    for i,(name,value) in enumerate(labels):
        x=34+(i%2)*720;y=108+(i//2)*146
        items.extend([place(shape_id,10+i*3,x,y,696,126,color=0xfffafbf9),
                      label(11+i*3,x+20,y+15,656,28,20,'key'+str(i),name,0xff647982),
                      label(12+i*3,x+20,y+56,656,52,29 if len(str(value))<36 else 23,'value'+str(i),value)])
    items.append(label(50,34,588,1390,36,18,'source','Local previsto da próxima partida.'))
    venue=card(items,color,ink)

    histories=[]
    for side in ('user','opponent'):
        label_owner='userHistory' if side=='user' else 'opponentHistory'
        team=payload[side];primary=team.get('header_color',0xff163e62);fg=0xff000000|team.get('header_ink',0xffffff)
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

    # Same sloped dark footer and lime/grey pagination cues as career cards.
    bar=solid_shape(((0,1),(44/270,0),(1,0),(1,0),(1,1),(0,1)))
    left,right=arrows
    circle=dot_shape
    def button(arrow):
        return sprite([place(shape_id,1,0,0,34,32,color=0xff26343c),place(arrow,2,12,10,9,12,color=0xffe4ebeb)])
    # Native shapes are not addressable MovieClips. Use root strip instances
    # with baked colors so the selected dot never depends on a shape setter.
    strips=[sprite([place(circle,1+i,146+i*34,12,16,16,color=0xffd7f51b if i==page else 0xff839196) for i in range(3)]) for page in range(3)]
    dot=sprite([place(shape_id,1,0,0,18,18,color=0x01ffffff)])
    label_owner=None
    return [place(venue,10,226,166,label='venuePage',color=0x00ffffff),
            place(histories[0],11,226,166,label='userHistory',color=0x00ffffff),
            place(histories[1],12,990,166,label='opponentHistory',color=0x00ffffff),
            place(bar,19,BAR_X,BAR_Y,270,40,label='paginationBar',color=0xff26343c),
            *[place(strip,30+i,BAR_X,BAR_Y,label='pageStrip'+str(i),color=0xffffffff if i==0 else 0x00ffffff) for i,strip in enumerate(strips)],
            place(button(left),20,BAR_X+47,BAR_Y+4,label='previousPage'),
            place(button(right),21,BAR_X+85,BAR_Y+4,label='nextPage'),
            *[place(dot,23+i,BAR_X+146+i*34,BAR_Y+12,label='pageDot'+str(i)) for i in range(3)],
            label(22,226,826,1130,31,23,'pageLabel','ESCALAÇÕES',0xff334b56)]


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
        a.do(R(1),'ShowPage',0)
    a.function('InitCarousel',0,init)
    def show(a):
        a.set(R(1),'carouselPage',R(2))
        a.when(('bin',72,T('carouselPage'),0),lambda a:a.set(R(1),'carouselPage',2))
        a.when(('bin',103,T('carouselPage'),2),lambda a:a.set(R(1),'carouselPage',0))
        for child,index in (('userPitch',0),('opponentPitch',0),('venuePage',1),('userHistory',2),('opponentHistory',2)):
            a.set(T(child),'_visible',EQ(T('carouselPage'),index));a.set(T(child),'_alpha',100)
        a.set(T('pageLabel'),'text',('index',('array',PAGE_NAMES),T('carouselPage')))
        for i in range(3):
            a.set(T('pageStrip'+str(i)),'_visible',EQ(T('carouselPage'),i));a.set(T('pageStrip'+str(i)),'_alpha',100)
        a.set(T('screenTitle'),'text',('bin',71,'PRÓXIMA PARTIDA — ',('index',('array',PAGE_NAMES),T('carouselPage'))))
        statuses=('Provável escalação adversária. As escolhas finais podem mudar até a partida.',
                  'Estádio e capacidade do mandante.',
                  'Resultados desta carreira, do mais recente ao mais antigo.')
        a.set(T('status'),'text',('index',('array',statuses),T('carouselPage')))
        if not payload.get('available',True):
            for child in ('userPitch','opponentPitch','venuePage'):a.set(T(child),'_visible',False)
            a.set(T('status'),'text','Não há próxima partida agendada nesta carreira.')
    a.function('ShowPage',1,show)
    a.function('PreviousPageClick',0,lambda a:a.do(P(R(1),'owner'),'ShowPage',('bin',11,P(P(R(1),'owner'),'carouselPage'),1)))
    a.function('NextPageClick',0,lambda a:a.do(P(R(1),'owner'),'ShowPage',('bin',71,P(P(R(1),'owner'),'carouselPage'),1)))
    a.function('PageDotClick',0,lambda a:a.do(P(R(1),'owner'),'ShowPage',P(R(1),'pageIndex')))
    def key(a):
        a.when(EQ(R(2),P(M('InputCodes'),'BACK')),lambda a:(a.do(b.ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''),a.do(M('InputManager'),'DisableCurrentLocalEventHandler'),a.ret(True)))
        for name,delta in (('LEFT',-1),('RIGHT',1),('UI_LEFT',-1),('UI_RIGHT',1),('UILEFT',-1),('UIRIGHT',1),('PREVIOUS',-1),('NEXT',1),('L1',-1),('R1',1)):
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,delta=delta:(a.do(R(1),'ShowPage',('bin',71,T('carouselPage'),delta)),a.ret(True)))
        a.ret(True)
    a.function('LocalEventHandler',2,key)
