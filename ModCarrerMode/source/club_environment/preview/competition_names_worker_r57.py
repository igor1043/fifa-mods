import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from db_worker import _prefer_bundled_site_packages
_prefer_bundled_site_packages()
import clr
clr.AddReference(sys.argv[1])
from FifaLibrary import DbFile
db=DbFile(sys.argv[2],sys.argv[3])
if not db.Load():raise RuntimeError('Cannot read FIFA language database')
table=db.GetTable('LanguageStrings');result={}
for i in range(table.NValidRecords):
 row=table.Records[i];key=str(row.GetStringField('stringid'))
 if any(word in key.upper() for word in ('LEAGUE','COMPETITION','TOURNAMENT','COMPOBJ','COMP_','CUPNAME','TROPHYNAME')):result[key]=str(row.GetStringField('sourcetext'))
print(json.dumps(result,ensure_ascii=True))
