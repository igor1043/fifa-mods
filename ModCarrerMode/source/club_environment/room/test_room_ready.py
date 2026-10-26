import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class RoomReadyTests(unittest.TestCase):
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
