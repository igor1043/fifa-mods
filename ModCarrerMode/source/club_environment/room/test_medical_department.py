from pathlib import Path
from datetime import date
import copy,json,tempfile,unittest
from unittest.mock import patch
import numpy as np
import medical_department as clinic
from medical_department_geometry import clinical,treadmill,bicycle
from room_visual_r68 import box,join
from room_medical_data_r77 import enrich
import portable_paths as portable


class Row:
 def __init__(self,**fields):self.fields=fields
 def value(self,key):return self.fields[key]


class ClinicalTests(unittest.TestCase):
 def test_partial_install_cannot_activate_clipping_or_replace_the_old_room(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p=root/clinic.MANIFEST;p.parent.mkdir(parents=True)
   p.write_text(json.dumps(dict(schema=1,required=['missing.rx3'])),encoding='utf8')
   self.assertIsNone(clinic.specification(root));self.assertEqual(clinic.model_path(root,'anything'), 'anything')

 def test_west_clipping_preserves_main_room_and_coach_geometry_exactly(self):
  shapes=[box((-1550,1000,1800),(-1400,1300,1900)),box((-300,1000,1800),(100,1300,1900)),box((-750,1000,100),(-600,1300,200))]
  v,idx=join(shapes);a,b=clinic.outside_clinic(v,idx)
  expected=np.concatenate([p['p'][i] for p,i in shapes[1:]])
  np.testing.assert_array_equal(a['p'][b],expected)

 def test_crossing_walls_are_clipped_at_the_boundary_and_keep_uvs_finite(self):
  v,idx=box((-500,1000,2000),(500,1320,2010));a,b=clinic.outside_clinic(v,idx)
  self.assertGreater(len(b),0);self.assertGreaterEqual(a['p'][b][:,0].min(),-335)
  self.assertEqual(a['p'][b][:,0].max(),500);self.assertTrue(np.isfinite(a['uv']).all());self.assertEqual(b.ndim,1)

 def test_hydration_mask_does_not_remove_counter_fridge_or_cups(self):
  pieces=[box((560,1095,1490),(590,1141,1520)),box((346,1095,1500),(354,1127,1510)),box((337,1090,1475),(685,1095,1542)),box((440,1095,1500),(455,1115,1510)),box((347,1030,1500),(355,1060,1510))]
  v,idx=join(pieces);mask=clinic.old_hydration(v,idx)
  self.assertEqual(int(mask.sum()),24);self.assertFalse(mask[24:].any())

 def test_instance_transform_does_not_change_rotation_or_render_origin(self):
  identity=[1,0,0,0,0,1,0,0,0,0,1,0,100000,0,0,1]
  result=clinic.translated(identity,[573,1095,1505]);self.assertEqual(result[12:15],[100573,1095,1505]);self.assertEqual(result[:12],identity[:12])

 def test_doors_have_one_plaque_each_and_new_equipment_has_three_tables(self):
  s=clinical();self.assertEqual(len(s.groups['board_door_medical']),1);self.assertEqual(len(s.groups['board_door_coach']),1)
  self.assertEqual(sum(o['name'].endswith('/ treatment table') for o in s.obstacles),3)
  for builder in (clinical,treadmill,bicycle):
   for parts in builder().groups.values():
    for v,idx in parts:
     self.assertLess(int(idx.max()),len(v));self.assertTrue(np.isfinite(v['p']).all());self.assertTrue(np.isfinite(v['uv']).all());self.assertEqual(len(idx)%3,0)

 def test_age_and_forecast_follow_the_career_date_without_inventing_unknown_data(self):
  epoch=date(1582,10,14);players=[Row(playerid=1,birthdate=(date(2000,1,20)-epoch).days,stamina=80),Row(playerid=2,birthdate=(date(1990,1,1)-epoch).days,stamina=60)]
  rows=lambda key:players if key=='players' else []
  context=dict(club=1043,date=20260115,medical=dict(players=[dict(player=1,name='Atleta',weeks=2,injury='Tipo não informado',source='saved_teamplayerlinks',**{'return':'2 semanas'})]))
  with tempfile.TemporaryDirectory() as folder,patch.object(portable,'ROOM',Path(folder)):
   result=enrich(context,dict(savePath=Path(folder)/'career'),[dict(id=1,name='Atleta'),dict(id=2,name='Outro')],rows)
  self.assertEqual(result['averageAge'],30.5);p=result['players'][0];self.assertEqual(p['age'],25);self.assertEqual(p['forecastDate'],'29/01/2026');self.assertTrue(p['forecastEstimated'])
  self.assertEqual(p['injury'],'Tipo não informado')


if __name__=='__main__':unittest.main()
