import portable_paths as portable
"""Read selected compressed player names; never saves a database."""
import sys,json
from pathlib import Path
from db_worker import _prefer_bundled_site_packages
_prefer_bundled_site_packages()
import clr
clr.AddReference(sys.argv[1])
from FifaLibrary import DbFile
db=DbFile(sys.argv[2],sys.argv[3])
if not db.Load():raise RuntimeError('Unable to read name database')
wanted=set(json.loads(Path(sys.argv[4]).read_text(encoding='utf8')));result={}
table=db.GetTable('playernames')
for i in range(table.NValidRecords):
    row=table.Records[i];key=row.GetIntField('nameid')
    if key in wanted:result[str(key)]=str(row.GetStringField('name'))
print(json.dumps(result,ensure_ascii=True))
