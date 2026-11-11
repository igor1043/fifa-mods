import copy,io,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image,ImageDraw
from . import data,assets


class TrophyGroupingTests(unittest.TestCase):
    def rows(self,n):
        return [dict(competition=7,root=40+i,club=1043 if i%2 else 2,date=(2020+i)*10000+1101,year=2020+i,name='Liga',origin='career') for i in range(n)]

    def test_threshold_two_individual_three_grouped_and_no_source_mutation(self):
        rows=self.rows(3);before=copy.deepcopy(rows)
        two=data.grouped_titles(rows[:2]);three=data.grouped_titles(rows)
        self.assertEqual([r['title_count'] for r in two],[1,1])
        self.assertEqual(len(three),1);self.assertEqual(three[0]['title_count'],3)
        self.assertEqual([r['year'] for r in three[0]['wins']],[2022,2021,2020])
        self.assertEqual({r['club'] for r in three[0]['wins']},{1043,2});self.assertEqual(rows,before)

    def test_different_competitions_and_demo_do_not_merge(self):
        rows=self.rows(3)+[dict(self.rows(1)[0],competition=229),dict(self.rows(1)[0],origin='preview')]
        result=data.grouped_titles(rows)
        self.assertEqual(len(result),3);self.assertEqual(sum(r['title_count'] for r in result),5)

    def test_thumbnail_centres_visible_cup_not_dds_padding_and_is_cached(self):
        source=Image.new('RGBA',(256,256));ImageDraw.Draw(source).rectangle((170,20,215,210),fill='gold')
        stream=io.BytesIO();source.save(stream,format='PNG')
        import portable_paths
        with tempfile.TemporaryDirectory() as tmp,patch.object(portable_paths,'read_asset',return_value=stream.getvalue()):
            relative=assets.trophy_thumbnail(tmp,7);path=Path(tmp)/relative
            image=Image.open(path);box=image.getbbox();self.assertAlmostEqual((box[0]+box[2])/2,128,delta=1);self.assertAlmostEqual((box[1]+box[3])/2,128,delta=1)
            stamp=path.stat().st_mtime_ns;self.assertEqual(assets.trophy_thumbnail(tmp,7),relative);self.assertEqual(path.stat().st_mtime_ns,stamp)


if __name__=='__main__':unittest.main()
