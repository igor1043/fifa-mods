"""Two-color secondary wall and a further 240 cm of real room space.

Colors come from the selected club, with optional per-club hex overrides.
Panel boundaries are native geometry, not a stretched bitmap.
"""
from pathlib import Path
import copy, json, re
import numpy as np
from PIL import Image
from rx3 import Rx3, VERTEX
from room_visual_r68 import VERT, box, join, packed, read_mesh, replace_mesh
from room_interior_r71 import PREFIX, palette, panel

CUT = 815.
EXTRA = 240.
CONFIG = 'ModCarrerMode/data/club_environment/room/secondary-wall.json'
WALL = dict(x=748.4, start=755., end=1475., bottom=1000., top=1316.)
# These disjoint areas cover 30.10% of the wall; the primary field is 69.90%.
SECONDARY_AREAS = [(755., 1475., 1088., 1152.), (800., 1120., 1218., 1288.)]


def config_stamp(game):
    try:
        stat=(Path(game)/CONFIG).stat()
        return stat.st_size, stat.st_mtime_ns
    except OSError:return None


def selected_palette(context, game):
    values = palette(context['colors'])
    try:
        data = json.loads((Path(game)/CONFIG).read_text(encoding='utf8'))
        override = data.get('clubs', {}).get(str(context['club']), {})
        for i, key in enumerate(('primary', 'secondary')):
            value = override.get(key)
            if isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                values[i] = tuple(int(value[j:j+2], 16) for j in (1, 3, 5))
    except (OSError, ValueError, TypeError, AttributeError):
        pass  # A malformed optional override must not prevent the room loading.
    return values


def material_images(context, game):
    primary, secondary = selected_palette(context, game)
    # Zero diffuse reflectance erases every edge under FIFA's lighting. A matte
    # black surface still reflects a little light; keep that detail in dark kits.
    def albedo(color):return (18,18,18) if max(color)<=8 else color
    return {key: Image.new('RGBA', (8, 8), albedo(color)+(255,)) for key, color in
            [('secondary_wall_primary', primary), ('secondary_wall_secondary', secondary)]}


def extend(v):
    v = v.copy()
    v['p'][:, 2] += np.where(v['p'][:, 2] >= CUT, EXTRA, 0)
    return v


def cushion(lo, hi):
    """Small bevels along the seat edge, keeping the material flat and matte."""
    x0, y0, z0 = lo; x1, y1, z1 = hi
    r = 1.5
    outline = [(x0+r,z0),(x1-r,z0),(x1,z0+r),(x1,z1-r),
               (x1-r,z1),(x0+r,z1),(x0,z1-r),(x0,z0+r)]
    center = np.array([(x0+x1)/2,(z0+z1)/2])
    inset = [(center+(np.array(p)-center)*[1-2*r/(x1-x0),1-2*r/(z1-z0)]).tolist() for p in outline]
    rings = [np.array([[x,y,z] for x,z in outline]) for y in (y0,y1-r)]
    rings.append(np.array([[x,y1,z] for x,z in inset]));triangles=[]
    for a,b in zip(rings,rings[1:]):
        for i in range(8):
            j=(i+1)%8
            triangles.extend([[a[i],a[j],b[j]],[a[i],b[j],b[i]]])
    for ring, reverse in [(rings[0],True),(rings[-1],False)]:
        c=ring.mean(0)
        for i in range(8):
            j=(i+1)%8
            triangles.append([c,ring[j],ring[i]] if reverse else [c,ring[i],ring[j]])
    v=np.zeros(len(triangles)*3,dtype=VERT)
    for i,t in enumerate(triangles):
        a,b,c=np.array(t)[[0,2,1]];normal=np.cross(b-a,c-a);normal/=np.linalg.norm(normal)
        for k,p in enumerate((a,b,c)):v[3*i+k]=(p,packed(normal),packed([0,0,1]),(.5,.5))
    return v,np.arange(len(v),dtype='<u2')


