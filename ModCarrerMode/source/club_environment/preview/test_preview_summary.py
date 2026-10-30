"""Real career results and native three-column layout contract."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from preview_details import head_to_head,stadium_location
import build_preview as screen
import preview_carousel as layout
from native_review_vm import open_native
from formats import Placement


class MatchSummaryTests(unittest.TestCase):
    @staticmethod
    def native_text(clip):
        # The APT test reader exposes C-string bytes as Latin-1. FIFA consumes
        # the emitted UTF-8; assert the actual decoded text, including accents.
        return clip.get('text').encode('latin1').decode('utf8')

    def test_head_to_head_uses_team_perspective_and_only_completed_meetings(self):
        fixtures=[[1,0,0,20260101,1600,10,20,2,1,1],
                  [2,0,0,20260102,1600,20,10,3,1,1],
                  [3,0,0,20260103,1600,20,10,1,1,1],
                  [4,0,0,20260104,1600,20,10,-1,-1,0],
                  [5,0,0,20260105,1600,10,30,9,0,1],
                  [6,0,0,20260110,1600,10,20,9,0,1],
                  [7,0,0,20260104,1600,10,20,-1,1,1]]
        fixtures.append(fixtures[0])
        self.assertEqual(head_to_head(fixtures,10,20,20260105),
                         dict(user_wins=1,draws=1,opponent_wins=1,games=3))
        self.assertEqual(head_to_head(fixtures,10,0,20260105)['games'],0)

    def test_location_is_only_shown_for_one_resolved_venue(self):
        with tempfile.TemporaryDirectory() as folder:
            game=Path(folder);(game/'FSW').mkdir();ini=game/'FSW/settings.ini'
            text='[stadium]\n10=A,5,3,0\n[scoreboardstdname]\nA=Arena - Alias - São Paulo - SP,1\n'
            ini.write_text(text,encoding='utf8')
            self.assertEqual(stadium_location(10,0,game),'São Paulo, SP')
            ini.write_text(text+'[comp]\n269=A,B,5,3,0\n',encoding='utf8')
            self.assertEqual(stadium_location(10,269,game),'')
            self.assertEqual(stadium_location(99,0,game),'')

    def payload(self):
        def side(ident):return dict(team_id=ident,name='Clube '+str(ident),probable=True,
            formation='4-4-2',players=[],portrait_ids=[],recent=[dict(opponent_id=3,opponent='Rival',
                date_text='01/01/2026',venue='Casa',result='V',score='2 – 1',competition_id=0)])
        return dict(available=True,pid=1,date=20260111,fixture=[1,0,0,20260111,1600,1,2,0,0,0,0],
            user=side(1),opponent=side(2),
            details=dict(competition_id=23,competition='Campeonato Carioca',date='11/01/2026',time='16:00',
                         stadium='Estádio do mandante',location='Rio de Janeiro, RJ'),
            head_to_head=dict(user_wins=3,draws=2,opponent_wins=1,games=6))

    def test_native_summary_binds_data_and_hides_when_changing_page(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(screen,'HERE',Path(folder)):
            file=screen.build(self.payload());vm,view,apt,calls=open_native(file,screen.FULL)
            vm.invoke(view.get('WaitForPitchClips'),view)
            center=view.get('lineupSummary')
            self.assertTrue(center.get('_visible'))
            title=[center.get(name).get('text') for name in ('competitionName','competitionLine1','competitionLine2') if center.get(name)]
            self.assertEqual(' '.join(title),'Campeonato Carioca')
            self.assertEqual(self.native_text(center.get('dateTime')),'11/01/2026 · 16:00')
            self.assertEqual(self.native_text(center.get('stadiumName')),'Estádio do mandante')
            self.assertEqual(center.get('h2hCount0').get('text'),'3')
            self.assertEqual(center.get('form0_0').get('text'),'V')
            self.assertIsNone(view.get('matchInfo'))
            self.assertIn('Rio de Janeiro, RJ',view.get('venuePage').get('stadiumLocation').get('text'))
            for page in (1,2,0):
                vm.invoke(view.get('ShowPage'),view,[page])
                self.assertEqual(center.get('_visible'),page==0)
                self.assertEqual(view.get('venuePage').get('_visible'),page==1)
            for symbol in ('Server16LineupPitch','Server16OpponentLineupPitch'):
                parts={p.name:p for p in apt.characters[apt.exports[symbol]].frames[0] if isinstance(p,Placement) and p.name}
                self.assertEqual(parts['teamHeader'].matrix[4:],(screen.FIELD_X,0))
                self.assertEqual(parts['teamHeader'].matrix[0],screen.FIELD_W)
                for i in range(11):
                    slot=parts['p'+str(i)]
                    self.assertGreaterEqual(slot.matrix[5],screen.FIELD_Y)
                    self.assertLessEqual(slot.matrix[5]+screen.HEAD_MAX+55,screen.PANEL_H)
            left=layout.PITCH_X[0]+(screen.FIELD_X+screen.FIELD_W)*layout.PITCH_SCALE
            right=layout.PITCH_X[1]+screen.FIELD_X*layout.PITCH_SCALE
            self.assertLess(left,layout.SUMMARY_X)
            self.assertLess(layout.SUMMARY_X+layout.SUMMARY_W,right)
            self.assertLessEqual(layout.PITCH_Y+screen.PANEL_H*layout.PITCH_SCALE,layout.CONTENT_BOTTOM)

    def test_absent_results_and_no_fixture_do_not_show_fabricated_statistics(self):
        data=self.payload();data['available']=False;data.pop('head_to_head')
        data['user']['recent']=[];data['opponent']['recent']=[]
        with tempfile.TemporaryDirectory() as folder,patch.object(screen,'HERE',Path(folder)):
            file=screen.build(data);vm,view,apt,calls=open_native(file,screen.FULL)
            vm.invoke(view.get('WaitForPitchClips'),view)
            self.assertFalse(view.get('lineupSummary').get('_visible'))
            self.assertEqual(self.native_text(view.get('lineupSummary').get('h2hCount0')),'—')
            self.assertEqual(self.native_text(view.get('lineupSummary').get('formEmpty0')),'Sem jogos concluídos')


if __name__=='__main__':unittest.main(verbosity=2)
