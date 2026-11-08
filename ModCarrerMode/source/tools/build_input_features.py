"""Build the two native feature switches without replacing unrelated Server16 code."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
from PyInstaller.archive.readers import CArchiveReader
from PyInstaller.archive.writers import CArchiveWriter
from build_frontend_server_update import build as build_python

MODULES=('server16_py','server16_py.app','server16_py.match_hub_panel',
         'server16_py.locales_data','server16_py.native_feature_switch','server16_py.ultrawide_background',
         'server16_py.frontend_stadium_panel','server16_py.match_settings_panel','server16_py.stadium_selector')

def build(server, overlay, output, preserve_offsets=False, native_only=False):
    server,overlay,output=map(lambda p:Path(p).resolve(),(server,overlay,output))
    if server==output:raise ValueError('Build to a separate file.')
    with tempfile.TemporaryDirectory(prefix='server16_features_') as directory:
        intermediate=Path(directory)/'Server16Python.exe'
        modules=('server16_py',) if native_only else MODULES
        python_report=build_python(server,intermediate,modules,allow_new=True,preserve_offsets=preserve_offsets)
        archive=CArchiveReader(str(intermediate));raw=intermediate.read_bytes()
        writer=CArchiveWriter.__new__(CArchiveWriter);payload=io.BytesIO();toc=[];replacements=[]
        for name,(offset,length,size,compressed,kind) in archive.toc.items():
            if name.replace('\\','/')=='bin/cgfs16_overlay.dll':
                entry=writer._write_blob(payload,overlay.read_bytes(),name,kind,bool(compressed));replacements.append(name)
            else:
                entry=(payload.tell(),length,size,compressed,kind,name)
                payload.write(raw[archive._start_offset+offset:archive._start_offset+offset+length])
            toc.append(entry)
        if len(replacements)!=1:raise ValueError('Expected one embedded overlay resource.')
        for option in archive.options:toc.append((0,0,0,0,'o',option))
        position=payload.tell();table=writer._serialize_toc(toc);payload.write(table)
        cookie=list(struct.unpack(writer._COOKIE_FORMAT,raw[-writer._COOKIE_LENGTH:]));cookie[1:4]=[position+len(table)+writer._COOKIE_LENGTH,position,len(table)]
        payload.write(struct.pack(writer._COOKIE_FORMAT,*cookie))
        output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(raw[:archive._start_offset]+payload.getvalue())
        updated=CArchiveReader(str(output))
        assert archive.toc.keys()==updated.toc.keys() and archive.options==updated.options
        for name in archive.toc:
            assert updated.extract(name)==(overlay.read_bytes() if name in replacements else archive.extract(name)),name
        if preserve_offsets:
            original=CArchiveReader(str(server))
            assert original._start_offset==updated._start_offset
            assert original.toc['PYZ.pyz'][0]==updated.toc['PYZ.pyz'][0]
            previous=original.extract('PYZ.pyz');current=updated.extract('PYZ.pyz')
            assert previous[12:]==current[12:len(previous)]
    report={'output':str(output),'version':'0.2.25','bytes':output.stat().st_size,
            'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'overlay_sha256':hashlib.sha256(overlay.read_bytes()).hexdigest(),
            'python_modules':python_report['modules'],'preserved_python_modules':python_report['preserved_python_modules'],
            'preserved_resources':len(updated.toc)-2,'live_import_offsets_preserved':bool(preserve_offsets)}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2));return report
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server',required=True,type=Path);parser.add_argument('--overlay',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--live',action='store_true',help='Preserve cached imports used by existing FIFA reader workers.')
    parser.add_argument('--native-only',action='store_true',help='Update only the native overlay and release version; preserve all other frozen Python modules.')
    args=parser.parse_args();build(args.server,args.overlay,args.output,preserve_offsets=args.live,native_only=args.native_only)
