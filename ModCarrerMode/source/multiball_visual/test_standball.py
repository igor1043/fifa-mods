"""Selection and production Lua integration, including delayed native creation."""
import argparse
import configparser
from itertools import permutations
from pathlib import Path
import sys
import unittest

parser=argparse.ArgumentParser()
parser.add_argument('--lua-python-path',type=Path)
args,remaining=parser.parse_known_args()
if args.lua_python_path:sys.path.insert(0,str(args.lua_python_path))
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parent
scripts={name:(ROOT/path).read_text(encoding='utf8') for name,path in
         [('stand','standball.lua'),('var','../var_cabin/var_cabin.lua'),('smoke','../smoke_machine/smoke_machine.lua')]}

def environment():
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
        db={sle={}};rows={};creates=0;delayed=false
        gSportsRNA={}
        function gSportsRNA:GetTable(name,index)
            if name=='wvWipe' then return {leagueID=7} end
            assert(rows[index],'RNA pending');return rows[index]
        end
        function gSportsRNA:GetInt(row,key) return row[key] end
        function SleUpdate(i)
            local s=db.sle[i]
            s.isMascot=0;s.isVarCabin=0;s.isSmokeMachine=0;s.isEntranceProps=0
            s.sletype=rows[i].sletype
        end
        function GetTexture(i) return 'base_texture' end
        function GetRMSle(i,m) return 'base_model' end
        function CreateSleVariations(gr,batch,sles) end
        gRenderables={}
        function gRenderables:Create(name,index) creates=creates+1;return {index=index} end
        function gRenderables:AddSubObject(batch,actor,kind)
            if not delayed then rows[actor.index]={sletype=kind,sleindex=1} end
            db.sle[actor.index]={sletype=kind,teamid=7}
        end
        function new_scene() rows={};gRenderObj={batchSle={},sles={}} end
        FIFA16_STANDBALL_HOOK_READY=true
        FIFA16_VAR_CABIN_HOOK_READY=true
        FIFA16_SMOKE_MACHINE_HOOK_READY=true
    ''')
    return lua

class Standball(unittest.TestCase):
    def test_no_prototype_before_verified_asset_gate(self):
        lua=environment();lua.globals().FIFA16_STANDBALL_HOOK_READY=False
        lua.execute(scripts['stand']);lua.execute('new_scene()')
        lua.globals().FIFA16_STANDBALL_CREATE_LIVE()
        self.assertEqual(lua.globals().creates,0)
        lua.globals().FIFA16_STANDBALL_HOOK_READY=True
        lua.globals().FIFA16_STANDBALL_CREATE_LIVE()
        self.assertEqual(lua.globals().creates,1)

    def test_selection_exact_ids_and_phase_inheritance(self):
        config=configparser.ConfigParser();config.read(ROOT/'standball.ini')
        mapping=config['competitions']
        def choose(comp,round=0,generic=1):
            return mapping.get(str(round),mapping.get(str(comp),'generic'+str(generic)))
        self.assertEqual(choose(1738),'brasileirao')
        for comp in (1741,1747,1757):self.assertEqual(choose(comp),'cbf')
        for comp in (2325,2330,2335,2338):self.assertEqual(choose(comp),'paulistao')
        self.assertEqual(choose(0,1794),'cbf')
        self.assertEqual(choose(0,2339),'paulistao')
        self.assertEqual(choose(1738,999999),'brasileirao')
        self.assertEqual(choose(195),'generic1')
        self.assertEqual(choose(195,generic=2),'generic2')
        for comp in (0,7,83,350,351,22,1813,2340):self.assertTrue(choose(comp).startswith('generic'))

    def test_native_factory_retry_scene_switch_and_capacity(self):
        lua=environment();lua.execute(scripts['stand']);create=lua.globals().FIFA16_STANDBALL_CREATE_LIVE
        create();self.assertEqual(lua.globals().creates,0)
        lua.execute('new_scene();delayed=true')
        for _ in range(20):create()
        self.assertEqual(lua.globals().creates,1)
        lua.execute('new_scene();delayed=false');create();create()
        self.assertEqual(lua.globals().creates,2)
        lua.execute('new_scene();for i=0,175 do gRenderObj.sles[i]={} end');create()
        self.assertFalse(lua.globals().FIFA16_STANDBALL_LIVE_CREATED)

    def test_wrappers_preserve_other_modules_in_every_order(self):
        for order in permutations(('stand','smoke','var')):
            with self.subTest(order=order):
                lua=environment()
                for name in order:lua.execute(scripts[name])
                lua.execute('''
                    db.sle[0]={};rows[0]={sletype=17,sleindex=0}
                    db.sle[1]={};rows[1]={sletype=17,sleindex=1}
                    db.sle[2]={};rows[2]={sletype=3,sleindex=1}
                    db.sle[3]={};rows[3]={sletype=16,sleindex=1}
                    SleUpdate(0);SleUpdate(1);SleUpdate(2);SleUpdate(3)
                ''')
                get=lua.globals().GetRMSle
                self.assertEqual(get(0,0),'base_model')
                self.assertIn('var_cabin/model.rx3',get(2,0))
                self.assertIn('smoke_machine/model.rx3',get(3,0))
                for variant in ('brasileirao','cbf','paulistao','generic1','generic2'):
                    lua.globals().FIFA16_STANDBALL_VARIANT=variant
                    self.assertEqual(get(1,0),'data/sceneassets/standball/'+variant+'/model.rx3;')
                    self.assertEqual(lua.globals().GetTexture(1),'data/sceneassets/standball/'+variant+'/textures.rx3')
                lua.globals().FIFA16_STANDBALL_VARIANT='../bad'
                self.assertIn('standball/generic1/',get(1,0))
                self.assertEqual(lua.globals().db.sle[1].attribmatname,'simple_character_static')

    def test_script_reactivation_keeps_later_wrappers(self):
        lua=environment();lua.execute(scripts['stand'])
        lua.execute('calls=0;local base=GetRMSle;function GetRMSle(i,m) calls=calls+1;return base(i,m) end')
        lua.execute(scripts['stand']);lua.execute('db.sle[0]={};rows[0]={sletype=17,sleindex=0};SleUpdate(0);GetRMSle(0,0)')
        self.assertEqual(lua.globals().calls,1)

if __name__=='__main__':unittest.main(argv=[sys.argv[0]]+remaining)
