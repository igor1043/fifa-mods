"""Close the hydration wall against the widened main room and raised ceiling.

The inherited annex ends at x=750/y=1320. V3's room ends farther out and
higher, leaving an opening beside the dispenser and above the backdrop.
Use the existing opaque neutral wall submesh; all club art stays in front.
"""
import numpy as np
from room_visual_r68 import box,join,read_mesh,replace_mesh
from room_fitted_shell import SIDE_INNER_X,SIDE_END_Z

LEFT=245.
OLD_RIGHT,OLD_TOP=750.,1320.
BOTTOM,BACK=1000.,1557.

def legacy_faces(vertices,indices):
    points=vertices['p'][indices.reshape(-1,3)]
    return ((points>=[LEFT-.02,BOTTOM-.02,1547.-.02])&
            (points<=[OLD_RIGHT+.02,OLD_TOP+.02,BACK+.02])).all((1,2))

def front_faces(vertices,indices,top):
    points=vertices['p'][indices.reshape(-1,3)]
    lo=points.min(1);hi=points.max(1)
    return ((np.abs(points[:,:,2]-SIDE_END_Z)<.001).all(1)&
            (np.abs(lo[:,0]-LEFT)<.01)&(np.abs(hi[:,0]-SIDE_INNER_X)<.01)&
            (np.abs(lo[:,1]-BOTTOM)<.01)&(np.abs(hi[:,1]-top)<.01))

def front_present(vertices,indices,top):
    points=vertices['p'][indices.reshape(-1,3)]
    mask=front_faces(vertices,indices,top)
    selected=points[mask]
    if len(selected)!=2:return False
    return (np.allclose(selected.min((0,1)),[LEFT,BOTTOM,SIDE_END_Z],atol=.02) and
            np.allclose(selected.max((0,1)),[SIDE_INNER_X,top,SIDE_END_Z],atol=.02))

def repair(rx,top=1338.):
    vertices,indices=read_mesh(rx,0)
    drop=legacy_faces(vertices,indices)
    front=front_present(vertices,indices,top)
    if front and not drop.any():return specification(top,0)
    if not 8<=int(drop.sum())<=24:
        raise ValueError('Hydration structural wall was not recognized; original room retained')
    if front:
        # A main-room/annex rebase can retain just the new front and the old
        # annex wall. Reconstruct the complete solid instead of two skins.
        drop|=front_faces(vertices,indices,top)
    triangles=indices.reshape(-1,3)[~drop]
    used,inverse=np.unique(triangles,return_inverse=True)
    wall=box((LEFT,BOTTOM,SIDE_END_Z),(SIDE_INNER_X,float(top),BACK))
    replace_mesh(rx,0,*join([(vertices[used],inverse.reshape(-1).astype('<u2')),wall]))
    return specification(top,int(drop.sum()))

def specification(top,removed):
    return dict(revision=1,material='existing_opaque_neutral_wall',
                bounds_cm=dict(lo=[LEFT,BOTTOM,SIDE_END_Z],hi=[SIDE_INNER_X,float(top),BACK]),
                original_faces_removed=removed,door_opening_unchanged=True,
                hydration_artwork_unchanged=True)

def obstacle(top=1338.):
    return dict(name='Current Dressing Room / hydration back wall',
                lo=[LEFT,0.,SIDE_END_Z],hi=[SIDE_INNER_X,float(top)-BOTTOM,BACK])
