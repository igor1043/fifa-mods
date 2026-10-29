"""A source-driven build must never publish a stale generated runtime screen."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys,tempfile,unittest
import bootstrap_ui

class BootstrapTests(unittest.TestCase):
 def test_publish_uses_the_package_just_built_even_with_an_old_runtime(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);source=root/'source-bank';runtime=root/'old-runtime';relative='package/data/ui/game/screens/career/server16/bankloans.big'
   stale=runtime/relative;stale.parent.mkdir(parents=True);stale.write_bytes(b'old screen')
   def bank_build(_):
    file=source/relative;file.parent.mkdir(parents=True);file.write_bytes(b'current screen')
   def output(name):
    file=root/name;file.write_bytes(b'generic screen');return file
   def finance_build(payload,file):
    self.assertFalse(payload['ready'])
    self.assertEqual(payload['budget'],0)
    file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'generic finance screen')
   modules={'bank_ui_r60':SimpleNamespace(build=bank_build),'build_screen':SimpleNamespace(HERE=source),
       'build_preview':SimpleNamespace(build=lambda _:output('preview.big')),
       'build_loading':SimpleNamespace(build=lambda file,*args:file.parent.mkdir(parents=True,exist_ok=True)),
       'finance_ui':SimpleNamespace(build=finance_build),
       'build_dressing_card_20261022':SimpleNamespace(screen=lambda *args:output('room.big'))}
   with patch.object(bootstrap_ui,'p',SimpleNamespace(GAME=root,BANK=runtime)),patch.dict(sys.modules,modules):
    bootstrap_ui.generate()
   self.assertEqual((root/'data/ui/game/screens/career/server16/bankloansv2.big').read_bytes(),b'current screen')
   self.assertEqual(stale.read_bytes(),b'old screen')
   self.assertEqual((root/'data/ui/game/screens/career/server16/clubfinance.big').read_bytes(),b'generic finance screen')

if __name__=='__main__':unittest.main()
