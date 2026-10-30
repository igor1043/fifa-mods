"""Mascot lookup, original assets, missing clubs and native career navigation."""
import copy,json,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
import numpy as np
import mascot_worker as worker
import build_apt as apt
from native_review_vm import open_native
from native_assets import read_model
from rx3 import Rx3,TEXTURE

GAME=Path(r'U:\fifa 16')

class MascotViewerTests(unittest.TestCase):
 def test_missing_package_never_uses_other_club(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);one=root/'data/sceneassets/mascot/1043';one.mkdir(parents=True)
   (one/'model.rx3').write_bytes(b'model');(one/'textures.rx3').write_bytes(b'texture')
   self.assertIsNone(worker.package(root,1629));self.assertEqual(worker.package(root,1043)[0],one/'model.rx3')
   (one/'textures.rx3').unlink();self.assertIsNone(worker.package(root,1043))
   with self.assertRaises(ValueError):worker.package(root,'../1043')
 def test_missing_mascot_publishes_empty_for_current_career(self):
  with tempfile.TemporaryDirectory() as temp:
   folder=Path(temp);req=dict(schema=1,pid=9,seq=10,club=1043,kind='mascot')
   saved=dict(path='unchanged/DATA',size=10,mtime_ns=11)
   with patch.object(worker,'observe',return_value=(saved,(90,7,1043))),patch.object(worker,'request',return_value=req):
    self.assertTrue(worker.generate(folder,folder,req,None))
   text=(folder/'status.tsv').read_text();self.assertIn('actor=0',text);self.assertNotIn('hash=',text)
 def test_other_club_uses_its_own_id_and_stale_request_cannot_publish(self):
  with tempfile.TemporaryDirectory() as temp:
   folder=Path(temp);req=dict(schema=1,pid=9,seq=10,club=1629,kind='mascot');saved=dict(path='unchanged/DATA',size=10,mtime_ns=11)
   with patch.object(worker,'observe',return_value=(saved,(90,7,1043))),patch.object(worker,'request',return_value=req):
    self.assertTrue(worker.generate(folder,folder,req,None))
   text=(folder/'status.tsv').read_text();self.assertIn('club=1629',text);self.assertIn('career=1043',text)
   (folder/'status.tsv').unlink()
   with patch.object(worker,'observe',return_value=(saved,(90,7,1043))),patch.object(worker,'request',return_value=dict(req,seq=11)):
    self.assertFalse(worker.generate(folder,folder,req,None));self.assertFalse((folder/'status.tsv').exists())
 def test_fourth_card_ready_back_controls_and_shutdown(self):
  with tempfile.TemporaryDirectory() as temp:
   target=Path(temp)/'browser.big';apt.build(GAME,target)
   vm,view,_,calls=open_native(target,apt.FULL)
   if not view.get('screenReady'):vm.invoke(view.get('Ready'),view)
   self.assertTrue(view.get('screenReady'))
   vm.invoke(view.get('LocalEventHandler'),view,[2,True]);self.assertEqual(view.get('navPage'),1)
   button=view.get('scene0').get('action4');vm.invoke(button.get('onRollOver'),button);vm.invoke(button.get('onRelease'),button)
   self.assertEqual(view.get('navPage'),6);self.assertEqual(view.get('hubIndex'),3)
   self.assertTrue(any(n=='SendSystemEvent' and list(a)==['Calendar','Server16ClubBrowser','mascot'] for n,a in calls))
   self.assertEqual([x[0] for x in vm.invoke(view.get('getHelpContext'),view)],['BACK','RAS_LR','L1R1','OPTION_TOP'])
   vm.invoke(view.get('LocalEventHandler'),view,[10,True])
   self.assertTrue(any(n=='SendSystemEvent' and list(a)==['Calendar','Server16ClubBrowser','mascot_center'] for n,a in calls))
   vm.invoke(view.get('LocalEventHandler'),view,[1,True]);self.assertEqual(view.get('navPage'),1);self.assertEqual(view.get('hubIndex'),3)
   vm.invoke(view.get('LocalEventHandler'),view,[6,True]);self.assertEqual(view.get('hubIndex'),0)
   vm.invoke(view.get('LocalEventHandler'),view,[5,True]);self.assertEqual(view.get('hubIndex'),3)
   vm.invoke(view.get('OnExitScreen'),view);vm.invoke(view.get('OnExitScreen'),view)
   self.assertEqual(sum(n=='Shutdown' for n,_ in calls),1)
   self.assertFalse(any('Budget' in n or 'Database' in n for n,_ in calls))
 def test_real_package_preserves_vertices_uv_and_compressed_colour(self):
  root=GAME/'data/sceneassets/mascot/111046';original=[p.read_bytes() for p in worker.package(GAME,111046)]
  blob,height=worker.model_bytes(*original)
  with tempfile.TemporaryDirectory() as temp:
   target=Path(temp)/'model.ff3d';target.write_bytes(blob);parts,textures=read_model(target)
  points=np.concatenate([p['v']['p'] for p in parts]);self.assertAlmostEqual(float(points[:,1].min()),0)
  self.assertAlmostEqual(float(points[:,1].max()),height,places=3)
  self.assertAlmostEqual(float(points[:,0].min()+points[:,0].max()),0,places=3)
  data=Rx3(original[1]).get(TEXTURE)[0];self.assertEqual(textures[0][3],data[32:32+len(textures[0][3])])
  self.assertEqual([p.read_bytes() for p in worker.package(GAME,111046)],original)

if __name__=='__main__':unittest.main()
