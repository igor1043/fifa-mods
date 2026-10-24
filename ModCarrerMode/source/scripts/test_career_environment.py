"""Portable regression suite. Requires development Python with Pillow/NumPy.

Run from the repository: python -B ModCarrerMode/source/scripts/test_career_environment.py
Uses fake game memory for financial mutations; never writes the native save.
"""
import os,sys,unittest
from pathlib import Path
source=Path(__file__).resolve().parents[1];root=source.parents[1]
os.environ['SERVER16_GAME_ROOT']=str(root)
env=source/'club_environment'
sys.path[:0]=list(map(str,(source,env,env/'vendor',env/'bank',env/'preview',env/'room',source/'tests')))
names=['test_loan_startup','test_dual_loans','test_loan_reminders','test_loan_confirmation','test_loan_dates_delivery','test_loan_navigation','test_club_switch','test_save_sidecar','test_loan_statement','test_loan_applications','test_finance_live_ui','test_finance_r57','test_loan_notifications',
       'test_environment_navigation','test_preview_progression','test_preview_details','test_career_context_record',
       'test_room_safety_r53','test_room_material_install_r59','test_room_commands','test_room_visual_r62']
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
raise SystemExit(not result.wasSuccessful())
