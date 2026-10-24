"""Add Python's matching SQLite stdlib/extension, preserving other frozen modules."""
from pathlib import Path
import hashlib,importlib.util,json,marshal,struct,sys,zlib,argparse
import pefile
from PyInstaller.archive.readers import CArchiveReader
from PyInstaller.archive.writers import CArchiveWriter

def build(server,output):
    server=Path(server);output=Path(output);old=server.read_bytes();a=CArchiveReader(str(server))
    cookie=struct.unpack(CArchiveWriter._COOKIE_FORMAT,old[-CArchiveWriter._COOKIE_LENGTH:])
    if cookie[4]!=sys.version_info.major*100+sys.version_info.minor:raise ValueError('Python version must match Server16')
    pyd=Path(sys.base_prefix)/'DLLs/_sqlite3.pyd'
    dll=pefile.PE(data=a.extract('sqlite3.dll'));extension=pefile.PE(str(pyd))
    have={e.name for e in dll.DIRECTORY_ENTRY_EXPORT.symbols}
    need={e.name for t in extension.DIRECTORY_ENTRY_IMPORT if t.dll.lower()==b'sqlite3.dll' for e in t.imports}
    assert dll.FILE_HEADER.Machine==extension.FILE_HEADER.Machine==0x8664 and need<=have
    z=a.open_embedded_archive('PYZ.pyz');previous=a.extract('PYZ.pyz');assert previous[4:8]==importlib.util.MAGIC_NUMBER
    payload=bytearray(previous[:17]);toc=[]
    for name,(kind,offset,size) in z.toc.items():
        if name.startswith('sqlite3'):continue
        toc.append((name,(kind,len(payload),size)));payload.extend(previous[offset:offset+size])
    for name,filename,kind in (('sqlite3','__init__.py',1),('sqlite3.dbapi2','dbapi2.py',0),('sqlite3.dump','dump.py',0)):
        source=Path(sys.base_prefix)/'Lib/sqlite3'/filename
        chunk=zlib.compress(marshal.dumps(compile(source.read_bytes(),'sqlite3/'+filename,'exec')),6)
        toc.append((name,(kind,len(payload),len(chunk))));payload.extend(chunk)
    at=len(payload);payload.extend(marshal.dumps(toc));payload[8:12]=struct.pack('!i',at)
    packed=bytearray();members=[]
    for name,(offset,size,unpacked,compressed,kind) in a.toc.items():
        if name=='_sqlite3.pyd':continue
        chunk=old[a._start_offset+offset:a._start_offset+offset+size]
        if name=='PYZ.pyz':unpacked=len(payload);chunk=zlib.compress(payload,9) if compressed else payload
        members.append((len(packed),len(chunk),unpacked,compressed,kind,name));packed.extend(chunk)
    binary=pyd.read_bytes();chunk=zlib.compress(binary,9);members.append((len(packed),len(chunk),len(binary),1,'b','_sqlite3.pyd'));packed.extend(chunk)
    for option in a.options:members.append((0,0,0,0,'o',option))
    toc_data=CArchiveWriter._serialize_toc(members)
    tail=struct.pack(CArchiveWriter._COOKIE_FORMAT,cookie[0],len(packed)+len(toc_data)+CArchiveWriter._COOKIE_LENGTH,len(packed),len(toc_data),cookie[4],cookie[5])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(old[:a._start_offset]+packed+toc_data+tail)
    updated=CArchiveReader(str(output));newz=updated.open_embedded_archive('PYZ.pyz')
    for name in a.toc:
        if name not in ('PYZ.pyz','_sqlite3.pyd'):assert updated.extract(name)==a.extract(name),name
    for name in z.toc:
        if not name.startswith('sqlite3'):assert newz.extract(name)==z.extract(name),name
    report=dict(sha256=hashlib.sha256(output.read_bytes()).hexdigest(),preserved_members=len(a.toc)-1,preserved_modules=len(z.toc),sqlite_dll_unchanged=True)
    output.with_suffix('.sqlite.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--server',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();build(args.server,args.output)
