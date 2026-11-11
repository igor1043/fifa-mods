import json,os,tempfile,unittest
from pathlib import Path
from collections import deque
import numpy as np
from room_prop_conversion import transform,without_coplanar_duplicates,merged_parts,Palette
from room_gym_equipment import PREFIX,specification,obstacles
from room_medical_r77 import geometry
from room_pes_office import prepare


class ConversionTests(unittest.TestCase):
    def test_reverse_coplanar_faces_removed_but_nearby_surfaces_survive(self):
        p=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,.01],[1,0,.01],[0,1,.01]],float)
        part=dict(p=p,idx=np.array([0,1,2,2,1,0,3,4,5]))
        result=without_coplanar_duplicates([part])
        np.testing.assert_array_equal(result[0]['idx'],[0,1,2,3,4,5])

    def test_floor_contact_dimensions_and_normals_survive_rotation(self):
        p=np.array([[0,3,0],[100,3,0],[100,103,50]],float);n=np.tile([0,0,1.],(3,1))
        out,normal=transform(p,n,[50,3,25],[-800,1002.7,2600],90)
        self.assertAlmostEqual(out[:,1].min(),1002.7)
        np.testing.assert_allclose(np.ptp(out,axis=0),[50,100,100],atol=1e-6)
        np.testing.assert_allclose(normal,np.tile([1,0,0],(3,1)),atol=1e-6)

    def test_authored_normals_correct_reversed_imported_winding(self):
        parts=[dict(p=np.array([[0,0,0],[1,0,0],[0,1,0]],float),n=np.tile([0,0,1.],(3,1)),uv=np.zeros((3,2)),idx=np.array([2,1,0]))]
        m=merged_parts(parts)[0];tri=m['positions'][m['indices'].reshape(-1,3)][0]
        self.assertGreater(np.dot(np.cross(tri[1]-tri[0],tri[2]-tri[0]),[0,0,1]),0)

    def test_incomplete_optional_pack_cannot_remove_existing_equipment(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)/PREFIX;folder.mkdir(parents=True)
            (folder/'equipment.json').write_text(json.dumps(dict(required=['missing.rx3'],bindings=[],obstacles=[])))
            original=[dict(name='Departamento médico R77 / estação de cabos')]
            self.assertIsNone(specification(root));self.assertEqual(obstacles(root,original),original)

    def test_clinical_treatments_preserved_when_rehab_placeholders_are_removed(self):
        _,old=geometry();_,new=geometry(rehab_furniture=False)
        for name in ('maca','carrinho','banco giratório','parede'):
            self.assertEqual([v for v in old if v['name'].endswith('/ '+name)],[v for v in new if v['name'].endswith('/ '+name)])
        self.assertFalse(any(v['name'].endswith('/ estação de cabos') for v in new))

    def test_added_props_keep_their_own_diffuse_name(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'data/sceneassets/server16_dressing_room_v3/pes_office/office.json';path.parent.mkdir(parents=True)
            path.write_text(json.dumps(dict(bindings=[dict(key='prop',model='m',texture='t',texname='equipment_cm',alpha=False,submesh='s')])));calls=[]
            prepare(root,lambda *args:calls.append(args),list(range(16)))
            self.assertEqual(calls[0][3],'equipment_cm')

    def test_palette_reuses_swatch_and_converts_linear_colors(self):
        palette=Palette();first=palette.uv([.5,.5,.5,1],True)
        self.assertEqual(first,palette.uv([.5,.5,.5,1],True));self.assertEqual(len(palette.colors),1)
        self.assertGreater(palette.colors[0][0],180)


STAGE=os.environ.get('ROOM_EQUIPMENT_STAGE')
@unittest.skipUnless(STAGE,'Set ROOM_EQUIPMENT_STAGE for converted asset checks')
class StagedEquipmentTests(unittest.TestCase):
    def setUp(self):
        self.stage=Path(STAGE);self.game=Path(os.environ['SERVER16_GAME_ROOT'])
        self.office=json.loads((self.stage/'data/sceneassets/server16_dressing_room_v3/pes_office/office.json').read_bytes())
        self.gym=json.loads((self.stage/PREFIX/'equipment.json').read_bytes())

    def test_all_native_mesh_indices_and_texture_bindings_are_valid(self):
        from rx3 import Rx3,VERTEX,INDEX,TEXTURE
        from room_visual_r68 import read_mesh
        from room_interior_r71 import decode_texture
        for b in self.office['bindings']+self.gym['bindings']:
            model=self.stage/b['model']
            if not model.is_file():model=self.game/b['model']
            rx=Rx3(model.read_bytes());slot=int(b['submesh'].rsplit('_',1)[1])-1
            v,ids=read_mesh(rx,slot)
            self.assertTrue(0<len(v)<=65535);self.assertEqual(len(ids)%3,0);self.assertLess(int(ids.max()),len(v))
            self.assertTrue(np.isfinite(v['p']).all());self.assertTrue(np.isfinite(v['uv']).all())
            texture=self.stage/b['texture']
            if not texture.is_file():texture=self.game/b['texture']
            tex=Rx3(texture.read_bytes());name=b.get('texname','equipment_cm' if b in self.gym['bindings'] else 'office_cm')
            self.assertIn((TEXTURE,name),tex.names());decode_texture(texture).load()

    def test_rehab_props_are_inside_room_and_do_not_intersect_one_another(self):
        items=self.gym['obstacles']
        for i,a in enumerate(items):
            self.assertGreaterEqual(a['lo'][0],-1110);self.assertLessEqual(a['hi'][0],-341)
            self.assertGreaterEqual(a['lo'][2],2530);self.assertLessEqual(a['hi'][2],2832)
            self.assertGreaterEqual(a['lo'][1],2.2)
            for b in items[i+1:]:
                overlap=min(a['hi'][0],b['hi'][0])>max(a['lo'][0],b['lo'][0]) and min(a['hi'][2],b['hi'][2])>max(a['lo'][2],b['lo'][2])
                self.assertFalse(overlap,(a['name'],b['name']))

    def test_entrance_paths_reach_both_sides_of_office_and_rehabilitation(self):
        def accessible(items,bounds,start,targets):
            x0,x1,z0,z1=bounds;step=10;radius=25
            def cell(p):return (round((p[0]-x0)/step),round((p[1]-z0)/step))
            def free(c):
                x,z=x0+c[0]*step,z0+c[1]*step
                return x0<=x<=x1 and z0<=z<=z1 and not any(p['lo'][1]<180 and p['hi'][1]>5 and p['lo'][0]-radius<x<p['hi'][0]+radius and p['lo'][2]-radius<z<p['hi'][2]+radius for p in items)
            first=cell(start);self.assertTrue(free(first));queue=deque([first]);seen={first}
            while queue:
                a,b=queue.popleft()
                for c in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
                    if c not in seen and free(c):seen.add(c);queue.append(c)
            for p in targets:self.assertIn(cell(p),seen,p)
        accessible(self.office['obstacles'],(-290,715,1600,2560),(180,1630),[(350,2180),(150,2490),(580,2490),(-240,2100)])
        clinical=json.loads((self.stage/self.gym['medical_spec']).read_bytes())['obstacles']
        accessible(clinical+self.gym['obstacles'],(-1080,-365,1585,2800),(-545,1600),[(-780,2470),(-780,2740),(-660,2630),(-450,2720)])

    def test_batching_preserves_capacity_for_other_room_components(self):
        self.assertLessEqual(len(self.office['bindings'])-15+len(self.gym['bindings']),7)
        self.assertIn('medical_room_r77.rx3',self.gym['medical_model'])


if __name__=='__main__':unittest.main()
