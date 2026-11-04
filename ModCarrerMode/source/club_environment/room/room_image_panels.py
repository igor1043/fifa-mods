"""Editable image panels with balanced native UV density and padded atlas tiles.

One material per bank; no glyph meshes, custom shader or removed mip levels.
"""
from pathlib import Path
import hashlib,math
import numpy as np
from PIL import Image
from room_interior_r71 import panel
from room_interior_r72 import write_groups
from room_visual_r68 import join,read_mesh
from rx3 import Rx3,MESH

TILE_WIDTH,TILE_HEIGHT,PAD=1024,256,4
INNER_WIDTH,INNER_HEIGHT=TILE_WIDTH-2*PAD,TILE_HEIGHT-2*PAD
_atlas_cache={}


def layout(width,height):
    count=max(1,math.ceil(width/(height*4)))
    atlas_height=1<<(count*TILE_HEIGHT-1).bit_length()
    return count,(TILE_WIDTH,atlas_height)


def atlas(image,width,height):
    key=(id(image),width,height)
    cached=_atlas_cache.get(key)
    if cached is not None and cached[0] is image:return cached[1]
    count,size=layout(width,height)
    image=image.convert('RGBA').resize((count*INNER_WIDTH,INNER_HEIGHT),Image.Resampling.LANCZOS)
    result=Image.new('RGBA',size,(0,0,0,255))
    for i in range(count):
        tile=np.asarray(image.crop((i*INNER_WIDTH,0,(i+1)*INNER_WIDTH,INNER_HEIGHT)))
        padded=Image.fromarray(np.pad(tile,((PAD,PAD),(PAD,PAD),(0,0)),mode='edge'))
        result.paste(padded,(0,i*TILE_HEIGHT))
    if len(_atlas_cache)>=8:_atlas_cache.pop(next(iter(_atlas_cache)))
    _atlas_cache[key]=(image,result)
    return result


def geometry(banks,height):
    groups={}
    for key,center,width,normal in banks:
        count,size=layout(width,height);right=np.cross((0,1,0),normal);parts=[]
        for i in range(count):
            offset=-width/2+(i+.5)*width/count
            uv=(PAD/size[0],(i*TILE_HEIGHT+PAD)/size[1],
                (TILE_WIDTH-PAD)/size[0],((i+1)*TILE_HEIGHT-PAD)/size[1])
            parts.append(panel(np.array(center)+right*offset,width/count,height,normal,uv))
        groups[key]=parts
    return groups


def build(game,banks,height,template,prefix):
    groups=geometry(banks,height);fingerprint=hashlib.sha256()
    for key,parts in groups.items():
        fingerprint.update(key.encode())
        for v,i in parts:fingerprint.update(v.tobytes());fingerprint.update(i.tobytes())
    relative=prefix+'image_panels_'+fingerprint.hexdigest()[:14]+'.rx3'
    target=Path(game)/relative
    bindings=[{'material':key,'submesh':'room_part_'+str(i+1)} for i,key in enumerate(groups)]
    if not target.is_file():
        target.parent.mkdir(parents=True,exist_ok=True);write_groups(template,groups,target)
    return relative,bindings


def planar(image,quad):
    """Pack a full rectangular picture without distorting its physical density."""
    if len(quad)!=4 or not np.allclose(quad['uv'],((0,0),(1,0),(1,1),(0,1))):
        raise ValueError('Image panel requires the original rectangular UV plane')
    tile,pad=1024,4;inside=tile-2*pad
    w,h=image.size;cols=math.ceil(w/inside);rows=math.ceil(h/inside)
    size=(1<<(cols*tile-1).bit_length(),1<<(rows*tile-1).bit_length())
    image=image.convert('RGBA');result=Image.new('RGBA',size,(0,0,0,255));parts=[]
    top,left=quad['p'][1]-quad['p'][0],quad['p'][3]-quad['p'][0]
    for row in range(rows):
        for col in range(cols):
            x,y=col*inside,row*inside;cw,ch=min(inside,w-x),min(inside,h-y)
            crop=np.asarray(image.crop((x,y,x+cw,y+ch)))
            crop=np.pad(crop,((pad,tile-ch-pad),(pad,tile-cw-pad),(0,0)),mode='edge')
            result.paste(Image.fromarray(crop),(col*tile,row*tile))
            v=quad.copy()
            for i,(u,t) in enumerate(((0,0),(1,0),(1,1),(0,1))):
                v['p'][i]=quad['p'][0]+top*((x+u*cw)/w)+left*((y+t*ch)/h)
                v['uv'][i]=((col*tile+pad+u*cw)/size[0],(row*tile+pad+t*ch)/size[1])
            parts.append((v,np.array([0,2,1,0,3,2],dtype='<u2')))
    return result,join(parts)


def next_match_board(game,context,read_asset,model,submesh):
    """Redraw the board's data as an image; keep all original scene coordinates."""
    from room_dynamic_context_20261022 import draw_board
    import room_v3
    game=Path(game);rx=Rx3((game/model).read_bytes())
    names=[n.removesuffix('.FxRenderableSimple') for kind,n in rx.names() if kind==MESH]
    vertices,ids=read_mesh(rx,names.index(submesh))
    # Native coordinates are ~235 x 148 cm. Use the same pixels/cm in both
    # directions instead of stretching the old square bitmap over this board.
    width=float(np.linalg.norm(vertices['p'][1]-vertices['p'][0]))
    height=float(np.linalg.norm(vertices['p'][3]-vertices['p'][0]))
    pixel_width=4064;pixel_height=round(pixel_width*height/width)
    signature=hashlib.sha256(b'picture-atlas-v1'+context['board_texture'].encode()+vertices.tobytes()).hexdigest()[:14]
    image_ref=room_v3.PREFIX+'board_atlas_'+signature+'.rx3'
    model_ref=room_v3.PREFIX+'board_image_'+signature+'.rx3'
    if not (game/image_ref).is_file() or not (game/model_ref).is_file():
        image=draw_board(context,read_asset,size=(pixel_width,pixel_height))
        sheet,mesh=planar(image,vertices)
        from room_native_hanging_20261022 import texture_package
        if not (game/image_ref).is_file():texture_package(sheet,game/image_ref,'v3_cm')
        if not (game/model_ref).is_file():write_groups(game/room_v3.OLD/'locker_support_r68.rx3',{'image':[mesh]},game/model_ref)
    return model_ref,image_ref,'v3_cm','room_part_1'
