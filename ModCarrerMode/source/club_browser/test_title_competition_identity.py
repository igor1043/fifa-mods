"""Keep actual draw phases when an unsaved season resolves reserved slots."""
import struct,unittest
from competition_schedule import read_schedule
from title_evidence import merge_scores,completed_titles


def reserved_final(asset=1003):
    def node(index,ident,kind,parent,key='',name=''):
        row=bytearray(47);struct.pack_into('<HBHB',row,0,index,1,ident,kind)
        row[6:6+len(key)]=key.encode();row[12:12+len(name)]=name.encode()
        struct.pack_into('<h',row,45,parent);return row
    nodes=[node(0,0,0,-1,name='FIFA'),node(1,10,3,0,key='C'+str(asset),name='TrophyName_Abbr15_'+str(asset)),
           node(2,11,4,10,name='FCE_Setup_Stage'),node(3,12,4,10,name='FCE_Final'),node(4,13,5,12)]
    fixture=bytearray(21);struct.pack_into('<HBH',fixture,0,0,1,10)
    struct.pack_into('<IHH',fixture,6,20261017,1600,0);struct.pack_into('<H',fixture,16,1)
    fixture[14]=fixture[18]=255
    standings=[]
    for index in (0,1):
        row=bytearray(21);struct.pack_into('<HBHi',row,0,index,1,13,-1);standings.append(row)
    return b''.join(nodes)+bytes(10)+fixture+bytes(12)+bytes(20)+bytes(10)+bytes(14)+b''.join(standings)


class CompetitionIdentity(unittest.TestCase):
    def test_reserved_final_preserves_phase_but_is_never_a_won_title(self):
        raw=reserved_final();self.assertEqual([],read_schedule(raw))
        rows=read_schedule(raw,{12:dict(kind=10)},include_unresolved=True)
        self.assertEqual((10,1003,12,10),(rows[0]['root'],rows[0]['asset'],rows[0]['stage'],rows[0]['stageKind']))
        self.assertTrue(rows[0]['schedule_template']);self.assertFalse(rows[0]['played'])
        self.assertEqual([],completed_titles(rows,{12:dict(mode='KO1LEG')},{},20261230,20260101,str))

    def snapshot(self,asset=1003,date=20261017,root=10):
        return dict(nodes=[[root,0,3,asset,0],[12,root,4,-1,10]],
                    fixtures=[[0,root,root,date,1600,1043,567,2,0,1,1]])

    def test_unsaved_draw_and_score_keep_the_exact_competition_final(self):
        for asset in (1003,1007,1009,9,28,224):
            with self.subTest(asset=asset):
                saved=read_schedule(reserved_final(asset),include_unresolved=True)
                rows=merge_scores(saved,self.snapshot(asset),20260101)
                won=completed_titles(rows,{12:dict(kind=10,mode='KO1LEG')},{},20261230,20260101,str)
                self.assertEqual([(asset,1043,20261017)],[(t['competition'],t['club'],t['date']) for t in won])

    def test_template_is_not_lent_to_another_competition_or_reused_year(self):
        saved=read_schedule(reserved_final(),include_unresolved=True)
        for snap in (self.snapshot(asset=1007),self.snapshot(root=40),self.snapshot(date=20271017)):
            rows=merge_scores(saved,snap,20260101)
            self.assertEqual([],completed_titles(rows,{12:dict(mode='KO1LEG')},{},20271230,20260101,str))

    def test_installed_final_format_resolves_an_unlabelled_live_stage(self):
        snap=self.snapshot();snap['nodes'][1][4]=0;snap['fixtures'][0][2]=12
        rows=merge_scores([],snap,20260101)
        won=completed_titles(rows,{12:dict(kind=10,mode='KO1LEG')},{},20261230,20260101,str)
        self.assertEqual([1003],[t['competition'] for t in won])


if __name__=='__main__':unittest.main()
