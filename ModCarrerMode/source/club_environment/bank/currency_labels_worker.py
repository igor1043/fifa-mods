"""Read only the three currency labels of the installed language database (x86)."""
import json,sys
from pathlib import Path
game=Path(sys.argv[2]).resolve().parents[2]
sys.path[:0]=[str(game/'ModCarrerMode/runtime/club_environment/preview'),str(game/'ModCarrerMode/source/server16_py')]
from db_worker import _prefer_bundled_site_packages
_prefer_bundled_site_packages()
import clr
clr.AddReference(sys.argv[1])
from FifaLibrary import DbFile
db=DbFile(sys.argv[2],sys.argv[3])
if not db.Load():raise RuntimeError('Cannot read currency labels')
table=db.GetTable('LanguageStrings');names={}
for i in range(table.NValidRecords):
 row=table.Records[i];key=str(row.GetStringField('stringid'))
 if key in ('CM_DollarCurrency','CM_EuroCurrency','CM_PoundsCurrency'):
  names[key]=str(row.GetStringField('sourcetext'))
print(json.dumps(names,ensure_ascii=True))
