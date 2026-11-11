"""Neutral coach office: existing native furniture, restrained club accents."""
from pathlib import Path
import copy,hashlib,json
import numpy as np
from rx3 import Rx3,VERTEX
from room_visual_r68 import box,packed,read_mesh,replace_mesh,join
from room_interior_r71 import panel
from room_interior_r72 import write_groups
from room_prop_conversion import transform
from build_room_equipment import native_box

PREFIX='data/sceneassets/server16_dressing_room_v3/office_neutral/'
BOARDS=[(0,[-317.,1178.,2350.],260.,145.,(1,0,0)),
        (1,[746.,1170.,2070.],205.,125.,(-1,0,0)),
        (2,[746.,1170.,2370.],200.,130.,(-1,0,0)),
        (3,[-317.,1175.,2035.],210.,130.,(1,0,0)),
        (4,[-317.,1175.,1780.],180.,120.,(1,0,0)),
        (5,[550.,1170.,2587.],230.,130.,(0,0,-1))]
SCENES={
 'Sala do treinador · visão geral':[150,178,1685,245,130,2260,83],
 'Sala do treinador · quadro tático':[0,180,2110,-317,1178-1000,2350,67],
 'Sala do treinador · desempenho':[420,175,2070,746,170,2070,53],
 'Sala do treinador · mercado':[0,177,1780,-317,175,1780,52],
 'Sala do treinador · destaques':[0,177,2035,-317,175,2035,56],
 'Sala do treinador · classificação':[410,177,2370,746,170,2370,54]}
DESK=([350,1000,2320],[260,1000,2250],0,1)
SEATING=([-70,1000,2100],[535,1000,1840],90,.74)
BOARD=([660,1000,2490],[-85,1000,2350],-90,1)
SHELF=([650,1000,1970],[560,1000,2330],0,1)
PLANT=([-220,1000,1740],[660,1000,2530],0,1)
CLOCK=([150,1230,2586],[746,1260,2220],90,1)
GUESTS=([0,1000,2110],[-90,1000,2140],0,1)


def unpack(bits):
    a=np.stack([(bits.astype(np.int64)>>s)&1023 for s in (0,10,20)],axis=1)
    return np.where(a>=512,a-1024,a)/511.


def move(vertices,conversion):
    result=vertices.copy();pivot,destination,yaw,scale=conversion
    result['p'],n=transform(result['p'],unpack(result['n']),pivot,destination,yaw,scale)
    _,g=transform(np.zeros((len(result),3)),unpack(result['g']),[0,0,0],[0,0,0],yaw)
    result['n']=[packed(x) for x in n];result['g']=[packed(x) for x in g]
    return result


