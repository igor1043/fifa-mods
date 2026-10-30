import json,sqlite3,tempfile,unittest
from pathlib import Path
from coach_ranking import project

class CoachWeights(unittest.TestCase):
 def test_club_power_sample_volume_and_titles_all_contribute(self):
  with tempfile.TemporaryDirectory() as t:
   game=Path(t);folder=game/'ModCarrerMode/runtime/manager_market';folder.mkdir(parents=True)
   save=game/'DATA';save.write_bytes(b'unchanged');dbfile=game/'coaches.sqlite3'
   db=sqlite3.connect(dbfile)
   db.executescript('''
    CREATE TABLE branches(id TEXT,start_date INT,game_date INT,user_club INT);
    CREATE TABLE coaches(branch TEXT,coach_id TEXT,name TEXT,nationality TEXT,reputation REAL);
    CREATE TABLE clubs(branch TEXT,club_id INT,name TEXT,league_name TEXT,country TEXT);
    CREATE TABLE appointments(branch TEXT,coach_id TEXT,club_id INT,start_date INT,end_date INT);
    CREATE TABLE honours(branch TEXT,coach_id TEXT,game_date INT);
    CREATE TABLE results(branch TEXT,match_key TEXT,game_date INT,home INT,away INT,hg INT,ag INT,home_coach TEXT,away_coach TEXT);
   ''')
   db.execute("INSERT INTO branches VALUES('b',20260101,20261130,1)")
   for club in (1,2):db.execute('INSERT INTO clubs VALUES(?,?,?,?,?)',('b',club,str(club),'Liga','Brasil'))
   for name,club,games in [('Poucos',1,3),('Grande',1,50),('Menor',2,50),('Campeão',1,50)]:
    db.execute('INSERT INTO coaches VALUES(?,?,?,?,?)',('b',name,name,'Brasil',4))
    db.execute('INSERT INTO appointments VALUES(?,?,?,?,?)',('b',name,club,20260101,None))
    for i in range(games):
     db.execute('INSERT INTO results VALUES(?,?,?,?,?,?,?,?,?)',('b',name+str(i),20261001,club,99,2,0,name,'opponent'))
   db.execute("INSERT INTO honours VALUES('b','Campeão',20261001)")
   db.commit();db.close();before=dbfile.read_bytes()
   (folder/'state_ready.json').write_text(json.dumps(dict(pid=10,club=1,date=20261130,save=str(save),database=str(dbfile),branch='b')),encoding='utf8')
   rules=dict(years=4,coaches=dict(prior_games=24,performance_weight=1100,games_weight=36,title_bonus=40,title_cap=5,club_overall_weight=5,club_domestic_weight=8,club_international_weight=10))
   teams={1:dict(overall=80,domestic=20,international=15),2:dict(overall=60,domestic=5,international=1)}
   result=project(game,save,dict(club=1,date=20261130),pid=10,rules=rules,teams=teams)
   by_name={r['name']:r for r in result['rows']}
   self.assertEqual(len(by_name),4)
   self.assertGreater(by_name['Grande']['points'],by_name['Menor']['points'])
   self.assertGreater(by_name['Menor']['points'],by_name['Poucos']['points'])
   self.assertGreater(by_name['Campeão']['points'],by_name['Grande']['points'])
   self.assertEqual(by_name['Campeão']['titlePoints'],40)
   self.assertEqual(save.read_bytes(),b'unchanged');self.assertEqual(dbfile.read_bytes(),before)

if __name__=='__main__':unittest.main()
