from pathlib import Path
from types import SimpleNamespace
import sqlite3,tempfile,unittest
from catalog_meta import Labels,populate

class DisplayMetadataTest(unittest.TestCase):
 def test_browser_country_groups_override_pseudo_fifa_countries(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);catalog=root/'catalog.sqlite3';browser=root/'browser.tsv'
   browser.write_text('\t'.join(map(str,[0,'Brasil',54,30,0,2,'Federação Piauiense',4,0,1,'Clube','Cidade',0,0,1,1,1,1])),encoding='utf8')
   tables=dict(nations=[dict(nationid=54,nationname='Brazil'),dict(nationid=223,nationname='Brasil Nordeste 2')],leagues=[dict(leagueid=2,leaguename='Federação Piauiense',countryid=223,level=4),dict(leagueid=900,leaguename='Nova liga',countryid=54,level=3)])
   populate(catalog,SimpleNamespace(rows=lambda table,fields:tables[table]),browser);labels=Labels(catalog)
   self.assertEqual(54,labels.leagues[2]['country_id']);self.assertEqual(54,labels.leagues[900]['country_id']);self.assertEqual(('Brasil','flag_54'),labels.nationality('Brasil Nordeste 2'));self.assertEqual(('Reino Unido','flag_uk'),labels.nationality('Reino Unido'));self.assertEqual(('Não informada','flag_0'),labels.nationality(''))

if __name__=='__main__':unittest.main()
