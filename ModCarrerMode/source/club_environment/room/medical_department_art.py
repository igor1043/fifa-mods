"""Clean clinical boards using only the current career's observed information."""
from PIL import Image,ImageDraw
from room_medical_r53 import font,fit_text,paste,native_image,player_portrait

INK=(37,56,66);MUTED=(102,120,129);GOLD=(174,150,98);LINE=(220,226,228)


def date_label(value):
 s=str(value);return f'{s[6:8]}/{s[4:6]}/{s[:4]}' if len(s)==8 else 'Data indisponível'


def base(title,subtitle,size):
 im=Image.new('RGBA',size,(247,249,249,255));d=ImageDraw.Draw(im)
 d.text((54,36),title,font=font(48,True),fill=INK)
 d.text((56,100),subtitle,font=font(26),fill=MUTED);d.rectangle((54,151,size[0]-54,155),fill=GOLD)
 return im,d


def label(d,text,xy,width,size=28,bold=False,color=INK):
 text,f=fit_text(d,text,width,size,bold);d.text(xy,text,font=f,fill=color)


def injury_board(context,read_asset,page):
 medical=context['medical'];size=max(6,medical.get('pageSize',6));players=medical['players'][page*size:(page+1)*size]
 im,d=base('SITUAÇÃO DOS JOGADORES',context['club_name']+'  ·  '+date_label(context['date']),(2048,1084))
 for text,x in [('JOGADOR',165),('LESÃO',790),('TEMPO RESTANTE',1305),('PREVISÃO DE VOLTA',1630)]:d.text((x,183),text,font=font(23,True),fill=MUTED)
 if not players:
  d.text((60,400),'Elenco sem lesões registradas',font=font(54,True),fill=INK)
  d.text((62,483),'Os dados serão atualizados com o andamento da carreira.',font=font(30),fill=MUTED)
 height=min(121,760/max(1,len(players)))
 for index,p in enumerate(players):
  y=234+index*height;d.rectangle((54,y,1994,y+height-6),fill=(255,255,255))
  portrait,_=player_portrait(read_asset,p['player']);paste(im,portrait,(64,int(y+2),84,int(height-12)))
  label(d,p.get('name') or 'Jogador',(165,y+22),595,32,True)
  label(d,p.get('injury') or 'Não informado',(790,y+26),490,25)
  days=p.get('remainingDays');text=f'{days} dia'+('s' if days!=1 else '') if days is not None else p.get('return') or 'Não informado'
  label(d,text,(1305,y+25),300,29,True)
  label(d,p.get('forecastDate') or 'Não informada',(1630,y+25),340,29)
 d.text((56,1030),f'Página {page+1}/{medical["pages"]}  ·  Previsões sujeitas à evolução no jogo.',font=font(24),fill=MUTED)
 return im


def summary_board(context):
 m=context['medical'];im,d=base('SAÚDE DO ELENCO',context['club_name'],(1680,1040))
 values=[('JOGADORES',str(m.get('rosterCount','—'))),('DISPONÍVEIS',str(m.get('availableCount','—'))),('EM RECUPERAÇÃO',str(m.get('unavailableCount',len(m['players']))))]
 for i,(title,value) in enumerate(values):
  x=60+i*540;d.text((x,225),title,font=font(27,True),fill=MUTED);d.text((x,280),value,font=font(96,True),fill=INK)
 d.line((60,445,1620,445),fill=LINE,width=2)
 for y,title,key in [(510,'Média de idade do elenco','averageAge'),(685,'Média de idade dos lesionados','injuredAverageAge')]:
  d.text((60,y),title,font=font(37,True),fill=INK);value=m.get(key)
  d.text((60,y+58),f'{value:.1f}'.replace('.',',')+' anos' if value is not None else 'Não informada',font=font(56,True),fill=GOLD)
 d.text((60,940),'Atualizado em '+date_label(context['date']),font=font(27),fill=MUTED)
 return im


def followup_board(context):
 m=context['medical'];im,d=base('ACOMPANHAMENTO',date_label(context['date'])+'  ·  Recuperação dos atletas',(1680,1000))
 for i,p in enumerate(m['players'][:5]):
  y=205+i*135;label(d,p.get('name','Jogador'),(60,y),1060,34,True)
  days=p.get('remainingDays');text=f'{days} dias restantes' if days is not None else 'Prazo não informado'
  d.text((60,y+46),text,font=font(27),fill=MUTED)
  if p.get('recovery') is not None:
   value=max(0,min(100,p['recovery']));d.rectangle((1020,y+25,1600,y+43),fill=LINE)
   if value:d.rectangle((1020,y+25,1020+5.8*value,y+43),fill=GOLD)
   d.text((1020,y+57),str(value)+'% do prazo observado',font=font(23),fill=MUTED)
 if not m['players']:d.text((60,330),'Nenhum atleta em recuperação',font=font(46,True),fill=INK)
 d.text((60,930),'Acompanhamento do prazo do jogo; não representa avaliação clínica.',font=font(24),fill=MUTED)
 return im


def identity_wall(context,read_asset):
 im=Image.new('RGBA',(2320,600),(240,241,238,255));d=ImageDraw.Draw(im)
 crest=native_image(read_asset,[f'data/ui/imgassets/crest/light/l{context["club"]}.dds']);paste(im,crest,(90,82,310,400))
 d.text((470,130),'DEPARTAMENTO MÉDICO',font=font(107,True),fill=INK)
 label(d,context['club_name'],(478,278),1760,65,True)
 primary=tuple(round(255*c) for c in context['colors'][0]);d.rectangle((478,385,2160,394),fill=primary)
 d.text((478,438),'AVALIAÇÃO   ·   RECUPERAÇÃO   ·   DESEMPENHO',font=font(39),fill=MUTED)
 return im


def door_sign(context,read_asset,kind):
 from room_interior_r71 import club_sign
 crest=native_image(read_asset,[f'data/ui/imgassets/crest/light/l{context["club"]}.dds'])
 return club_sign(context,'DEPARTAMENTO MÉDICO' if kind=='medical' else 'COMISSÃO TÉCNICA',kind,crest)
