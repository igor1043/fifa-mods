"""Generic first-launch screens; career-specific faces/names are never shipped."""
import shutil
import portable_paths as p

def generate():
    import bank_ui_r60,build_screen as b
    bank_ui_r60.build({'club':0,'budget':0,'date':None,'used':0,'can_borrow':False,'schedule':[],
                      'active':None,'ready':False,'nonce':'DISABLED','error':'Aguardando dados da carreira'})
    import build_preview
    side={'team_id':0,'name':'Aguardando dados da carreira','players':[],'portrait_ids':[],
          'formation':'','probable':False,'recent':[],'header_color':0xffd9e0e1,'header_ink':0x334b56}
    preview=build_preview.build({'available':False,'pid':0,'date':0,'fixture':[0]*11,
                                 'user':dict(side),'opponent':dict(side),'details':{}})
    import build_loading
    build_loading.build(p.GAME/'data/ui/game/screens/career/server16/matchpreviewloading.big')
    build_loading.build(p.GAME/'data/ui/game/screens/career/server16/transfermarketloading.big','market')
    import finance_ui
    finance_ui.build(dict(ready=False,club=0,club_name='Aguardando carreira',date=0,start=0,budget=0,
        months=[],agreements=[],settings={},nonce='DISABLED',currency=0,ack=0),
        p.GAME/'data/ui/game/screens/career/server16/clubfinance.big')
    import build_dressing_card_20261022 as room
    from PIL import Image
    import io,struct
    image=io.BytesIO();Image.new('RGBA',(64,64),(0,0,0,0)).save(image,format='DDS',pixel_format='DXT5')
    dds=bytearray(image.getvalue());struct.pack_into('<I',dds,20,len(dds)-128);struct.pack_into('<I',dds,88,0)
    screen=room.screen({'pid':0,'club':0,'club_name':'Aguardando dados da carreira','scene_catalog':[]},lambda _:bytes(dds))
    targets={b.HERE/'package/data/ui/game/screens/career/server16/bankloans.big':'bankloansv2.big',
             preview:'matchpreview.big',screen:'dressingroom.big'}
    for source,name in targets.items():
        target=p.GAME/'data/ui/game/screens/career/server16'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
