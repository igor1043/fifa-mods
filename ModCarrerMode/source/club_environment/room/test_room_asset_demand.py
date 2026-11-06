import importlib
import json
import os
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


class RoomAssetDemandTests(unittest.TestCase):
 def setUp(self):
  self.room=importlib.import_module('prepare_native_room_components_r46_20261022')
  self.stack=ExitStack();self.addCleanup(self.stack.close)
  self.game=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
  self.root=self.game/'room';(self.root/'runtime').mkdir(parents=True)
  for key,value in [('ROOT',self.root),('GAME',self.game)]:
   self.stack.enter_context(patch.object(self.room,key,value))
  self.status=self.root/'runtime/native_status.json'
  self.snapshot=self.game/'ModCarrerMode/runtime/career_fce_snapshot.json'
  self.snapshot.parent.mkdir(parents=True)
  self.snapshot.write_text(json.dumps(dict(pid=77,club=1043,fixtures=[])))
  self.log=self.root/'runtime/helper.log';self.state={}

 def requested(self,**fields):
  self.status.write_text(json.dumps(dict(pid=77,installed=True,requested=True,error=0,**fields)))

 def test_only_fresh_matching_healthy_ui_request_wakes_assets(self):
  self.assertFalse(self.room.room_requested(77))
  valid=dict(pid=77,installed=True,requested=True,error=0)
  for update in [dict(pid=88),dict(requested=False),dict(installed=False),dict(error=9)]:
   self.status.write_text(json.dumps(dict(valid,**update)))
   self.assertFalse(self.room.room_requested(77))
  self.requested();self.assertTrue(self.room.room_requested(77))
  os.utime(self.status,(time.time()-10,time.time()-10))
  self.assertFalse(self.room.room_requested(77))
  self.status.write_text('{partial');self.assertFalse(self.room.room_requested(77))

 def test_calendar_year_without_room_never_reads_calendar_or_prepares(self):
  self.status.write_text(json.dumps(dict(pid=77,installed=True,requested=False,error=0)))
  with patch.object(self.room,'prepare') as prepare,patch.object(self.room,'calendar_stamp') as calendar,patch.object(self.room,'refresh_appearance') as appearance,patch.object(self.room,'publish_room_ready') as ready:
   self.state['appearance_changed']=True
   for _ in range(365):self.assertFalse(self.room.refresh_requested_room(77,self.state,self.log))
   for mock in (prepare,calendar,appearance,ready):mock.assert_not_called()
  self.assertTrue(self.state['appearance_changed'])

 def test_enter_after_calendar_jump_prepares_latest_once_then_stays_idle(self):
  self.requested()
  with patch.object(self.room,'prepare') as prepare,patch.object(self.room,'calendar_stamp',return_value=(1,12,2026)) as calendar,patch.object(self.room,'publish_room_ready') as ready,patch('room_interior_r71.art_stamp',return_value=()),patch('room_secondary_wall_r75.config_stamp',return_value=()),patch.object(self.room.room_v3,'stamp',return_value='v3'),patch.object(self.room.room_v3,'enabled',return_value=True):
   self.assertTrue(self.room.refresh_requested_room(77,self.state,self.log))
   self.room.refresh_requested_room(77,self.state,self.log)
   prepare.assert_called_once();self.assertEqual(ready.call_count,2)
   self.status.write_text(json.dumps(dict(pid=77,installed=True,requested=False,error=0)))
   calendar.return_value=(31,12,2026)
   for _ in range(30):self.room.refresh_requested_room(77,self.state,self.log)
   prepare.assert_called_once();self.assertEqual(calendar.call_count,2)
   self.requested();self.room.refresh_requested_room(77,self.state,self.log)
   self.assertEqual(prepare.call_count,2)

 def test_previous_session_snapshot_cannot_prepare_current_room(self):
  self.requested();self.snapshot.write_text(json.dumps(dict(pid=88,club=1043)))
  with patch.object(self.room,'prepare') as prepare,patch.object(self.room,'calendar_stamp') as calendar:
   self.assertFalse(self.room.refresh_requested_room(77,self.state,self.log))
   prepare.assert_not_called();calendar.assert_not_called()

 def test_appearance_change_waits_for_room_and_refreshes_only_once(self):
  self.requested()
  with patch.object(self.room,'prepare'),patch.object(self.room,'calendar_stamp',return_value=(1,12,2026)),patch.object(self.room,'publish_room_ready'),patch('room_interior_r71.art_stamp',return_value=()),patch('room_secondary_wall_r75.config_stamp',return_value=()),patch.object(self.room.room_v3,'stamp',return_value='v3'),patch.object(self.room.room_v3,'enabled',return_value=True),patch.object(self.room,'refresh_appearance') as appearance:
   self.room.refresh_requested_room(77,self.state,self.log)
   self.state['appearance_changed']=True
   self.room.refresh_requested_room(77,self.state,self.log)
   self.room.refresh_requested_room(77,self.state,self.log)
   appearance.assert_called_once();self.assertFalse(self.state['appearance_changed'])


if __name__=='__main__':unittest.main()
