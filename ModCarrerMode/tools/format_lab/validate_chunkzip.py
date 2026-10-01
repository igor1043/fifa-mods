"""Small offline validation of one observed chunkzip dialect and .seq recovery."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from fifa_formats import (chunkzip_decode_single, chunkzip_encode_single, identify,
                          outside_input, sha, unpack_big_bytes)
from validate_assets import read_member


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path)
    p.add_argument('inventory',type=Path)
    p.add_argument('validation',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    outside_input(a.inventory,a.output,a.root)
    a.output.mkdir(parents=True)
    samples=json.loads((a.inventory/'samples.json').read_text(encoding='utf-8'))['chunkzip']
    sequences=json.loads((a.validation/'validation.json').read_text(encoding='utf-8'))['sequence_candidates']
    tests=[]
    for row in samples+sequences:
        result={'path':row['path'],'members':row['members']}
        try:
            data=read_member(a.root,row)
            plain=chunkzip_decode_single(data)
            repacked=chunkzip_encode_single(plain)
            if chunkzip_decode_single(repacked)!=plain:
                raise ValueError('codec roundtrip failed')
            result.update(decoded_size=len(plain),decoded_sha256=sha(plain),
                          decoded_format=identify(plain[:8192]),roundtrip_equal=True)
            if row in sequences:
                (a.output/'skillmoveai.original.chunkzip').write_bytes(data)
                (a.output/'skillmoveai.decoded.big').write_bytes(plain)
                (a.output/'skillmoveai.reencoded.EXPERIMENTAL.chunkzip').write_bytes(repacked)
                info, entries=unpack_big_bytes(plain)
                target=a.output/'skillmoveai_entries'
                target.mkdir()
                records=[]
                for index,(name,payload) in enumerate(entries):
                    filename=f'{index:06d}.payload'
                    (target/filename).write_bytes(payload)
                    records.append({'index':index,'name':name,'file':filename,'size':len(payload),
                                    'format':identify(payload[:8192]),'sha256':sha(payload)})
                (target/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
                seq=[r for r in records if r['name'].lower().endswith('.seq')]
                result.update(inner_entries=len(records),seq_count=len(seq),seq_bytes=sum(r['size'] for r in seq),
                              inner_formats=dict(Counter(r['format'] for r in records)),
                              seq_semantics_decoded=False)
            result['source_unchanged']=sha(read_member(a.root,row))==sha(data)
        except Exception as error:
            result['error']=str(error)
        tests.append(result)
    result={'tests':tests,'scope':'observed single-block dialect only; not universal chunkzip',
            'game_files_written':False,'game_acceptance_tested':False}
    (a.output/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
