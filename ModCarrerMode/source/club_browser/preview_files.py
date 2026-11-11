"""Bounded sharing retries and immutable files for the native preview cache."""
from pathlib import Path
import os,time

def retry(operation):
    for attempt in range(8):
        try:return operation()
        except PermissionError:
            if attempt==7:raise
            time.sleep(min(.02*2**attempt,.2))

def read_bytes(path):return retry(Path(path).read_bytes)

def replace(source,target):return retry(lambda:os.replace(source,target))

def atomic(path,blob):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.'+os.urandom(12).hex()+'.new')
    try:
        temp.write_bytes(blob);replace(temp,path)
    finally:
        if temp.exists():retry(temp.unlink)

def store_immutable(path,blob):
    """Publish once without replacing an inode which FIFA may have open.

    Unsupported cache hardlinks return False: the caller can use a private
    copy instead. Other readers never see a partially written cache entry.
    """
    path=Path(path)
    if path.is_file():return True
    temp=path.with_name(path.name+'.'+os.urandom(12).hex()+'.new')
    try:
        temp.write_bytes(blob)
        # Windows rename is atomic and never replaces an existing target.
        # Unlike link-then-unlink, it leaves no extra alias needing DELETE
        # sharing after another process has opened the published file.
        try:
            if os.name=='nt':os.rename(temp,path)
            else:os.link(temp,path)
        except FileExistsError:return True
        except OSError:return path.is_file()
        return True
    finally:
        if temp.exists():retry(temp.unlink)

def publish_directory(source,target):
    """Reuse complete models and recover only empty, abandoned directories.

    Windows cannot rename a directory over an existing empty directory. A
    cleanup or an interrupted preparation can leave such a shell behind.
    Never recursively delete or replace a populated directory: FIFA may
    still have its files open, or another publisher may have just won.
    """
    source=Path(source);target=Path(target)
    def publish():
        for attempt in range(3):
            if (target/'assets.json').is_file():return
            if not (source/'assets.json').is_file():raise FileNotFoundError('Modelo preparado sem assets.json: '+str(source))
            try:os.rename(source,target);return
            except OSError as error:
                if (target/'assets.json').is_file():return
                if attempt==2 or target.is_symlink() or target.is_junction():raise
                try:target.rmdir()  # Empty only; a populated/racing target is preserved.
                except FileNotFoundError:continue
                except OSError:
                    if (target/'assets.json').is_file():return
                    raise error
    return retry(publish)
