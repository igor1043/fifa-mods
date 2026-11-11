import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class RoomReadyTests(unittest.TestCase):
 def test_failed_preparation_does_not_rebuild_on_every_worker_tick(self):
  room=importlib.import_module('prepare_native_room_components_r46_20261022')
  with tempfile.TemporaryDirectory() as temporary:
   game=Path(temporary);root=game/'room';(root/'runtime').mkdir(parents=True)
   snapshot=game/'ModCarrerMode/runtime/career_fce_snapshot.json';snapshot.parent.mkdir(parents=True)
   snap=dict(pid=77,club=1043,savePath='career1',saveWriteTime100ns=10,fixtures=[]);snapshot.write_text(json.dumps(snap));state={}
   with patch.object(room,'ROOT',root),patch.object(room,'GAME',game),patch.object(room,'room_request_status',return_value=dict(background_club=0)),patch.object(room,'calendar_stamp',return_value=(9,11,2026)),patch('room_interior_r71.art_stamp',return_value=1),patch('room_secondary_wall_r75.config_stamp',return_value=1),patch.object(room.room_v3,'stamp',return_value=1),patch.object(room.room_v3,'enabled',return_value=False),patch.object(room,'prepare',side_effect=ValueError('bad asset')) as prepare,patch.object(room,'publish_room_ready'),patch.object(room.time,'monotonic',return_value=100) as clock:
    refresh=lambda:room.refresh_requested_room(77,state,root/'runtime/log.txt')
    with self.assertRaises(ValueError):refresh()
    for _ in range(10):self.assertFalse(refresh())
    self.assertEqual(prepare.call_count,1)
    clock.return_value=131
    with self.assertRaises(ValueError):refresh()
    self.assertEqual(prepare.call_count,2)
    snap['club']=1629;snapshot.write_text(json.dumps(snap))
    with self.assertRaises(ValueError):refresh()
    self.assertEqual(prepare.call_count,3)
 def test_background_room_is_reused_on_entry_but_world_changes_refresh(self):
  room=importlib.import_module('prepare_native_room_components_r46_20261022')
  with tempfile.TemporaryDirectory() as temporary:
   game=Path(temporary);root=game/'room';(root/'runtime').mkdir(parents=True)
   snapshot=game/'ModCarrerMode/runtime/career_fce_snapshot.json';snapshot.parent.mkdir(parents=True)
   snap=dict(pid=77,club=1043,savePath='career1',saveWriteTime100ns=10,fixtures=[[0,1,2,3,4,1043,10,7,8,9,10]])
   snapshot.write_text(json.dumps(snap));status=dict(background_club=1043);state={}
   with patch.object(room,'ROOT',root),patch.object(room,'GAME',game),patch.object(room,'room_request_status',side_effect=lambda pid:status),patch.object(room,'calendar_stamp',return_value=(9,11,2026)) as date,patch('room_interior_r71.art_stamp',return_value=1),patch('room_secondary_wall_r75.config_stamp',return_value=1),patch.object(room.room_v3,'stamp',return_value=1),patch.object(room.room_v3,'enabled',return_value=False),patch.object(room,'prepare') as prepare,patch.object(room,'publish_room_ready') as publish:
    refresh=lambda:room.refresh_requested_room(77,state,root/'runtime/log.txt')
    self.assertTrue(refresh());self.assertEqual(prepare.call_count,1);self.assertEqual(publish.call_count,1)
    status['background_club']=0;refresh();refresh();self.assertEqual(prepare.call_count,1);self.assertEqual(publish.call_count,3)
    status['background_club']=1043;date.return_value=(10,11,2026);refresh();self.assertEqual(prepare.call_count,1);self.assertEqual(publish.call_count,4)
    status['background_club']=0;refresh();self.assertEqual(prepare.call_count,2)
    medical=root/'runtime/medical_native_capture.tsv';medical.write_text('S16MEDICAL 1 77 1043 20261110 100\nplayer\tinjury');refresh();self.assertEqual(prepare.call_count,3)
    medical.write_text('S16MEDICAL 1 77 1043 20261110 200\nplayer\tinjury');refresh();self.assertEqual(prepare.call_count,3)
    snap['fixtures'][0][8]=99;snapshot.write_text(json.dumps(snap));refresh();self.assertEqual(prepare.call_count,4)
    snap['savePath']='career2';snapshot.write_text(json.dumps(snap));refresh();self.assertEqual(prepare.call_count,5)
    snap['club']=1629;snapshot.write_text(json.dumps(snap));refresh();self.assertEqual(prepare.call_count,6)
 def test_ready_room_publishes_current_native_context_and_exact_package(self):
  room=importlib.import_module('prepare_native_room_components_r46_20261022')
  with tempfile.TemporaryDirectory() as temporary:
   game=Path(temporary);root=game/'room';(root/'runtime').mkdir(parents=True)
   import build_dressing_card_20261022 as ui
   (root/'runtime/room_header.json').write_text(json.dumps(dict(revision=ui.HEADER_REVISION,pid=77,club=1043)))
   snapshot=game/'ModCarrerMode/runtime/career_fce_snapshot.json';snapshot.parent.mkdir(parents=True)
   snapshot.write_text(json.dumps(dict(pid=77,club=1043,processCreated100ns=1234567)))
   import build_dressing_card_20261022 as ui
   package=game/ui.BIG;package.parent.mkdir(parents=True);package.write_bytes(b'native room package')
   profile=dict(club_id=1043,registry_address=0x1234,context_address=0x5678,context_epoch=9)
   with patch.object(room,'ROOT',root),patch.object(room,'GAME',game),patch.object(room,'calendar_stamp',return_value=((26,10,2026),profile)),patch('prepared_views.ticks',return_value=1000):
    room.publish_room_ready(77)
   text=(root/'runtime/view_ready.tsv').read_text()
   for expected in ('pid=77','club=1043','process_created_100ns=1234567','context=5678','registry=1234','epoch=9','date=20261026','captured_ms=1000'):
    self.assertIn(expected+'\n',text)
   self.assertIn('revision=',text)

 def test_previous_session_or_club_cannot_refresh_current_room(self):
  room=importlib.import_module('prepare_native_room_components_r46_20261022')
  with tempfile.TemporaryDirectory() as temporary:
   game=Path(temporary);root=game/'room';(root/'runtime').mkdir(parents=True)
   snapshot=game/'ModCarrerMode/runtime/career_fce_snapshot.json';snapshot.parent.mkdir(parents=True)
   snapshot.write_text(json.dumps(dict(pid=77,club=1043)))
   import build_dressing_card_20261022 as ui
   for header in (dict(revision=ui.HEADER_REVISION-1,pid=77,club=1043),dict(revision=ui.HEADER_REVISION,pid=88,club=1043),dict(revision=ui.HEADER_REVISION,pid=77,club=1629)):
    (root/'runtime/room_header.json').write_text(json.dumps(header))
    with patch.object(room,'ROOT',root),patch.object(room,'GAME',game),patch.object(room,'calendar_stamp') as calendar:
     room.publish_room_ready(77);calendar.assert_not_called()
    self.assertFalse((root/'runtime/view_ready.tsv').exists())


if __name__=='__main__':unittest.main()
