from pathlib import Path
import copy,tempfile,unittest
from unittest.mock import patch
import numpy as np
import portable_paths as portable
from room_visual_r68 import box
from room_medical_r77 import clip_medical,geometry
from room_medical_data_r77 import enrich,remaining_days


class Row:
    def __init__(self,**values):self.fields=values
    def value(self,key):return self.fields[key]


class MedicalRoomTests(unittest.TestCase):
    def rows(self,name):
        return {'players':[Row(playerid=1,stamina=82)],'career_calendar':[Row(startdate=20260101)]}.get(name,[])
    def context(self,date,weeks):
        return dict(pid=1,club=1043,date=date,medical=dict(players=[] if weeks is None else [dict(player=1,name='Atleta',weeks=weeks,injury='Lesão informada',**{'return':f'{weeks} semanas'},source='saved_teamplayerlinks')]))
    def observe(self,context,path):return enrich(context,dict(savePath=path),[dict(id=1,name='Atleta')],self.rows)

    def test_shared_back_wall_keeps_the_coach_half(self):
        v,ids=box((-762,1000,2352),(756,1320,2364));v,ids=clip_medical(v,ids)
        self.assertGreater(len(ids),0);self.assertAlmostEqual(float(v['p'][ids][:,0].min()),-335)
        self.assertAlmostEqual(float(v['p'][ids][:,0].max()),756)

    def test_clipping_does_not_touch_main_locker_geometry(self):
        v,ids=box((-750,1000,500),(-650,1290,600));out,indices=clip_medical(v,ids)
        np.testing.assert_array_equal(out['p'][indices],v['p'][ids])

    def test_parallel_beds_and_clinical_sector_colliders(self):
        groups,obstacles=geometry();beds=[o for o in obstacles if o['name'].endswith('/ maca')]
        self.assertEqual(len(beds),3);self.assertEqual(len({(o['lo'][0],o['hi'][0]) for o in beds}),1)
        self.assertTrue(any('cabos' in o['name'] for o in obstacles));self.assertTrue(any('halteres' in o['name'] for o in obstacles))

    def test_observed_countdown_persists_and_cannot_leak_between_careers(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(portable,'ROOM',Path(tmp)):
            first=self.observe(self.context(20260101,4),Path(tmp)/'career_a');self.assertEqual(first['players'][0]['recovery'],0)
            next=self.observe(self.context(20260115,2),Path(tmp)/'career_a');self.assertEqual(next['players'][0]['recovery'],50)
            other=self.observe(self.context(20260115,2),Path(tmp)/'career_b');self.assertEqual(other['players'][0]['recovery'],0)
            rolled=self.observe(self.context(20260101,4),Path(tmp)/'career_a');self.assertEqual(rolled['players'][0]['recovery'],0)

    def test_history_records_absence_from_the_current_injury_list(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(portable,'ROOM',Path(tmp)):
            self.observe(self.context(20260101,4),Path(tmp)/'career')
            healthy=self.observe(self.context(20260201,None),Path(tmp)/'career')
            self.assertEqual(healthy['availableCount'],1);self.assertEqual(healthy['unavailableCount'],0)
            self.assertEqual(healthy['observedHistory'][0]['last'],20260201)

    def test_unknown_metrics_remain_unknown_and_stamina_is_only_an_attribute(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(portable,'ROOM',Path(tmp)):
            result=self.observe(self.context(20260101,0),Path(tmp)/'career')
            self.assertIsNone(result['players'][0]['recovery']);self.assertIsNone(result['fatigue']);self.assertIsNone(result['injuryRisk'])
            self.assertEqual(result['condition'][0]['stamina'],82)

    def test_native_return_text_is_parsed_without_making_a_diagnosis(self):
        self.assertEqual(remaining_days(dict(source='native_InjuryList',**{'return':'2 semanas'}),20260101),14)
        self.assertEqual(remaining_days(dict(source='native_InjuryList',**{'return':'Retorno em 5 dias'}),20260101),5)
        self.assertIsNone(remaining_days(dict(source='native_InjuryList',weeks=0,**{'return':'Não informado'}),20260101))

    def test_large_squad_is_not_truncated_by_native_six_page_limit(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(portable,'ROOM',Path(tmp)):
            roster=[dict(id=i,name=f'Atleta {i}') for i in range(1,44)];c=self.context(20260101,4)
            c['medical']['players']=[dict(player=p['id'],name=p['name'],weeks=4,injury='Lesão',**{'return':'4 semanas'},source='saved_teamplayerlinks') for p in roster]
            result=enrich(c,dict(savePath=Path(tmp)/'career'),roster,self.rows)
            self.assertEqual(result['unavailableCount'],43);self.assertLessEqual(result['pages'],6)
            seen=[p['player'] for i in range(result['pages']) for p in result['players'][i*result['pageSize']:(i+1)*result['pageSize']]]
            self.assertEqual(seen,list(range(1,44)))

if __name__=='__main__':unittest.main()