def shell():
    from room_coach_r76 import geometry,uv
    original,_=geometry(furniture=False)
    groups={k:[] for k in ('primary','secondary','wood','dark','metal','light','panels','crest','rug','shirts')}
    from room_coach_rug import geometry as rug_geometry
    groups['rug'].append(rug_geometry())
    groups['primary']=original['primary']  # Same solid boundary and doorway.
    groups['metal']=original['metal'];groups['light']=original['light']
    # Dark skirting and one 3 cm club-colour inlay; walls stay neutral.
    for lo,hi in [((-319.7,1000.4,1561),(-318.8,1009,2591)),
                  ((748.8,1000.4,1561),(749.7,1009,2591)),
                  ((-319.7,1000.4,2590.2),(749.7,1009,2591))]:groups['dark'].append(box(lo,hi))
    for center,width,normal in [([-319.5,1095,2080],1000,(1,0,0)),
                                ([749.5,1095,2080],1000,(-1,0,0)),
                                ([215,1095,2591.3],1070,(0,0,-1))]:
        groups['secondary'].append(panel(center,width,3,normal))
    # A small oak feature behind the coach, rather than a coloured arena wall.
    groups['dark'].append(box((98,1000.5,2588.9),(422,1268,2591)))
    for x in np.arange(100.,420.,4.):groups['wood'].append(box((x,1000.7,2588.2),(x+3.2,1267.5,2589.2)))
    groups['crest'].append(panel([260,1227,2587.7],52,52,(0,0,-1)))
    # Compact storage uses one shared wood material and physical door handles.
    groups['dark'].append(box((-313,1000.5,1760),(-262,1088,2310)))
    for z in np.arange(1763.,2300.,91.):
        groups['wood'].append(box((-261.9,1005,z),(-260.5,1084,min(z+86,2306))))
        groups['metal'].append(box((-260.1,1066,z+30),(-258.6,1068,z+56)))
    groups['wood'].append(box((-314,1088,1759),(-258,1090,2311)))
    groups['dark'].append(box((-313,1000.5,2495),(-257,1210,2580)))
    for z in (2497.,2538.):
        groups['wood'].append(box((-256.8,1004,z),(-255.5,1206,z+38)))
        groups['metal'].append(box((-255.3,1090,z+27),(-253.7,1109,z+29)))
    # TV corner faces the sofa, with a low cabinet rather than another wall
    # dashboard. Its pre-match picture reuses the existing live atlas cell.
    groups['dark'].append(box((744,1124,1740),(749,1228,1920)))
    groups['panels'].append(panel([743.8,1176,1830],170,85,(-1,0,0),uv(6)))
    groups['dark'].append(box((692,1001,1738),(741,1059,1922)))
    groups['wood'].append(box((690,1059,1736),(743,1063,1924)))
    for z in (1741.,1801.,1861.):
        groups['wood'].append(box((690.4,1005,z),(692.0,1055,z+57)))
        groups['metal'].append(box((689.9,1044,z+20),(690.3,1045.5,z+38)))
    for z in (1742.,1907.):groups['dark'].append(box((725,1063,z),(739,1091,z+12)))
    groups['dark'].append(box((531,1038.5,1845),(536,1039.6,1860)))
    for z in (1847.,1851.,1855.):groups['metal'].append(box((532,1039.6,z),(535,1039.8,z+1.4)))
    for kit,x in enumerate((420.,610.)):
        groups['dark'].append(box((x-50,1112.5,1558.8),(x+50,1257.5,1562)))
        groups['shirts'].append(panel([x,1185,1562.3],90,135,(0,0,1),(kit*.5,0,(kit+1)*.5,.75)))
    for cell,center,width,height,normal in BOARDS:
        n=np.array(normal)
        # Physical monitor cases, slightly proud of the wall. The active screen
        # sits 2 mm ahead of the case face, never on a coplanar backing layer.
        mid=np.array(center)-n*1.7
        extent=np.array([3.4,height+5,width+5] if n[0] else [width+5,height+5,3.4])/2
        groups['dark'].append(box((mid-extent).tolist(),(mid+extent).tolist()))
        groups['panels'].append(panel((np.array(center)+n*.2).tolist(),width,height,normal,uv(cell)))
    for v,_ in groups['wood']:
        p=v['p'];n=unpack(v['n']);axis=np.abs(n).argmax(1)
        v['uv'][:,0]=p[:,0]/80.;v['uv'][:,1]=1-(p[:,1]-1000)/240.
        v['uv'][axis==0,0]=p[axis==0,2]/80.
        v['uv'][axis==1,1]=p[axis==1,2]/80.
    return groups


