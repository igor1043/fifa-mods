import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import build_preview as screen
from native_review_vm import open_native

class PreviewInputTests(unittest.TestCase):
    def test_left_stick_cycles_all_cards_and_right_stick_does_not(self):
        side=lambda team:dict(team_id=team,name='Clube',probable=True,formation='',players=[],portrait_ids=[],recent=[])
        payload=dict(available=True,pid=1,date=20260111,fixture=[1,0,0,20260111,1600,1,2,0,0,0,0],user=side(1),opponent=side(2),details={'stadium':'Estádio do mandante'})
        with tempfile.TemporaryDirectory() as folder,patch.object(screen,'HERE',Path(folder)):
            file=screen.build(payload);vm,view,apt,calls=open_native(file,screen.FULL)
            for symbol in ('Server16LineupPitch','Server16OpponentLineupPitch'):
                placements=apt.characters[apt.exports[symbol]].frames[0]
                header=next(p for p in placements if getattr(p,'name',None)=='teamHeader')
                self.assertEqual(header.matrix[4:],(screen.FIELD_X,0))
                self.assertEqual((header.matrix[0],header.matrix[3]),(screen.FIELD_W,screen.FIELD_Y))
            for name in ('userPitch','opponentPitch'):
                self.assertIsNotNone(view.get(name).get('p0'));self.assertIsNotNone(view.get(name).get('p10'))
            vm.invoke(view.get('WaitForPitchClips'),view);self.assertTrue(view.get('pitchClipsReady'))
            self.assertEqual(view.get('carouselPage'),0)
            for code,destination in ((14,1),(14,2),(14,0),(13,2),(13,1),(13,0)):
                vm.invoke(view.get('LocalEventHandler'),view,[code,True]);self.assertEqual(view.get('carouselPage'),destination)
            for right_stick in (5,6):
                vm.invoke(view.get('LocalEventHandler'),view,[right_stick,True]);self.assertEqual(view.get('carouselPage'),0)
            help_items=vm.invoke(view.get('getHelpContext'),view);self.assertEqual([c for c,t in help_items],['BACK','LAS_LR'])
            self.assertIn('INDISPON',view.get('opponentPitch').get('caption').get('text'))

if __name__=='__main__':unittest.main()
