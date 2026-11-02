import os,unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
import portable_paths as portable
from room_visual_r68 import box
from room_coach_r76 import clip_office,geometry,LEFT,FRONT
from room_coach_data_r76 import build


class Row:
    def __init__(self,**values):self.fields=values
    def value(self,key):return self.fields[key]


class CoachRoomTests(unittest.TestCase):
    def test_shared_wall_keeps_medical_half_and_removes_old_office(self):
        v,ids=box((-756,1000,2352),(756,1320,2364));new,indices=clip_office(v,ids)
        p=new['p'][indices.reshape(-1,3)]
        self.assertTrue(len(indices)>0)
        self.assertFalse(np.any((p[:,:,0].min(1)>LEFT+.01)&(p[:,:,2].min(1)>FRONT+.01)))
        self.assertAlmostEqual(float(p[:,:,0].min()),-756)
        self.assertTrue(np.isfinite(new['uv']).all())

    def test_locker_geometry_is_preserved_exactly(self):
        v,ids=box((650,1000,600),(740,1270,700));new,indices=clip_office(v,ids)
        np.testing.assert_array_equal(new['p'][indices],v['p'][ids]);np.testing.assert_array_equal(new['uv'][indices],v['uv'][ids])

    def test_open_coach_door_is_not_cut_with_the_furniture(self):
        v,ids=box((243,1002,1556),(249,1228,1660));new,indices=clip_office(v,ids,True)
        np.testing.assert_array_equal(new['p'][indices],v['p'][ids])

    def test_geometry_has_three_separate_chairs_and_no_window_openings(self):
        groups,obstacles=geometry();chairs=[b for b in obstacles if b['name'].endswith('/ cadeira')]
        self.assertEqual(len(chairs),3);self.assertEqual(len(groups),8)
        walls=[b for b in obstacles if b['name'].endswith('/ parede')];self.assertEqual(len(walls),3)
        self.assertTrue(all(b['hi'][1]==320 for b in walls))

    def test_derived_six_games_are_not_replaced_by_two_fixtures_or_added_twice(self):
        tables={
          'leagueteamlinks':[Row(teamid=1,leagueid=53,secondarytable=0),Row(teamid=2,leagueid=53,secondarytable=0)],
          'teams':[Row(teamid=1,teamname='Clube A'),Row(teamid=2,teamname='Clube B')],
          'players':[Row(playerid=10,overallrating=80,potential=85,preferredposition1=24,contractvaliduntil=2027)],
          'career_calendar':[Row(startdate=20260101)]}
        snap=dict(date=20260810,nodes=[[1,-1,3,53,0],[2,1,5,-1,0]],
          standings=[[0,2,1,0,0,0,0,0,0,0],[1,2,2,0,0,0,0,0,0,0]],
          derivedStandings=[[0,2,1,5,0,0,1,0,0,6,14,2,2,0],[1,2,2,0,0,1,0,0,5,6,0,2,2,14]],
          fixtures=[[1,2,2,20260801,1500,1,2,2,0,1],[2,2,2,20260802,1500,1,2,1,0,1]],
          stats=[[0,2,1,10,2,180,1,1,140,3]])
        c=dict(club=1,date=20260810,league=53)
        with patch('competition_names_r57.competition_name',return_value='Liga'):
            result=build(c,snap,[dict(id=10,name='Atacante',number=9)],lambda name:tables.get(name,[]),portable.GAME,set(tables))
        self.assertEqual(result['stats']['games'],6);self.assertEqual(result['stats']['wins'],6)
        self.assertEqual(result['stats']['goalsFor'],16);self.assertEqual(result['squad'][0]['rating'],7)
        self.assertEqual(result['table'][0]['rank'],1);self.assertEqual(len(result['recent']),2)

if __name__=='__main__':unittest.main()
