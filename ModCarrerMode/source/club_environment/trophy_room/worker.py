"""Demand-driven gallery publication, hosted by the existing room asset worker."""
from pathlib import Path
import hashlib,json,math,shlex,time,threading
from PIL import Image
from . import assets,data,presentation

ORIGIN_X=-100000.


def matrix(x=0,y=0,z=0,yaw=0,scale=1,offset=(0,0,0)):
    c,s=math.cos(yaw),math.sin(yaw);ox,oy,oz=offset
    return [c*scale,0,-s*scale,0,0,scale,0,0,s*scale,0,c*scale,0,
            ORIGIN_X+x+scale*(c*ox+s*oz),1000+y+scale*oy,z+scale*(-s*ox+c*oz),1]


def scoped_request(game,pid):
    p=Path(game)/'ModCarrerMode/runtime/trophy_room/request.json'
    if not p.is_file():return None
    r=json.loads(p.read_text(encoding='utf8'))
    if r['pid']!=pid or not r['requested'] or not r['club'] or not r['epoch']:return None
    return r


def generate(game,pid,req):
    game=Path(game);folder=game/'ModCarrerMode/runtime/trophy_room';folder.mkdir(parents=True,exist_ok=True)
    raw=(game/'ModCarrerMode/runtime/career_fce_snapshot.json').read_bytes();snap=json.loads(raw)
    if any(snap.get(k)!=req[v] for k,v in [('pid','pid'),('club','club'),('fceContextEpoch','epoch')]):
        raise InterruptedError('Aguardando a publicação da carreira atual')
    identity,cups=assets.club_identity(game,req['club']);collection=req.get('collection','club')
    assets.atomic(folder/'loading_identity.json',json.dumps(dict(pid=pid,club=req['club'],club_name=identity['name']),ensure_ascii=False).encode('utf8'))
    all_rows,branch=data.title_rows(game,snap,collection)
    real_titles=len(all_rows);preview=data.demo_rows(game,req['club'],snap['date']//10000) if not all_rows else []
    if preview:all_rows=preview
    all_rows=data.grouped_titles(all_rows)
    if req.get('presentation')=='list':
        from . import cabinet
        return cabinet.publish(game,pid,req,snap,identity,cups,all_rows,branch)
    rows,page,pages=data.page_rows(all_rows,req.get('page',0));style='custom' if req.get('custom') and data.custom_available(game,req['club']) else 'default'
    layout=json.loads((game/assets.PREFIX/'layout.json').read_text(encoding='utf8'))
    wall=game/'ModCarrerMode/data/trophy_room/custom'/str(req['club'])/'identity-wall.png'
    enhanced=req.get('gallery_views',1)>=2;collections=req.get('gallery_views',1)>=3;probes=req.get('gallery_views',1)>=4
    wall_stamp=wall.stat().st_mtime_ns if wall.is_file() else 0
    signature=hashlib.sha256(json.dumps(['native-stream-v10-manual-cups-coach-wall',enhanced,probes,collection,pid,req['epoch'],req['club'],branch,rows,page,style,wall_stamp,layout['revision']],sort_keys=True).encode()).hexdigest()[:16]
    # Snapshot generations can change without a new title. Reuse the gallery
    # instead of repainting plaques or loading the same native assets again.
    try:
        prior=json.loads((folder/'publication.json').read_text(encoding='utf8'))
        if prior.get('signature')==signature and (folder/'components.txt').is_file():return signature
    except (OSError,ValueError):pass
    # Follow the same native data mount as the dressing room and player views.
    destination=game/assets.PREFIX/str(pid)/signature;destination.mkdir(parents=True,exist_ok=True)
    # The room is shared by both collections. Its materials must have stable
    # paths so the renderer reuses them instead of reloading the architecture.
    appearance_key=hashlib.sha256(json.dumps([identity,style,wall_stamp,layout['revision']],sort_keys=True).encode()).hexdigest()[:16]
    appearance=game/assets.PREFIX/'appearance'/appearance_key;appearance.mkdir(parents=True,exist_ok=True)
    template=game/'ModCarrerMode/data/trophy_room/texture-template.rx3';components=[]
    for row in rows:
        row['club']=row.get('club',req['club']);winner,_=assets.club_identity(game,row['club']);row['club_name']=winner['name']
    def texture(key,image,shared=False):
        path=(appearance if shared else destination)/(key+'.rx3')
        if not shared or not path.is_file():assets.rx_texture(image,template,'gallery_cm',path)
        return str(path.relative_to(game)).replace('\\','/')
    default_aux=assets.PREFIX+'normal.rx3'
    for binding in layout['bindings']:
        # Both collections share the panel geometry; the coach wall uses its
        # own neutral texture and never loads the current club's custom image.
        c=dict(binding);key=c['key'];c.update(aux=default_aux,normal='gallery_nm',coeff_texture=assets.PREFIX+('metal.rx3' if c.get('metal') else 'matte.rx3'),coeff='gallery_coeff',matrices=[matrix()])
        if key=='gallery':c['baked']=True
        elif key=='identity':c['texture']=texture('coach-identity-v1',assets.coach_identity_image(),True) if collection=='coach' else texture(key,assets.identity_image(game,identity,style=='custom'),True)
        elif key.startswith('plaque_'):
            index=int(key.split('_')[1]);row=rows[index] if index<len(rows) else None
            c['texture']=texture(key if row else 'empty-plaque',assets.plaque(game,row,index),row is None)
        elif key in ('primary','secondary'):
            color=identity['colors'][0 if key=='primary' else 1];c['texture']=texture(key,Image.new('RGBA',(8,8),(*color,255)),True)
        elif key=='exit':
            im=Image.new('RGBA',(512,128),'#284b3d');assets.center(__import__('PIL.ImageDraw',fromlist=['Draw']).Draw(im),(256,64),'SAÍDA',65,'#ffffff',True);c['texture']=texture(key,im,True)
        elif key=='glass':c['texture']=texture(key,Image.new('RGBA',(8,8),(220,230,232,21)),True)
        elif key=='emission':c['texture']=texture(key,Image.new('RGBA',(8,8),(255,248,224,255)),True);c['baked']=True
        elif key=='chrome':c['texture']=texture(key,Image.new('RGBA',(8,8),(194,201,203,255)),True)
        components.append(c)
    missing=[];native_models={};visits=[]
    for index,row in enumerate(rows):
        ident=data.trophy_id(row['competition'],row['root'],cups,lambda i:(game/f'data/sceneassets/trophy/trophy_{i}.rx3').is_file())
        if not ident:missing.append(row);continue
        try:cup=assets.native_cup(game,ident)
        except (OSError,ValueError):missing.append(row);continue
        slot=layout['slots'][index]
        visits.append(presentation.visit(slot,cup))
        for part in cup['parts']:
            key=(ident,part)
            if key not in native_models:
                c=dict(key=f'cup_{ident}_{len(native_models)}',model=cup['model'],texture=cup['texture'],diffuse=cup['diffuse'],submesh=part,
                       aux=cup['texture'] if cup['normal'] else default_aux,normal=cup['normal'] or 'gallery_nm',
                       coeff_texture=cup['texture'] if cup['coeff'] else assets.PREFIX+'metal.rx3',coeff=cup['coeff'] or 'gallery_coeff',
                       alpha='glass' in part.lower(),metal=True,matrices=[],
                       lighting_point=[-cup['offset'][0],-cup['offset'][1]+cup['native_dimensions_cm'][1]/2,-cup['offset'][2]])
                native_models[key]=c;components.append(c)
            native_models[key]['matrices'].append(matrix(slot['x'],slot['y'],slot['z'],slot['yaw'],cup['scale'],cup['offset']))
        row['trophy_id']=ident
        row['native_dimensions_cm']=cup['native_dimensions_cm'];row['display_dimensions_cm']=cup['display_dimensions_cm']
        row['scale']=cup['scale'];row['sizing']=cup['sizing']
    current=scoped_request(game,pid)
    if not current or any(current.get(k)!=req.get(k) for k in ('pid','club','epoch','custom','page','collection','presentation')):raise InterruptedError('A sala foi fechada ou alterada')
    live=json.loads((game/'ModCarrerMode/runtime/career_fce_snapshot.json').read_bytes())
    if any(live.get(k)!=snap.get(k) for k in ('pid','club','fceContextEpoch','date','savePath')):raise InterruptedError('A carreira mudou durante a preparação da sala')
    generation=int(signature[:7],16)
    from . import cabinet
    title_cards=cabinet.records(game,req,cups,rows)
    assets.atomic(folder/'detail-cards.tsv',cabinet.serialize('S16TITLECARDS',pid,req,generation,len(all_rows),page,pages,title_cards))
    if enhanced:
        camera_lines=[f'S16TROPHYCAM 1 {generation} {len(visits)}']
        for v in visits:
            values=[*v['eye'],*v['target'],v['fov'],*v['detail_eye'],*v['detail_target'],v['detail_fov']]
            camera_lines.append(str(v['slot'])+' '+' '.join(format(x,'.9g') for x in values))
        assets.atomic(folder/'cameras.txt',('\n'.join(camera_lines)+'\n').encode('utf8'))
    # A bounded text manifest lets the renderer validate every path/instance.
    lines=[f'S16TROPHY {3 if probes else 2 if collections else 1} {pid} {req["club"]} {req["epoch"]} {generation} {int(style=="custom")} {len(components)} {len(all_rows)} {page} {pages}'+(' '+str(int(collection=='coach')) if collections else '')]
    quote=lambda text:json.dumps(str(text),ensure_ascii=False)
    for c in components:
        fields=[c['key'],c['model'],c['submesh'],c['texture'],c['diffuse'],c['aux'],c['normal'],c['coeff_texture'],c['coeff']]
        probe=' '+' '.join(format(float(v),'.9g') for v in c.get('lighting_point',[0,150,0])) if probes else ''
        lines.append(' '.join(map(quote,fields))+f' {int(c.get("alpha",False))} {int(c.get("baked",False))} {len(c["matrices"])}'+probe)
        lines.extend(' '.join(format(v,'.9g') for v in m) for m in c['matrices'])
    assets.atomic(folder/'components.txt',('\n'.join(lines)+'\n').encode('utf8'))
    assets.atomic(folder/'publication.json',json.dumps(dict(schema=1,signature=signature,pid=pid,epoch=req['epoch'],club=req['club'],branch=branch,
        generation=generation,style=style,custom_available=data.custom_available(game,req['club']),titles=all_rows,shown=rows,page=page,pages=pages,
        missing_models=missing,components=len(components),preview=bool(preview),real_titles=real_titles,save=snap['savePath'],date=snap['date'],renderer='native FIFA GameplayProp',
        lighting=layout.get('lighting','legacy room material; native trophy material classes'),appearance=appearance_key,
        gallery_views=4 if probes else 3 if collections else 2 if enhanced else 1,collection=collection,cameras=visits,scale_policy='native dimensions, reduction only when larger than case'),ensure_ascii=False,indent=2).encode('utf8'))
    return signature


def poll(game,pid,state):
    """No extraction or rebuilding on unrelated pages or calendar ticks."""
    try:
        req=scoped_request(game,pid)
        if not req:state.clear();return False
        snapshot=Path(game)/'ModCarrerMode/runtime/career_fce_snapshot.json'
        ready=Path(game)/'ModCarrerMode/runtime/manager_market/state_ready.json'
        wall=Path(game)/'ModCarrerMode/data/trophy_room/custom'/str(req['club'])/'identity-wall.png'
        settings=Path(game)/'ModCarrerMode/config/trophy_room.ini'
        key=tuple(req[k] for k in ('pid','club','epoch','custom','page'))+(req.get('gallery_views',1),req.get('collection','club'),req.get('presentation','3d'),req.get('shelf_page',0),snapshot.stat().st_mtime_ns,ready.stat().st_mtime_ns if ready.is_file() else 0,wall.stat().st_mtime_ns if wall.is_file() else 0,settings.stat().st_mtime_ns if settings.is_file() else 0)
        if key!=state.get('key'):
            state['signature']=generate(game,pid,req);state['key']=key
            state.pop('error',None)
        return True
    except (OSError,ValueError,KeyError,InterruptedError,__import__('sqlite3').Error) as error:
        # Diagnostics never escape into the dressing-room worker.
        label=type(error).__name__+': '+str(error)
        if state.get('error')!=label:
            path=Path(game)/'ModCarrerMode/runtime/trophy_room/worker.log';path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('a',encoding='utf8') as f:f.write(label+'\n')
            state['error']=label
        return False


_services={}


def watch(game,pid,stop,alive=None,interval=.5):
    """A dedicated asset lane: room building and coach simulation never gate it."""
    if alive is None:
        import psutil
        alive=lambda:psutil.pid_exists(pid)
    state={}
    while not stop.is_set() and alive():
        try:poll(game,pid,state)
        except Exception as error:
            # A renderer/asset failure remains local to this service.
            label=type(error).__name__+': '+str(error)
            if state.get('service_error')!=label:
                path=Path(game)/'ModCarrerMode/runtime/trophy_room/worker.log'
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('a',encoding='utf8') as f:f.write(label+'\n')
                state['service_error']=label
        stop.wait(interval)


def start_service(game,pid):
    key=(str(Path(game).resolve()),int(pid));prior=_services.get(key)
    if prior and prior[0].is_alive():return prior
    stop=threading.Event();thread=threading.Thread(target=watch,args=(game,pid,stop),name='TrophyGalleryAssets',daemon=True)
    _services[key]=(thread,stop);thread.start();return thread,stop
