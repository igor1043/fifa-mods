from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import integrate_menu_layout as layout


class MenuIntegration(unittest.TestCase):
    XML = b'<root><tile><tileid NAME="CALENDAR" tileid="48"/><main_tile ID="48" DESTINATION="EnterCalendar" DATAPROVIDERID="CM_CALENDAR_DP"/><data ID="COMPETITION" TYPE="asset" PATH="league" WIDTH="40"/><data ID="TITLE" TYPE="title" PARAM="Old title" Y="18"/></tile></root>'

    def test_visual_pack_can_change_artwork_and_typography_but_not_live_bindings(self):
        new = self.XML.replace(b'Old title', b'New title').replace(b'Y="18"', b'Y="7"').replace(b'WIDTH="40"', b'WIDTH="52"')
        self.assertEqual(new, layout.checked_layout(self.XML, new))
        for old, new in ((b'tileid="48"', b'tileid="49"'),
                         (b'EnterCalendar', b'EnterGameSettings'),
                         (b'CM_CALENDAR_DP', b'OTHER_DP'),
                         (b'ID="COMPETITION"', b'ID="OTHER_COMPETITION"')):
            with self.subTest(binding=old), self.assertRaises(ValueError):
                layout.checked_layout(self.XML, self.XML.replace(old, new))

    def test_stage_keeps_only_active_layout_and_dds_and_does_not_mutate_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);pack = root/'pack';game = root/'game';out = root/'stage'
            rel = Path('data/ui/layout/careermanagerhubcfg.xml')
            for folder in (pack, game):
                (folder/rel).parent.mkdir(parents=True);(folder/rel).write_bytes(self.XML)
            (pack/rel.with_name('careermanagerhubcfg-rzm.xml')).write_bytes(b'broken alternate')
            (pack/rel.with_name('layout-new.rar')).write_bytes(b'archive')
            dds = bytearray(128);dds[:4] = b'DDS ';struct.pack_into('<I', dds, 4, 124);struct.pack_into('<II', dds, 12, 64, 64)
            icon = pack/'data/ui/imgAssets/tileicons/new_active.dds';icon.parent.mkdir(parents=True);icon.write_bytes(dds)
            report = layout.stage(pack, game, out)
            self.assertEqual(2, len(report['files']));self.assertEqual(2, len(report['skipped']))
            self.assertFalse((game/icon.relative_to(pack)).exists());self.assertEqual(self.XML, (game/rel).read_bytes())
            self.assertEqual(bytes(dds), (out/icon.relative_to(pack)).read_bytes())
            with self.assertRaises(ValueError):layout.stage(pack, game, game/'stage')


if __name__ == '__main__':
    unittest.main()