def remove_coloured_office(rx,bindings):
    """Clip only office paint out of the shared primary/secondary materials."""
    from room_coach_r76 import clip_office
    import room_coach_r76 as coach
    old_left,old_front=coach.LEFT,coach.FRONT;removed={}
    try:
        coach.LEFT=-325.;coach.FRONT=1558.
        for slot,binding in enumerate(bindings):
            if binding['material'] not in ('secondary_wall_primary','secondary_wall_secondary'):continue
            v,ids=read_mesh(rx,slot);a,b=clip_office(v,ids)
            replace_mesh(rx,slot,a,b);removed[slot]={'before':len(ids)//3,'after':len(b)//3}
    finally:coach.LEFT,coach.FRONT=old_left,old_front
    return removed


def stage(game,output,baseline):
    game,output=Path(game),Path(output);output.mkdir(parents=True,exist_ok=True)
    office=copy.deepcopy(baseline)
    if office.get('layout_revision')!=2:raise ValueError('Neutral office requires the installed layout-2 baseline')
    audit=[];model_cache={}
    def write_model(name,rx):
        data=rx.build();relative=PREFIX+name+'_'+hashlib.sha256(data).hexdigest()[:14]+'.rx3'
        path=output/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        return relative
    def convert_model(model,name,conversion=None,mixed=False):
        if model in model_cache:return model_cache[model]
        rx=Rx3((game/model).read_bytes())
        for slot in range(len(rx.get(VERTEX))):
            v,ids=read_mesh(rx,slot)
            if mixed:
                tri=ids.reshape(-1,3);c=v['p'][tri].mean(1)
                masks=[((c[:,0]>210)&(c[:,0]<490)&(c[:,2]>2240)&(c[:,2]<2400),DESK),
                       ((c[:,0]>100)&(c[:,0]<200)&(c[:,2]>2560),CLOCK),
                       ((c[:,0]>600)&(c[:,2]<2050),SHELF)]
                covered=np.zeros(len(tri),bool);parts=[]
                for mask,conv in masks:
                    if (covered&mask).any():raise ValueError('Overlapping office prop zones')
                    covered|=mask
                    if mask.any():
                        expanded=v[tri[mask].reshape(-1)];parts.append((move(expanded,conv),np.arange(len(expanded),dtype='<u2')))
                if not covered.all():raise ValueError('An office prop has no verified destination')
                a,b=join(parts)
            else:a,b=move(v,conversion),ids
            replace_mesh(rx,slot,a,b)
        path=write_model(name,rx);model_cache[model]=path
        audit.append(dict(source=model,target=path,conversion=conversion,mixed=mixed));return path
    kept=[]
    for b in office['bindings']:
        key=b['key'];conversion=None
        if key.startswith('coach_pes_media_wall_'):continue  # Replaced by wall storage, no freestanding divider.
        if key.startswith(('coach_pes_sofa_set_','coach_pes_coffee_table_','coach_pes_table_vase_')):conversion=SEATING
        elif key.startswith(('coach_pes_desk_assembly_','coach_pes_office_chair_')):conversion=DESK
        elif key.startswith('coach_guest_chairs_'):conversion=GUESTS
        elif key.startswith('coach_pes_tactical_board_'):conversion=BOARD
        elif key.startswith('coach_pes_rolling_shelf_'):conversion=SHELF
        elif key.startswith('coach_pes_floor_plant_'):conversion=PLANT
        elif key.startswith('coach_prop_clock_face_'):conversion=CLOCK
        mixed=key.startswith('coach_desktop_props_')
        if conversion or mixed:
            b['model']=convert_model(b['model'],Path(b['model']).stem,conversion,mixed)
        kept.append(b)
    office['bindings']=kept
    for obstacle in office['obstacles']:
        name=obstacle['name'];conv=None
        if '/ seating ' in name or name.endswith('/ coffee_table'):conv=SEATING
        elif name.endswith(('/ desk_assembly','/ office_chair')):conv=DESK
        elif 'guest chair' in name:conv=GUESTS
        elif name.endswith('/ tactical_board'):conv=BOARD
        elif name.endswith('/ rolling_shelf'):conv=SHELF
        elif name.endswith('/ plant'):conv=PLANT
        if conv:obstacle.update(native_box(obstacle['lo'],obstacle['hi'],*conv))
    for name,lo,hi in [('low storage',[-314,.5,1759],[-258,90,2311]),('archive',[-313,.5,2495],[-253.7,210,2580]),
                       ('TV console',[690,.5,1736],[743,63,1924])]:
        office['obstacles'].append(dict(name='Coach office / '+name,lo=lo,hi=hi))
    # Replace the original coloured wall geometry only in its office variants.
    import room_v3 as room
    manifest=json.loads((game/room.PREFIX/'manifest.json').read_bytes())
    interior=room.PREFIX+manifest['model_files']['interior.rx3']
    original=office['replacements'][interior]
    rx=Rx3((game/original).read_bytes())
    spec=json.loads((game/room.OLD/'interior_r78.json').read_bytes())
    removed=remove_coloured_office(rx,spec['bindings'])
    office['replacements'][interior]=write_model('interior',rx)
    shell_file=output/PREFIX/'shell.rx3';shell_file.parent.mkdir(parents=True,exist_ok=True)
    bindings=write_groups(game/room.OLD/'locker_support_r68.rx3',shell(),shell_file)
    shell_name=write_model('shell',Rx3(shell_file.read_bytes()))
    office['replacements'][room.OLD+'coach_room_r76.rx3']=shell_name
    office.update(layout_revision=5,dashboard_revision=1,palette_style='coach_neutral',shell_bindings=bindings,
                  overview_pose=SCENES['Sala do treinador · visão geral'],scene_poses=SCENES,
                  neutral_wall_rgb=[232,229,222],wood_finish='wood_light',
                  design='Neutral coaching workspace, central desk, compact meeting corner, smaller live panels')
    report=dict(layout_revision=5,furniture=audit,coloured_wall_removal=removed,
                panels=[dict(cell=c,center=p,width=w,height=h) for c,p,w,h,_ in BOARDS],
                legacy_media_bindings_removed=2,office=office)
    return office,report


def restyle(game,output,baseline):
    """Refresh only the monitor shell; never transform installed furniture twice."""
    import room_v3 as room
    game,output=Path(game),Path(output)
    if baseline.get('layout_revision') not in (3,4,5) or baseline.get('palette_style')!='coach_neutral':
        raise ValueError('Monitor refresh requires the neutral office')
    office=copy.deepcopy(baseline);target=output/PREFIX/'monitor-shell.rx3';target.parent.mkdir(parents=True,exist_ok=True)
    bindings=write_groups(game/room.OLD/'locker_support_r68.rx3',shell(),target)
    relative=PREFIX+'shell_'+hashlib.sha256(target.read_bytes()).hexdigest()[:14]+'.rx3'
    (output/relative).write_bytes(target.read_bytes())
    office['replacements'][room.OLD+'coach_room_r76.rx3']=relative
    office.update(layout_revision=5,dashboard_revision=1,shell_bindings=bindings)
    if not any(o['name']=='Coach office / TV console' for o in office['obstacles']):
        office['obstacles'].append(dict(name='Coach office / TV console',lo=[690,.5,1736],hi=[743,63,1924]))
    return office
