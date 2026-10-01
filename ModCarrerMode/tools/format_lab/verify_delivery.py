"""Read-only QA of generated documentation and preservation of original studies."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('studies',type=Path)
    p.add_argument('baseline',type=Path)
    a=p.parse_args()
    changed, missing=[],[]
    with (a.baseline/'documents.jsonl').open(encoding='utf-8') as stream:
        records=[json.loads(line) for line in stream]
    for record in records:
        path=a.studies/record['path']
        if not path.exists():
            missing.append(record['path'])
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
            changed.append(record['path'])
    broken=[]
    pages=list((a.studies/'03_CATALOGO').glob('*.md'))+[Path(__file__).parent/'README.md']
    checked=0
    for page in pages:
        text=page.read_text(encoding='utf-8')
        for raw in re.findall(r'\]\(([^)]+)\)',text):
            target=unquote(raw.strip('<>').split('#')[0])
            if not target or re.match(r'^[a-zA-Z]+://',target):
                continue
            checked+=1
            if not (page.parent/target).exists():
                broken.append({'page':str(page),'target':target})
    allowed={'00_GUIA\\README.md','00_GUIA\\MAPA_DE_PASTAS.md'}
    unexpected=[name for name in changed if name not in allowed]
    result={'original_files_checked':len(records),'missing_originals':missing,
            'changed_originals':changed,'unexpected_changes':unexpected,
            'local_links_checked':checked,'broken_new_links':broken,
            'ok':not(missing or unexpected or broken)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['ok'] else 1


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
