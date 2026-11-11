"""Reproduce the frozen worker's partial runtime package in a fresh interpreter."""
import os,sys,shutil,subprocess,tempfile,unittest
from pathlib import Path

class FinanceImportPathTests(unittest.TestCase):
 def check_runtime(self,with_old_layout):
  source=Path(__file__).resolve().parents[2]
  game=Path(os.environ['SERVER16_GAME_ROOT'])
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);bank=root/'bank';market=root/'market';bank.mkdir();market.mkdir()
   shutil.copy2(Path(__file__).with_name('finance_ui.py'),bank/'finance_ui.py')
   (market/'native_screen.py').write_text("raise AssertionError('picked partial runtime native_screen')")
   if with_old_layout:(market/'layout.py').write_text("raise AssertionError('picked old runtime layout')")
   env=dict(os.environ);env['PYTHONPATH']=';'.join(map(str,(bank,source,source/'club_environment',source/'club_environment/vendor',source/'club_environment/preview',source/'club_environment/bank')))
   code="""from pathlib import Path
import finance_ui,native_screen,layout,sys
expected=Path(sys.argv[1]).resolve()
assert Path(finance_ui.market_source).resolve()==expected
assert Path(native_screen.__file__).resolve().parent==expected
assert Path(layout.__file__).resolve().parent==expected
print('PASS complete finance UI dependency package')
"""
   result=subprocess.run([sys.executable,'-c',code,str(game/'ModCarrerMode/source/club_environment/market')],env=env,cwd=root,capture_output=True,text=True,timeout=25)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('PASS complete finance UI dependency package',result.stdout)
 def test_lone_runtime_renderer_does_not_hide_shipped_layout(self):self.check_runtime(False)
 def test_shipped_pair_takes_precedence_over_stale_runtime(self):self.check_runtime(True)

if __name__=='__main__':unittest.main()