def secondary_wall():
    groups={'secondary_wall_primary':[], 'secondary_wall_secondary':[]}
    def add(which, shape):groups['secondary_wall_'+which].append(shape)
    x=WALL['x'];z0=WALL['start'];z1=WALL['end'];y0=WALL['bottom'];y1=WALL['top']
    # Unadorned primary field plus two broad, rectilinear secondary panels.
    add('primary',panel([x,(y0+y1)/2,(z0+z1)/2],z1-z0,y1-y0,(-1,0,0)))
    for left,right,bottom,top in SECONDARY_AREAS:
        add('secondary',panel([x-.5,(bottom+top)/2,(left+right)/2],right-left,top-bottom,(-1,0,0)))
    # Five-metre bench: colored frame, six bevelled seats, open equipment bays.
    add('primary',box((698,1006,870),(746,1010,1370)))
    add('primary',box((742,1008,870),(746,1041,1370)))
    add('primary',box((696,1036,870),(746,1041,1370)))
    for i in range(7):
        z=870+i*500/6
        add('primary',box((698,1000,z),(746,1037,z+2)))
    for i in range(6):
        z=872+i*500/6
        add('secondary',cushion((694,1041,z),(747,1047,z+500/6-3.5)))
    # A closed locker at one end and an open shelf unit at the other.
    for z in (790,1385):
        add('primary',box((703,1000,z),(746,1008,z+60)))
        add('primary',box((741,1008,z),(746,1208,z+60)))
        for side in (z,z+57):add('primary',box((703,1008,side),(746,1212,side+3)))
        add('primary',box((702,1208,z),(746,1213,z+60)))
    for low,high in ((1009,1104),(1107,1207)):
        add('secondary',box((700,low,794),(703,high,846)))
        add('primary',box((697,low+35,838),(700,low+58,841)))
    for y in (1048,1088,1128,1168):add('secondary',box((701,y,1388),(742,y+3,1442)))
    # A few folded cloths and small equipment bags, using only the club palette.
    for y in (1052,1092):
        for layer in range(3):add('secondary',box((706,y+layer*3,1393),(735,y+layer*3+2.5,1431)))
    for z in (895,1145):
        add('secondary',box((708,1011,z),(738,1029,z+44)))
        for edge in (z+8,z+32):add('primary',box((707.5,1011,edge),(708.1,1029,edge+3)))
        for edge in (z+16,z+28):add('primary',box((718,1029,edge),(721,1033,edge+2)))
        add('primary',box((718,1032,z+16),(721,1034,z+30)))
    return groups


def stage(game, output):
    from room_interior_r72 import write_groups
    game,output=Path(game),Path(output);output.mkdir(parents=True,exist_ok=True);base=game/PREFIX
    spec=json.loads((base/'interior_r74.json').read_text(encoding='utf8'))
    rx=Rx3((base/'interior_r74.rx3').read_bytes());groups={}
    for i,binding in enumerate(spec['bindings']):
        v,idx=read_mesh(rx,i);groups[binding['material']]=[(extend(v),idx)]
    groups.update(secondary_wall())
    spec['bindings']=write_groups(base/'locker_support_r68.rx3',groups,output/'interior_r75.rx3')
    # Transform each independent scene asset together; keep all native slots.
    for name in ['room_roles','scenery','medical_room','crest_surfaces','floor_shadows','water_cooler']:
        rx=Rx3((base/(name+'_r72.rx3')).read_bytes())
        for slot in range(len(rx.get(VERTEX))):
            v,idx=read_mesh(rx,slot);v=extend(v)
            if name in ('room_roles','medical_room') and slot in (2,3):v['uv']=v['p'][:,[0,2]]/60
            if name=='room_roles' and slot in (4,5):
                r=30 if slot==4 else 28;low,high=(1318.4,1320) if slot==4 else (1318,1318.3)
                v,idx=join([(v,idx)]+[box((x-r,low,930-r),(x+r,high,930+r)) for x in (-450,30,450)])
            replace_mesh(rx,slot,v,idx)
        (output/(name+'_r75.rx3')).write_bytes(rx.build())
    layout=json.loads((base/'room_layout_r72.json').read_text(encoding='utf8'))
    def shifted(z):return z+(EXTRA if z>=CUT else 0)
    for data in (layout['room'],layout['medical']):
        for o in data['obstacles']:
            for key in ('lo','hi'):o[key][2]=shifted(o[key][2])
    layout['room']['camera_bounds']['front']=shifted(layout['room']['camera_bounds']['front'])
    layout['room']['hydration_origin'][2]=shifted(layout['room']['hydration_origin'][2])
    for key in ('lo','hi'):layout['medical']['room_bounds'][key][2]=shifted(layout['medical']['room_bounds'][key][2])
    for pose in layout['medical']['navigation']+[s['pose'] for s in layout['medical']['scenes']]:
        for index in (2,5):pose[index]=shifted(pose[index])
    for o in spec['obstacles']:
        for key in ('lo','hi'):o[key][2]=shifted(o[key][2])
    # Body colliders cover the whole furniture footprints, including the seats.
    spec['obstacles'] += [
        dict(name='Parede secundária / banco',lo=[694,0,870],hi=[747,47,1372]),
        dict(name='Parede secundária / armário',lo=[697,0,790],hi=[746,213,850]),
        dict(name='Parede secundária / prateleiras',lo=[701,0,1385],hi=[746,213,1445])]
    layout['revision']=spec['revision']=75
    layout['extension_cm']=spec['extension_cm']=600
    spec['cooler_model']='water_cooler_r75.rx3'
    spec['secondary_wall']=copy.deepcopy(WALL)
    spec['secondary_area_ratio']=sum((b-a)*(d-c) for a,b,c,d in SECONDARY_AREAS)/((WALL['end']-WALL['start'])*(WALL['top']-WALL['bottom']))
    (output/'room_layout_r75.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2),encoding='utf8')
    (output/'interior_r75.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf8')
    return spec


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--game',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();r=stage(a.game,a.output)
    print(json.dumps(dict(revision=75,groups=len(r['bindings']),extra_length_cm=EXTRA,secondary_percent=round(r['secondary_area_ratio']*100,2))))
