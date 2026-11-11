"""V3 native RX3 dressing room. V2 geometry remains an immutable input.

The installed shell, doors, coach room and medical annex are retained. Only
the furniture inside the locker envelopes is replaced by one instanced bay.
This module never opens a career file for writing.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import copy
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from rx3 import Rx3, VERTEX
from room_visual_r68 import VERT, packed, box, join, read_mesh, replace_mesh
from room_interior_r71 import panel
from room_interior_r72 import write_groups
from room_secondary_wall_r75 import cushion
from locker_system_v3 import read_config, system_manifest, slot_frames, visual_profile
import room_appearance as appearance

OLD = 'data/sceneassets/server16_dressing_room_v3/shared/'
PREFIX = 'data/sceneassets/server16_dressing_room_v3/'
CONFIG = 'ModCarrerMode/data/club_environment/room/locker-system-v3.json'
ACTIVE = 'ModCarrerMode/data/club_environment/room/active-version.txt'
CAPACITY = 38
REVISION = 20
FLOOR_TILE_CM = 60.
TOE_KICK_BOTTOM, TOE_KICK_TOP, TOE_KICK_RECESS = 1000.5, 1002.5, .4
CEILING_Y = 1338.
DEPTH = 84.
MAIN_END = 1543.6
BOARD_DROP = 22.
FEATURE_CREST_Y = 1302.
FASCIA_BOTTOM, FASCIA_TOP = 1287., 1332.
MODELS = {'room_roles_r77.rx3': 'room_roles.rx3',
          'scenery_r77.rx3': 'scenery.rx3',
          'crest_surfaces_r77.rx3': 'crest_surfaces.rx3',
          'interior_r78.rx3': 'interior.rx3'}


def enabled(game):
    try:
        return (Path(game) / ACTIVE).read_text().strip() == '3'
    except OSError:
        return False


def stamp(game, club=0):
    return tuple((p.stat().st_mtime_ns, p.stat().st_size) if p.is_file() else None
                 for p in (Path(game) / ACTIVE, Path(game) / CONFIG,
                           Path(game) / 'data/sceneassets/server16_dressing_room_v3/pes_office/office.json',
                           Path(game) / 'data/sceneassets/server16_dressing_room_v3/rehab_equipment/equipment.json',
                           *(setting_path(game, club, key) for key in ('finish', 'floor', 'backs'))))+appearance.stamp(game,club)


def setting_path(game, club, key):
    return Path(game) / 'ModCarrerMode/data/club_environment/room/v3-settings' / f'{int(club)}_{key}.txt'


def setting(game, club, key, default):
    try:
        value = setting_path(game, club, key).read_text().strip()
        return value if value in ('light', 'dark', 'plain', 'message') else default
    except OSError:
        return default


@lru_cache(maxsize=8)
def _config(path, modified):
    return read_config(path)


def config(game):
    path = Path(game) / CONFIG
    return _config(str(path), path.stat().st_mtime_ns)


def frame(index, game):
    origin, yaw = slot_frames(index + 1, config(game)['layout'])[index]
    return np.array(origin, dtype=float), yaw


def rotation(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def camera_layout(layout):
    result=copy.deepcopy(layout)
    from room_fitted_shell import SIDE_SHIFT,BACK_SHIFT
    result['room']['camera_bounds']['half_width']+=100-SIDE_SHIFT
    result['room']['camera_bounds']['back']+=BACK_SHIFT
    for pose in result['medical'].get('navigation',[])+[s['pose'] for s in result['medical'].get('scenes',[])]:
        for i in (0,3):
            if pose[i+2]<=1543.6:
                if pose[i]>=690:pose[i]+=100
                elif pose[i]<=-690:pose[i]-=100
    # Narrow, straight approach anchors let the camera's near plane fit the
    # real door openings. The old angled/wide medical approach was unreachable
    # even though a first-person body could already walk through the doorway.
    from room_annex_doors import DOORS
    navigation=result['medical'].setdefault('navigation',[])
    for _,x in DOORS:
        for z in (1440.,1725.):
            pose=[x,180.,z,x,180.,z+400.,52.]
            if pose not in navigation:navigation.append(pose)
    # Pass the coach's desk along its open right-hand aisle, rather than
    # interpolating through the desk on the way to the far wall displays.
    for z in (2070.,2400.):
        pose=[440.,180.,z,440.,180.,z+400.,60.]
        if pose not in navigation:navigation.append(pose)
    return result


def obstacles(items):
    result=[]
    for source in items:
        if source['name'].startswith(('Arm','Parede secundária')):continue
        parts=[copy.deepcopy(source)]
        if source['lo'][2]<1543.6<source['hi'][2]:
            parts=[copy.deepcopy(source),copy.deepcopy(source)]
            parts[0]['hi'][2]=1543.6;parts[1]['lo'][2]=1543.6
        for item in parts:
            if item['hi'][2]<=1543.6:
                for key in ('lo','hi'):
                    if item[key][0]>=690:item[key][0]+=100
                    elif item[key][0]<=-690:item[key][0]-=100
            result.append(item)
    for index,(lo,hi) in enumerate([((-675,0,-594),(-135,287,-508)),((135,0,-594),(675,287,-508)),
                                    ((-834,0,-435),(-748,287,735)),((748,0,-435),(834,287,735)),
                                    ((675,0,-594),(834,287,-435)),((-834,0,-594),(-675,287,-435))]):
        result.append({'name':'Current Dressing Room / fitted cabinets '+str(index),'lo':list(lo),'hi':list(hi)})
    # The table is rendered at x ±160, z 77..213, height 86.5 cm. Camera
    # collision uses room-local coordinates; do not add the render origin.
    result.append({'name':'Current Dressing Room / central table','lo':[-160,3,77],'hi':[160,86.5,213]})
    from room_annex_doors import obstacles as door_obstacles
    from room_fitted_shell import obstacles as fitted_obstacles
    return fitted_obstacles(door_obstacles(result))


def locker_vertices(points):
    """Furniture-only envelopes; the wall behind each bay lies outside them."""
    mask = np.zeros(points.shape[:-1], dtype=bool)
    for index in range(36):
        if index < 12:
            origin = [-630 + index * 90 if index < 6 else 180 + (index - 6) * 90, 1000, -592]
            yaw = 0
        else:
            q = index - 12
            left = q % 2 == 0
            origin = [-732 if left else 732, 1000, -410 + (q // 2) * 102]
            yaw = math.pi / 2 if left else -math.pi / 2
        local = (points - origin) @ rotation(yaw)
        mask |= ((local >= [-44.5, .05, -2.5]) & (local <= [44.5, 287, 99])).all(axis=-1)
    return mask


def empty_mesh():
    # Valid inert native mesh, following the existing room's empty-slot format.
    return box((0, 900, 0), (0, 900, 0))


def trim_lockers(source, target, remove_floor_crest=False):
    rx = Rx3(source.read_bytes())
    removed = []
    for slot in range(len(rx.get(VERTEX))):
        vertices, indices = read_mesh(rx, slot)
        triangles = indices.reshape(-1, 3)
        drop = locker_vertices(vertices['p'][triangles]).all(axis=1)
        if remove_floor_crest:
            points = vertices['p'][triangles]
            drop |= ((points[:, :, 1] < 1002) & (points[:, :, 2] < 940)).all(axis=1)
        kept = triangles[~drop]
        removed.append(int(drop.sum()))
        if len(kept):
            used, inverse = np.unique(kept, return_inverse=True)
            v, ids = vertices[used], inverse.reshape(-1).astype('<u2')
        else:
            v, ids = empty_mesh()
        replace_mesh(rx, slot, v, ids)
    target.write_bytes(rx.build())
    return removed


def bay_groups():
    """One complete cabinet, in the same local frame as the native hanging kit."""
    groups = {key: [] for key in ('wood', 'niche', 'accent', 'cushion', 'linen', 'safe', 'safe_metal', 'linen_seam')}
    add = lambda key, lo, hi: groups[key].append(box(lo, hi))
    add('wood', (-45, 3, -2), (45, 9, 98))
    add('wood', (-45, 9, -2), (45, 286, 1))
    for x in (-45, 41.8):
        add('wood', (x, 9, 0), (x + 3.2, 287, 98))
    add('wood', (-45, 235, -2), (45, 237, 98))
    add('wood', (-45, 259, -2), (45, 261, 98))
    add('wood', (-45, 285, -2), (45, 287, 98))
    add('wood', (-45, 263, 95), (45, 283, 98))
    groups['niche'].append(panel([0, 140.5, 2.5], 81.2, 189, (0, 0, 1)))
    add('wood', (-45, 45, -2), (45, 48, 98))
    groups['cushion'].append(cushion((-41, 48, 4), (41, 55, 95)))
    for x in (-45., 41.8):
        add('accent', (x, 9., 98.8), (x + 3.2, 287., 99.4))
    # No metal runners intersect the boot shelf. Their former top faces were
    # coplanar with the base and produced two flashing, bright stripes.
    # No pale plate under this shelf: it protruded above the shirt backing.
    # FIFA's scene lights remain independent of this decorative mesh.
    for parts in groups.values():
        for vertices,_ in parts:vertices['p'][:,2]*=DEPTH/98.
    from room_linen import folded_towel
    groups['linen'],groups['linen_seam']=folded_towel()
    # Dimensions below are final room-space cm, matching the approved render.
    # One 81.2 cm row: open left half and a fitted drawer in the right half.
    add('wood', (-.8, 237, 1.8), (.8, 259, 83.5))
    add('safe', (1.4, 237.7, 81.3), (40.6, 258.3, 84.2))
    add('safe_metal', (34.8, 244.4, 84.25), (38.5, 251.2, 84.4))
    for key in ('wood','accent'):
        for vertices,_ in groups[key]:project_wood(vertices)
    return groups


def crest_groups():
    """Keep existing material slots stable; custom drawer art uses its own UVs."""
    return {'bay': [panel([20.6, 248, DEPTH+.55], 14, 14, (0, 0, 1))],
            'ceiling': [ceiling_crest()], 'floor': [floor_crest()],
            'feature_wall': [panel([0, FEATURE_CREST_Y, -588.6], 58, 58, (0, 0, 1))],
            'corner': [panel([sign*710.8, 1238, -470.8], 44, 44,
                             (-sign/math.sqrt(2), 0, 1/math.sqrt(2))) for sign in (-1, 1)],
            'bay_custom': [panel([20.6, 248, DEPTH+.55], 38, 19, (0, 0, 1))]}


def project_wood(vertices):
    p=vertices['p'];bits=vertices['n'].astype(np.int64)
    n=np.stack([((bits>>shift)&1023) for shift in (0,10,20)],axis=1)
    n=np.where(n>=512,n-1024,n);axis=np.abs(n).argmax(axis=1)
    uv=vertices['uv'];uv[:,0]=(p[:,0]+45)/90;uv[:,1]=1-p[:,1]/287
    uv[axis==0,0]=p[axis==0,2]/DEPTH
    uv[axis==1,1]=p[axis==1,2]/DEPTH
    return vertices


def fascia_specs():
    # Flush with the cabinet front; a small physical gap prevents z fighting.
    return [('back_left', [-405, 1309.5, -507.5], 540., (0, 0, 1)),
            ('back_right', [405, 1309.5, -507.5], 540., (0, 0, 1)),
            ('left', [-747.5, 1309.5, 150], 1170., (1, 0, 0)),
            ('right', [747.5, 1309.5, 150], 1170., (-1, 0, 0))]


def band_groups():
    return {key:[panel(center,width,FASCIA_TOP-FASCIA_BOTTOM,normal)] for key,center,width,normal,_ in band_specs()}


def band_specs():
    result=[]
    for index,(key,center,width,normal) in enumerate(fascia_specs()):
        if width<700:result.append((key,center,width,normal,index));continue
        # Two 4K panels keep side lettering at the same texel density as the
        # rear bank and avoid an oversized 8K resource on older GPUs.
        right=np.cross([0,1,0],normal)
        for half,offset in enumerate((-width/4,width/4)):
            result.append((key+'_'+str(half),(np.array(center)+right*offset).tolist(),width/2,normal,index))
    return result


def joinery_groups():
    groups = {'body': [], 'edge': [], 'cabinet': []}
    for key, center, width, normal in fascia_specs():
        front = np.array(center)
        n = np.array(normal)
        right = np.cross([0, 1, 0], n)
        def cuboid(x0, x1, y0, y1, depth0, depth1):
            points = [front + right*x + n*d for x in (x0,x1) for d in (depth0,depth1)]
            lo, hi = np.min(points,axis=0), np.max(points,axis=0)
            lo[1], hi[1] = y0, y1
            return box(lo,hi)
        # Shared cornice, plus a recessed toe kick below the individual bases.
        groups['body'].append(cuboid(-width/2,width/2,FASCIA_BOTTOM,FASCIA_TOP,-DEPTH,-1.2))
        groups['edge'].append(cuboid(-width/2,width/2,FASCIA_TOP,FASCIA_TOP+2.5,-DEPTH-1,-.8))
        groups['body'].append(cuboid(-width/2,width/2,FASCIA_TOP+2.5,CEILING_Y,-DEPTH,-1.2))
        groups['edge'].append(cuboid(-width/2,width/2,FASCIA_BOTTOM-1.8,FASCIA_BOTTOM,-DEPTH-1,-.8))
        # Bases start at y=1003. The old y=1001..1008 beam intersected them:
        # its pale end caps shared the dark base planes and flickered white.
        groups['body'].append(cuboid(-width/2+TOE_KICK_RECESS,width/2-TOE_KICK_RECESS,
                                      TOE_KICK_BOTTOM,TOE_KICK_TOP,
                                      -DEPTH+TOE_KICK_RECESS,-1.2-TOE_KICK_RECESS))
        # The former pale decorative strip above each name plate made a white
        # seam across every dark bay. It was not a physical FIFA light.
    # Equal 45-degree corner infills connect the rear bank to each side run.
    for sign in (-1,1):
        points=[(sign*x,z) for x,z in [(675,-592),(832,-592),(832,-435),(748,-435),(675,-508)]]
        groups['cabinet'].append(prism(points,1003,1287))
        groups['body'].append(prism(points,FASCIA_BOTTOM,CEILING_Y))
    # These are internal contact faces: cabinet caps meet the cornice at
    # y=1287 and its top meets the ceiling. Drawing the opposing coloured
    # caps on those same planes caused the green/white flashing at the board.
    for key, levels in [('body',(FASCIA_BOTTOM,FASCIA_TOP,FASCIA_TOP+2.5,CEILING_Y)),
                        ('edge',(FASCIA_BOTTOM,))]:
        clipped=[]
        for vertices,indices in groups[key]:
            tri=indices.reshape(-1,3);ys=vertices['p'][tri][:,:,1]
            hidden=np.zeros(len(tri),dtype=bool)
            for y in levels:hidden|=(np.abs(ys-y)<.005).all(1)
            clipped.append((vertices,tri[~hidden].reshape(-1).astype('<u2')))
        groups[key]=clipped
    return groups


def prism(points,bottom,top):
    rows=[];ids=[]
    center=np.mean(points,axis=0)
    for a,b in zip(points,points[1:]+points[:1]):
        p=np.array([[a[0],bottom,a[1]],[b[0],bottom,b[1]],[b[0],top,b[1]],[a[0],top,a[1]]],dtype=float)
        n=np.cross(p[1]-p[0],p[2]-p[0]);n/=np.linalg.norm(n)
        if np.dot(n,[(a[0]+b[0])/2-center[0],0,(a[1]+b[1])/2-center[1]])<0:n=-n
        start=len(rows)
        uvs=[(0,1),(1,1),(1,0),(0,0)]
        # A reflected corner reverses the vertex order, but its artwork must
        # still read left-to-right when viewed from inside the room.
        if np.dot(p[1]-p[0],np.cross((0,1,0),n))<0:uvs=[(1-u,v) for u,v in uvs]
        rows.extend((q,packed(n),packed((0,1,0)),uv) for q,uv in zip(p,uvs))
        ids.extend(start+i for i in (0,1,2,0,2,3))
    for y,flip in ((bottom,True),(top,False)):
        start=len(rows);normal=(0,-1 if flip else 1,0)
        rows.extend(((x,y,z),packed(normal),packed((1,0,0)),(x/90,z/90)) for x,z in points)
        for j in range(1,len(points)-1):ids.extend((start,start+j+1,start+j) if flip else (start,start+j,start+j+1))
    vertices=np.array(rows,dtype=VERT);indices=np.array(ids,dtype='<u2').reshape(-1,3)
    p=vertices['p'][indices];raw=vertices['n'][indices[:,0]].astype(np.int64)
    normals=np.stack([(raw>>shift)&1023 for shift in (0,10,20)],axis=1);normals=np.where(normals>=512,normals-1024,normals)/511
    reverse=(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])*normals).sum(axis=1)<0
    indices[reverse]=indices[reverse][:,[0,2,1]]
    return vertices,indices.reshape(-1)


def widen_main(path):
    rx=Rx3(path.read_bytes())
    for slot in range(len(rx.get(VERTEX))):
        v,ids=read_mesh(rx,slot)
        # A long right wall straddles the annex boundary. Moving only its near
        # vertices tilted the whole wall through the last lockers. Split it
        # into separate planar faces before applying the main-room expansion.
        v,ids=split_at_z(v,ids,MAIN_END)
        p=v['p'];main=p[:,2]<=MAIN_END+.001
        p[main&(p[:,0]>=690),0]+=100
        p[main&(p[:,0]<=-690),0]-=100
        replace_mesh(rx,slot,v,ids)
    path.write_bytes(rx.build())


def align_floor_uv(path):
    """Keep one straight 60 cm floor grid after every room expansion.

    Retaining the old UVs while widening/clipping the room shears the grid
    differently in adjacent triangles. Use the final world X/Z coordinates
    for every floor piece, including the medical and coach annexes. Only UV
    bytes change; positions, winding, normals and all other meshes survive.
    """
    path=Path(path);rx=Rx3(path.read_bytes());slot=2
    vertices,_=read_mesh(rx,slot);points=vertices['p'].astype(float)
    if not np.isfinite(points).all() or points[:,1].min()<999 or points[:,1].max()>1001:
        raise ValueError('Unexpected V3 floor geometry; no texture coordinates changed')
    section=[s for s in rx.sections if s[0]==VERTEX][slot]
    raw=bytearray(section[1]);view=np.frombuffer(raw,dtype=VERT,count=len(vertices),offset=16)
    view['uv']=points[:,[0,2]]/FLOOR_TILE_CM
    section[1]=bytes(raw);path.write_bytes(rx.build())


def split_at_z(vertices,indices,plane):
    result=list(vertices.copy());output=[]
    for tri in indices.reshape(-1,3):
        polygon=vertices[tri]
        z=polygon['p'][:,2]
        if not (z.min()<plane-.001 and z.max()>plane+.001):
            output.extend(int(i) for i in tri);continue
        pieces=[]
        if z.min()<plane-.001 and z.max()>plane+.001:
            pieces=[]
            for side in (-1,1):
                clipped=[]
                for a,b in zip(polygon,np.roll(polygon,-1)):
                    da=(float(a['p'][2])-plane)*side;db=(float(b['p'][2])-plane)*side
                    if da>=0:clipped.append(a.copy())
                    if (da>=0)!=(db>=0):
                        t=da/(da-db);q=a.copy()
                        q['p']=a['p']+(b['p']-a['p'])*t;q['p'][2]=plane
                        q['uv']=a['uv'].astype(float)+(b['uv'].astype(float)-a['uv'].astype(float))*t
                        clipped.append(q)
                # Independent seam vertices let the inner piece translate
                # without dragging the unchanged annex along the whole wall.
                piece=np.array(clipped,dtype=VERT)
                if side==1:piece['p'][:,2]=np.maximum(piece['p'][:,2],plane+.01)
                pieces.append(piece)
        for piece in pieces:
            for j in range(1,len(piece)-1):
                output.extend((len(result),len(result)+1,len(result)+2))
                result.extend((piece[0],piece[j],piece[j+1]))
    if not output:return empty_mesh()
    assert len(result)<65536,'Room clipping exceeded native index range'
    return np.array(result,dtype=VERT),np.array(output,dtype='<u2')


def raise_main_ceiling(path):
    rx = Rx3(path.read_bytes())
    for slot in (0,1,3,4,5):
        vertices, indices = read_mesh(rx,slot)
        p = vertices['p']
        if slot in (4,5):
            triangles = indices.reshape(-1,3)
            points = p[triangles]
            remove = ((points[:,:,1] > 1300) & (points[:,:,2] <= 1542.1)).all(axis=1)
            kept = triangles[~remove]
            if len(kept):
                used, inverse = np.unique(kept,return_inverse=True)
                vertices, indices = vertices[used],inverse.reshape(-1).astype('<u2')
            else:vertices, indices = empty_mesh()
        else:
            main = (p[:,2] <= MAIN_END+.001) & (np.abs(p[:,0]) <= 862.1) & (p[:,1] >= 1310)
            vertices['p'][main,1] += CEILING_Y-1320
        replace_mesh(rx,slot,vertices,indices)
    path.write_bytes(rx.build())


def ceiling_groups():
    from room_ceiling import geometry
    groups=geometry(CEILING_Y)
    # Perimeter moulding ends below the roof instead of sharing its plane.
    groups['paint'].append(box((-856,1320,1541.5),(856,CEILING_Y-.8,1543.5)))
    for lo,hi in [((-856,CEILING_Y-6,-600),(-844,CEILING_Y-.8,1542)),
                  ((844,CEILING_Y-6,-600),(856,CEILING_Y-.8,1542)),
                  ((-856,CEILING_Y-6,-600),(856,CEILING_Y-.8,-588)),
                  ((-856,CEILING_Y-6,1530),(856,CEILING_Y-.8,1542))]:
        groups['paint'].append(box(lo,hi))
    groups['wall']=plain_wall_panels()
    from room_fitted_shell import returns
    groups['wall'].extend(returns())
    return groups


def plain_wall_panels():
    """Cover the full two end walls; no club stripe or partial overlay seams."""
    from room_exit_door import CENTER_Z
    parts=[]
    def face(x,lo,hi,bottom,top,normal):
        parts.append(panel([x,(bottom+top)/2,(lo+hi)/2],hi-lo,top-bottom,normal))
    # The closed exit and its frame stay in front, with a matching opening.
    for lo,hi in ((735.,CENTER_Z-85.),(CENTER_Z+85.,MAIN_END)):
        face(-847.7,lo,hi,1000.,CEILING_Y,(1,0,0))
    face(-847.7,CENTER_Z-85.,CENTER_Z+85.,1242.,CEILING_Y,(1,0,0))
    face(847.7,735.,MAIN_END,1000.,CEILING_Y,(-1,0,0))
    return parts


def logo_mount_groups():
    shift=CEILING_Y-1360.
    return {'metal':[box((-126,1356+shift,-116),(126,1359+shift,136))],
            'paint':[box((-123,1355.6+shift,-113),(123,1356.1+shift,133))]}


def ceiling_crest():
    vertices = np.zeros(4, dtype=VERT)
    vertices['p'] = [(-120, CEILING_Y-.2, -110), (120, CEILING_Y-.2, -110),
                     (120, CEILING_Y-.2, 130), (-120, CEILING_Y-.2, 130)]
    vertices['n'] = packed((0, -1, 0))
    vertices['g'] = packed((1, 0, 0))
    vertices['uv'] = [(0, 1), (1, 1), (1, 0), (0, 0)]
    return vertices, np.array([0, 1, 2, 0, 2, 3], dtype='<u2')


def floor_crest():
    vertices=np.zeros(4,dtype=VERT)
    # 20% larger, retaining the same central floor anchor and clearance.
    vertices['p']=[(-192,1000.85,338),(-192,1000.85,722),(192,1000.85,722),(192,1000.85,338)]
    vertices['n']=packed((0,1,0));vertices['g']=packed((1,0,0));vertices['uv']=[(0,0),(0,1),(1,1),(1,0)]
    return vertices,np.array([0,1,2,0,2,3],dtype='<u2')


def annex_surfaces(vertices, indices):
    """Remove the replaced main-room wall, retaining both enclosed annexes.

    R76/R77 also put the coach/medical solid walls in secondary_wall_*.
    Dropping the entire material slot removed their inner and outer faces.
    The main room ends before z=1544; the annex shells start at z=1545.
    """
    tri=indices.reshape(-1,3)
    keep=(vertices['p'][tri][:,:,2]>=1544.).all(axis=1)
    if not keep.any():return empty_mesh()
    used,inverse=np.unique(tri[keep],return_inverse=True)
    return vertices[used].copy(),inverse.reshape(-1).astype('<u2')


def stage(game, output):
    game, output = Path(game), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    original = game / OLD
    report = {'version': 3, 'revision': REVISION, 'capacity': CAPACITY, 'sources': {}, 'removed_triangles': {}}
    for source, name in MODELS.items():
        path = original / source
        report['sources'][source] = hashlib.sha256(path.read_bytes()).hexdigest()
        if name=='interior.rx3':
            rx=Rx3(path.read_bytes());spec=json.loads(path.with_suffix('.json').read_text(encoding='utf8'))
            for slot,binding in enumerate(spec['bindings']):
                if binding['material'].startswith('secondary_wall_'):
                    replace_mesh(rx,slot,*annex_surfaces(*read_mesh(rx,slot)))
            (output/name).write_bytes(rx.build())
        else:report['removed_triangles'][source] = trim_lockers(path, output / name, 'crest' in source)
        widen_main(output/name)
    from room_fitted_shell import geometry as fit_shell,specification as shell_specification
    for name,kind in [('room_roles.rx3','roles'),('interior.rx3','interior')]:
        rx=Rx3((output/name).read_bytes());fit_shell(rx,kind)
        (output/name).write_bytes(rx.build())
    report['fitted_shell']=shell_specification()
    raise_main_ceiling(output/'room_roles.rx3')
    from room_ceiling import replace_main_ceiling, specification as ceiling_specification
    ceiling_rx=Rx3((output/'room_roles.rx3').read_bytes())
    report['ceiling_removed_triangles']=replace_main_ceiling(ceiling_rx,CEILING_Y,MAIN_END)
    (output/'room_roles.rx3').write_bytes(ceiling_rx.build())
    report['ceiling']=ceiling_specification(CEILING_Y)
    refine_front_wall(output/'room_roles.rx3',output/'crest_surfaces.rx3')
    lower_board(output/'room_roles.rx3');lower_board(output/'scenery.rx3')
    extend_board_frame_down(output/'room_roles.rx3')
    align_floor_uv(output/'room_roles.rx3')
    template = original / 'locker_support_r68.rx3'
    from room_exit_door import geometry as exit_geometry, replace_old_fixture, CENTER_Z, RIGHT_SHIFT_CM
    exit_interior=Rx3((output/'interior.rx3').read_bytes())
    removed_exit=replace_old_fixture(exit_interior)
    (output/'interior.rx3').write_bytes(exit_interior.build())
    report['exit_door_bindings']=write_groups(template,exit_geometry(),output/'exit_door.rx3')
    from room_annex_doors import strip_old_fixtures, specification as door_specification
    for name,kind in [('interior.rx3','interior'),('room_roles.rx3','roles')]:
        rx=Rx3((output/name).read_bytes());strip_old_fixtures(rx,kind)
        (output/name).write_bytes(rx.build())
    report['annex_doors']=door_specification()
    report['exit_door']={'revision':1,'center_native_cm':[-846,1118,CENTER_Z],
                         'right_shift_cm':RIGHT_SHIFT_CM,'leaf_finish':'door_finish','custom_asset':'exit-door.png',
                         'closed':True,'panic_bar_height_cm':105,'unrelated_triangles_preserved':True,
                         'removed_old_fixture_triangles':removed_exit}
    report['bay_bindings'] = write_groups(template, bay_groups(), output / 'locker_bay.rx3')
    report['band_bindings'] = write_groups(template, band_groups(), output / 'fascia.rx3')
    for binding, (_,_,width,_,index) in zip(report['band_bindings'],band_specs()):
        binding['width_cm']=width;binding['banner_index']=index
    report['joinery_bindings'] = write_groups(template, joinery_groups(), output/'joinery.rx3')
    report['ceiling_bindings'] = write_groups(template, ceiling_groups(), output/'ceiling_details.rx3')
    report['crest_bindings'] = write_groups(template, crest_groups(), output / 'crests.rx3')
    report['mount_bindings']=write_groups(template,logo_mount_groups(),output/'logo_mount.rx3')
    report['feature_bindings']=write_groups(template,{'wall':[panel([0,(1000+CEILING_Y)/2,-589],268,CEILING_Y-1000,(0,0,1))]},output/'feature_wall.rx3')
    report['furniture_bindings']=extract_table_wood(game,output/'scenery.rx3',template,output/'furniture_wood.rx3')
    from room_next_match_board import stage as board_stage
    report['next_match_board']=board_stage(game,output)
    report['scenery_bindings']=[{'submesh':'room_part_1','atlas':0,'alpha':False},
                               {'submesh':'room_part_2','atlas':0,'alpha':True},
                               {'submesh':'room_part_3','atlas':1,'alpha':False}]
    report['empty_submeshes'] = {}
    for name in MODELS.values():
        rx = Rx3((output / name).read_bytes())
        empty = []
        for slot in range(len(rx.get(VERTEX))):
            v, ids = read_mesh(rx, slot)
            t = v['p'][ids.reshape(-1, 3)]
            if not np.any(np.linalg.norm(np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0]), axis=1) > .001):
                empty.append(f'room_part_{slot+1}')
        report['empty_submeshes'][name] = empty
    report['preserved'] = ['next_match_board', 'coach_room', 'medical_department', 'all_doorways', 'exit_paths', 'collision_layout']
    # Content-addressed paths force fresh native resources on a room re-entry.
    report['model_files']={}
    for name in list(MODELS.values())+['locker_bay.rx3','fascia.rx3','crests.rx3','joinery.rx3','ceiling_details.rx3','logo_mount.rx3','feature_wall.rx3','furniture_wood.rx3','exit_door.rx3']:
        data=(output/name).read_bytes();hashed=Path(name).stem+'_'+hashlib.sha256(data).hexdigest()[:14]+'.rx3'
        (output/hashed).write_bytes(data);report['model_files'][name]=hashed
    from room_loading_r81 import stage as loading_stage
    report['loading']=loading_stage(game,output)
    for path in output.glob('loading_*_r8[123].rx3'):report['model_files'][path.name]=path.name
    (output / 'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    return report


def refine_front_wall(roles,crests):
    for path,slot in ((roles,1),(crests,0)):
        rx=Rx3(path.read_bytes());v,ids=read_mesh(rx,slot);tri=ids.reshape(-1,3);p=v['p'][tri]
        drop=((abs(p[:,:,0])<134)&(p[:,:,2]<-580)&(p[:,:,1]>=1000)).all(1)
        kept=tri[~drop]
        replace_mesh(rx,slot,v,kept.reshape(-1).astype('<u2'))
        path.write_bytes(rx.build())


def lower_board(path):
    rx=Rx3(path.read_bytes())
    for slot in range(len(rx.get(VERTEX))):
        v,ids=read_mesh(rx,slot);p=v['p']
        board=(abs(p[:,0])<=125.6)&(p[:,2]>=-561)&(p[:,2]<=-479)&(p[:,1]>=1114)
        v['p'][board,1]-=BOARD_DROP
        replace_mesh(rx,slot,v,ids)
    path.write_bytes(rx.build())


def extend_board_frame_down(path):
    """Lower only the physical bottom rail; keep the generated board image fixed."""
    rx=Rx3(path.read_bytes())
    slot=19  # room_part_20 is the screen frame and stand
    vertices,indices=read_mesh(rx,slot);p=vertices['p']
    rail=((np.abs(p[:,0])<=123.6)&(p[:,1]>=1107.5)&(p[:,1]<=1111.4)&
          (p[:,2]>=-518.3)&(p[:,2]<=-513.7))
    if int(rail.sum())<40:
        raise ValueError('Next-match physical lower frame rail was not found; board left unchanged')
    p[rail,1]-=14.0
    replace_mesh(rx,slot,vertices,indices)
    path.write_bytes(rx.build())


def extract_table_wood(game,source,template,target):
    from room_texture_tools import color_image
    rx=Rx3(source.read_bytes());parts=[]
    for slot in range(len(rx.get(VERTEX))):
        v,ids=read_mesh(rx,slot);tri=ids.reshape(-1,3);p=v['p'][tri]
        page=1 if slot==2 else 0
        atlas=np.array(color_image((Path(game)/OLD/f'scenery_textures_{page}_r72.rx3').read_bytes(),'room_cm'))
        uv=v['uv'][tri].mean(1).astype(float)
        rgb=atlas[np.clip((uv[:,1]*atlas.shape[0]).astype(int),0,atlas.shape[0]-1),np.clip((uv[:,0]*atlas.shape[1]).astype(int),0,atlas.shape[1]-1),:3].astype(float)
        wood=(rgb[:,0]>rgb[:,1]*1.08)&(rgb[:,1]>rgb[:,2]*1.06)&(rgb[:,0]>70)
        main=((abs(p[:,:,0])<240)&(p[:,:,2]>15)&(p[:,:,2]<240)&(p[:,:,1]<1100)).all(1)
        selected=wood&main
        if selected.any():
            vv=v[tri[selected].reshape(-1)].copy();ii=np.arange(len(vv),dtype='<u2')
            raw=vv['n'].astype(np.int64);n=np.stack([(raw>>s)&1023 for s in (0,10,20)],axis=1);n=np.where(n>=512,n-1024,n)
            axis=np.abs(n).argmax(1);q=vv['p'];vv['uv'][:,0]=(q[:,0]+240)/480;vv['uv'][:,1]=(q[:,2]-15)/225
            vv['uv'][axis!=1,1]=(q[axis!=1,1]-1000)/100
            vv['uv'][axis==0,0]=(q[axis==0,2]-15)/225
            parts.append((vv,ii))
            replace_mesh(rx,slot,v,tri[~selected].reshape(-1).astype('<u2'))
    assert parts,'Central-table wood not found; refuse to modify unrelated furniture'
    source.write_bytes(rx.build())
    from room_table import split as split_table
    return write_groups(template,split_table(parts),target)


def model_path(model, game):
    if enabled(game) and model.startswith(OLD):
        name = MODELS.get(model[len(OLD):])
        if name:
            name=build_manifest(str(game)).get('model_files',{}).get(name,name)
            target = PREFIX + name
            if not (Path(game) / target).is_file():
                raise FileNotFoundError('Vestiário V3: ' + target)
            return target
    return model


@lru_cache(maxsize=4)
def build_manifest(game):
    return json.loads((Path(game) / PREFIX / 'manifest.json').read_text(encoding='utf8'))


def empty_component(model, submesh, game):
    if not model.startswith(PREFIX):return False
    manifest=build_manifest(str(game));name=model[len(PREFIX):]
    logical=next((k for k,v in manifest.get('model_files',{}).items() if v==name),name)
    return submesh in manifest['empty_submeshes'].get(logical, [])


def texture(game, image, name,*,mipmaps=True):
    from room_native_hanging_20261022 import texture_package
    policy=b'' if mipmaps else b'full-resolution-sign-v1'
    digest = hashlib.sha256(policy+str(image.size).encode()+image.tobytes()).hexdigest()[:14]
    relative = PREFIX + name + '_' + digest + '.rx3'
    path = Path(game) / relative
    if not path.exists():
        texture_package(image, path, 'v3_cm',mipmaps=mipmaps)
    return relative


@lru_cache(maxsize=8)
def scenery_texture(game,page,source_stamp,wood_stamp):
    from room_texture_tools import color_image
    game=Path(game)
    im=color_image((game/OLD/f'scenery_textures_{page}_r72.rx3').read_bytes(),'room_cm')
    pixels=np.array(im);rgb=pixels[:,:,:3].astype(float)
    mask=(rgb[:,:,0]>rgb[:,:,1]*1.08)&(rgb[:,:,1]>rgb[:,:,2]*1.06)&(rgb[:,:,0]>70)
    wood=editable_image(game/appearance.ROOT/'generic/materials/walnut.png').resize(im.size,Image.Resampling.BICUBIC)
    grain=np.array(wood);pixels[mask,:3]=grain[mask,:3]
    return texture(game,Image.fromarray(pixels),'scenery_atlas_'+str(page))


def floor_texture(context, game):
    choice=appearance.preferences(game,context['club']).get('floor','light')
    custom=appearance.asset(game,context['club'],'floor') if choice=='custom' else None
    if custom:return texture(game,editable_image(custom),'custom')
    material=Path(game)/appearance.ROOT/'generic/materials'/('walnut.png' if choice=='wood' else 'floor_'+choice+'.png')
    if material.is_file():return texture(game,editable_image(material),'floor')
    dark = choice=='dark'
    rgb = (78, 81, 84) if dark else (177, 178, 176)
    image = Image.new('RGBA', (1024, 1024), rgb + (255,))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1023, 1023), outline=tuple(max(0, v-24) for v in rgb), width=5)
    draw.line((5, 6, 1018, 6), fill=tuple(v+6 for v in rgb), width=2)
    return texture(game, image, 'floor')


def editable_image(path):
    path=Path(path);s=path.stat()
    return _editable_image(str(path),s.st_mtime_ns,s.st_size)


@lru_cache(maxsize=24)
def _editable_image(path,modified,size):
    with Image.open(path) as source:
        if source.width*source.height>16_777_216:raise ValueError('Editable room texture exceeds 16 megapixels')
        image=source.convert('RGBA')
        # Keep wide/tall artwork sharp within the same 4 MP surface budget;
        # a 4096 x 1024 image need not lose three quarters of its pixels just
        # because its longest side exceeds 2048.
        scale=min(1.,4096/image.width,4096/image.height,math.sqrt(4_194_304/(image.width*image.height)))
        if scale<1:image=image.resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))),Image.Resampling.LANCZOS)
        return image


def finish_image(game,club,choice,custom_key):
    if choice=='custom':
        path=appearance.asset(game,club,custom_key)
        if path:return editable_image(path)
    if choice in ('wood','wood_light','dark','ash','slate'):
        filename={'wood':'walnut.png','wood_light':'oak_light.png','dark':'ash_black.png','ash':'ash_natural.png','slate':'slate_charcoal.png'}[choice]
        path=Path(game)/appearance.ROOT/'generic/materials'/filename
        if path.is_file():return editable_image(path)
    rgb={'light':(238,239,236),'dark':(29,31,33),'gray':(119,123,126)}.get(choice,(29,31,33))
    noise=np.random.default_rng(304).integers(-1,2,(256,256,1))
    pixels=np.empty((256,256,4),dtype='uint8');pixels[:,:,:3]=np.clip(np.array(rgb)[None,None,:]+noise,0,255);pixels[:,:,3]=255
    return Image.fromarray(pixels)


@lru_cache(maxsize=4)
def ceiling_texture(game):
    size=2048
    noise=np.random.default_rng(302).integers(-1,2,(size,size,1))
    pixels=np.empty((size,size,4),dtype='uint8')
    pixels[:,:,:3]=np.clip(np.array([233,234,230])[None,None,:]+noise,0,255)
    pixels[:,:,3]=255
    image=Image.fromarray(pixels);draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,size-1,size-1),outline=(143,150,151),width=5)
    draw.line((6,7,size-7,7),fill=(249,249,247),width=3)
    return texture(game,image,'acoustic_ceiling')


def color(value):
    return tuple(int(value[i:i+2], 16) for i in (1, 3, 5))


@lru_cache(maxsize=256)
def font(size):
    for name in ('ariblk.ttf', 'arialbd.ttf', 'segoeuib.ttf', 'arial.ttf'):
        try:
            return ImageFont.truetype(str(Path(__import__('os').environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / name), size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


@lru_cache(maxsize=8)
def banner(text, base, accent, width=4096, club_id=0, physical_width=540.):
    height=1024
    image = Image.new('RGBA', (width, height), base + (255,))
    draw = ImageDraw.Draw(image)
    # A fitted, cabinet-height fascia: white relief letters with club accents.
    draw.line((0,3,width,3),fill=tuple(min(255,c+12) for c in base),width=3)
    draw.line((0,height-4,width,height-4),fill=(5,6,7),width=4)
    ratio=(width/physical_width)/(height/(FASCIA_TOP-FASCIA_BOTTOM))
    size = 840
    while size > 24 and draw.textlength(text, font=font(size))*ratio > width - 120:
        size -= 2
    face=font(size);natural=math.ceil(draw.textlength(text,font=face))+16
    lettering=Image.new('RGBA',(natural,height),(0,0,0,0));letters=ImageDraw.Draw(lettering);x=8
    runs=re.split(r'(FLAMENGO|MENGÃO| DO )',text) if club_id==1043 else [text]
    light=(245,245,242) if sum(base)<540 else (24,26,29)
    for run in runs:
        if not run:continue
        ink=accent if club_id==1043 and run in ('FLAMENGO','MENGÃO',' DO ') else light
        letters.text((x+3,524),run,font=face,fill=(0,0,0),anchor='lm',stroke_width=3)
        letters.text((x,512),run,font=face,fill=ink,anchor='lm')
        x+=letters.textlength(run,font=face)
    lettering=lettering.resize((max(1,round(natural*ratio)),height),Image.Resampling.LANCZOS)
    image.alpha_composite(lettering,((width-lettering.width)//2,0))
    return image


def prepare(context, game, add, identity):
    """Add repeated native components; native kit/crest textures stay in FIFA."""
    game = Path(game)
    spec = config(game)
    profile = system_manifest(CAPACITY, context, spec)
    style = profile['club_style']
    prefs=appearance.preferences(game,context['club'],style['finish'])
    custom=appearance.custom_profile(game,context['club']) if prefs['style']=='custom' else {}
    theme=custom.get('theme',{})
    if prefs['style']=='default':
        style=visual_profile(context['club'],context.get('club_name','Clube'),context['colors'][0],context['colors'][1],{'fallback':spec.get('visual',{}).get('fallback',{})})
    if isinstance(theme,dict):
        for key,value in theme.items():
            if key=='banner' and isinstance(value,dict):
                style['banner']=copy.deepcopy(value)
                style['banner'].setdefault('base',style['primary']);style['banner'].setdefault('accent',style['secondary'])
                style['banner'].setdefault('lines',[context.get('club_name','Clube').upper()])
    context['room_settings']=appearance.ui_data(game,context['club'],style['finish'])
    profile['club_style'] = style
    profile['appearance']=prefs
    profile['finish_options']=[item['value'] for row in context['room_settings'] if row['key']=='finish' for item in row['options']]
    build = build_manifest(str(game))
    asset=lambda name:PREFIX+build.get('model_files',{}).get(name,name)
    materials = {'wood': style['panel'], 'niche': style['niche'], 'accent': style['primary'],
                 'cushion': style['cushion'], 'metal': '#9BA1A7', 'linen': '#ECEDE9', 'light': '#F1F5F5',
                 'safe': '#272B2F', 'safe_metal': '#121517', 'linen_seam': '#D8D6CD'}

    poses = []
    for origin, yaw in slot_frames(CAPACITY, spec['layout']):
        matrix = np.eye(4)
        matrix[:3, :3] = rotation(yaw)
        matrix[:3, 3] = np.array(origin) + [100000, 1000, 0]
        poses.append(matrix.T.reshape(-1).tolist())
    for binding in build['bay_bindings']:
        key = binding['material']
        rgb = color(materials[key])
        if key == 'wood':
            image=finish_image(game,context['club'],prefs['finish'],'cabinet')
        elif key=='niche':image=finish_image(game,context['club'],prefs['backs'],'backing')
        elif key=='accent':image=trim_image(game,context,prefs['trim'])
        elif key=='linen':image=__import__('room_linen').fabric_image()
        elif key=='linen_seam':image=__import__('room_linen').seam_image()
        else:
            image = Image.new('RGBA', (8, 8), rgb + (255,))
        tex = texture(game, image, 'custom' if key in ('wood','niche') and prefs['finish' if key=='wood' else 'backs']=='custom' else key)
        for matrix in poses:
            add('v3_bay_' + key, asset('locker_bay.rx3'), tex, 'v3_cm', matrix, submesh=binding['submesh'])
    import room_image_panels
    banks=fascia_specs();height=FASCIA_TOP-FASCIA_BOTTOM
    image_model,image_bindings=room_image_panels.build(game,banks,height,game/OLD/'locker_support_r68.rx3',PREFIX)
    for index,(bank,binding) in enumerate(zip(banks,image_bindings)):
        key,center,physical_width,normal=bank
        from room_fascia import render as render_fascia
        count,_=room_image_panels.layout(physical_width,height)
        choice=prefs.get('fascia','custom' if custom else 'name')
        if choice=='custom':fascia_image=render_fascia(game,context['club'],style['banner'],index,count*1024,physical_width,banner)
        elif choice=='name':
            spec={'base':style['primary'],'accent':style['secondary'],'lines':[context.get('club_name','Clube').upper()]}
            fascia_image=render_fascia(game,context['club'],spec,index,count*1024,physical_width,banner)
        elif choice in ('primary','secondary','light','gray'):
            fill=style[choice] if choice in ('primary','secondary') else '#EEEEEB' if choice=='light' else '#777C80'
            fascia_image=Image.new('RGBA',(1024,256),color(fill)+(255,))
        else:fascia_image=finish_image(game,context['club'],'dark' if choice=='dark' else 'wood','cabinet')
        tiled=room_image_panels.atlas(fascia_image,physical_width,height)
        tex=texture(game,tiled,'image_fascia')
        add('v3_image_band_'+key,image_model,tex,'v3_cm',identity,submesh=binding['submesh'])
    for group,bindings,colors in [('joinery',build['joinery_bindings'],{'body':style['banner']['base'],'edge':'#151719','light':'#EDF1EC','cabinet':'#282A2C'}),
                                  ('ceiling_details',build['ceiling_bindings'],{'paint':'#E8E9E6','metal':'#AEB5B8','diffuser':'#F4F7F6','vent':'#292D31','sprinkler_glass':'#AF2937','wall':'#F3F4F0'})]:
        for binding in bindings:
            key=binding['material']
            if key=='cabinet':
                corner=appearance.asset(game,context['club'],'corner') if prefs['style']=='custom' else None
                im=editable_image(corner) if corner else finish_image(game,context['club'],'dark' if prefs['finish']=='custom' else prefs['finish'],'cabinet')
            else:im=Image.new('RGBA',(8,8),color(colors[key])+(255,))
            tex=texture(game,im,group+'_'+key)
            add('v3_'+group+'_'+key,asset(group+'.rx3'),tex,'v3_cm',identity,submesh=binding['submesh'])
    crest = f'data/ui/imgassets/crest/light/l{context["club"]}.dds'
    front = drawer_front(game, context['club'], prefs)
    if front is not None:
        safe_texture, texname, material = front
        binding = next(item for item in build['crest_bindings'] if item['material']==material)
        for matrix in poses:
            add('v3_bay_safe_front', asset('crests.rx3'), safe_texture,
                texname, matrix, True, binding['submesh'])
    if prefs['logo']=='ceiling':
        add('v3_ceiling_crest', asset('crests.rx3'), crest, '', identity, True, build['crest_bindings'][1]['submesh'])
    else:add('v3_floor_crest',asset('crests.rx3'),crest,'',identity,True,build['crest_bindings'][2]['submesh'])
    wall=appearance.asset(game,context['club'],'feature_wall') if prefs['style']=='custom' else None
    wall_image=editable_image(wall) if wall else Image.new('RGBA',(8,8),color(style['primary'])+(255,))
    for binding in build.get('feature_bindings',[]):
        add('v3_feature_wall',asset('feature_wall.rx3'),texture(game,wall_image,'feature_wall'),'v3_cm',identity,submesh=binding['submesh'])
    add('v3_feature_crest',asset('crests.rx3'),crest,'',identity,True,build['crest_bindings'][3]['submesh'])
    add('v3_corner_crest',asset('crests.rx3'),crest,'',identity,True,build['crest_bindings'][4]['submesh'])
    from room_table import image as table_image
    for binding in build.get('furniture_bindings',[]):
        part=binding['material'];choice=prefs.get('table_'+part,'default')
        image=table_image(game,context,part,choice)
        material_key='wood_' if choice in ('default','walnut','oak') else ''
        add('v3_table_'+material_key+part,asset('furniture_wood.rx3'),texture(game,image,'table_finish'),'v3_cm',identity,submesh=binding['submesh'])
    for binding in build['scenery_bindings']:
        page=binding['atlas'];original=game/OLD/f'scenery_textures_{page}_r72.rx3'
        wood=game/appearance.ROOT/'generic/materials/walnut.png'
        tex=scenery_texture(str(game),page,original.stat().st_mtime_ns,wood.stat().st_mtime_ns)
        add('v3_static_'+binding['submesh'],asset('scenery.rx3'),tex,'v3_cm',identity,binding['alpha'],binding['submesh'])
    from room_next_match_board import prepare as prepare_match_board
    prepare_match_board(build,add,identity)
    from room_exit_door import prepare as prepare_exit_door
    prepare_exit_door(build,context,game,add,identity,prefs)
    context['room_version'] = 3
    context['locker_system_v3'] = profile
    return profile


def drawer_front(game, club, prefs):
    """A missing custom image stays blank, never silently restores the badge."""
    choice=prefs.get('drawer_art','crest')
    if choice=='none':return None
    if choice=='crest':return f'data/ui/imgassets/crest/light/l{club}.dds', '', 'bay'
    source=appearance.asset(game,club,'locker_box_front')
    if not source:return None
    image=Image.new('RGBA',(1024,512),(0,0,0,0))
    fitted=ImageOps.contain(editable_image(source),(1024,512),Image.Resampling.LANCZOS)
    image.alpha_composite(fitted,((image.width-fitted.width)//2,(image.height-fitted.height)//2))
    return texture(game,image,'locker_box_front'), 'v3_cm', 'bay_custom'


def trim_image(game,context,choice):
    if choice in ('primary','secondary'):
        rgb=tuple(round(v*255) for v in context['colors'][0 if choice=='primary' else 1])
        return Image.new('RGBA',(8,8),rgb+(255,))
    return finish_image(game,context['club'],choice,'cabinet')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = stage(args.game, args.output)
    print(json.dumps({'version': 3, 'capacity': result['capacity'], 'module_materials': len(result['bay_bindings'])}))
