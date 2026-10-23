"""Offline regression checks. Never attaches to FIFA or submits financial actions."""
from pathlib import Path
import argparse,os,sys,unittest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--game-root',type=Path,required=True);args=parser.parse_args()
    os.environ['SERVER16_GAME_ROOT']=str(args.game_root.resolve())
    source=Path(__file__).resolve().parent;runtime=args.game_root/'ModCarrerMode/runtime/club_environment'
    sys.path[:0]=[str(source.parent),str(source),str(source/'vendor'),str(runtime/'room'),str(runtime/'preview'),str(runtime/'bank')]
    tests=unittest.TestSuite()
    for folder,pattern in (('bank','test_finance_r57.py'),('bank','test_finance_live_ui.py'),('preview','test_preview_details.py'),('room','test_room_safety_r53.py'),('room','test_room_material_install_r59.py'),('room','test_kit_print_r61.py')):
        tests.addTests(unittest.defaultTestLoader.discover(str(runtime/folder),pattern=pattern,top_level_dir=str(runtime/folder)))
    return 0 if unittest.TextTestRunner(verbosity=2).run(tests).wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
