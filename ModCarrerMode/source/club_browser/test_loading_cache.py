"""Real-save/asset cache regression; no game process is attached or modified."""
from pathlib import Path
import hashlib,json,os,sys,tempfile,time
from unittest.mock import patch
from lineup_data import project,ProjectionCache
from native_assets import convert


def run(game,save,case):
    game,save,case=map(Path,(game,save,case))
    os.environ['SERVER16_GAME_ROOT']=str(game)
    sys.path[:0]=[str(game/'ModCarrerMode/source'),str(game/'ModCarrerMode/source/club_environment')]
    import portable_paths
    before=hashlib.sha256(save.read_bytes()).hexdigest();cache=ProjectionCache();times=[]
    for club in (1035,1043,567,1629,1035):
        start=time.perf_counter();result=project(game,save,club,cache);ms=(time.perf_counter()-start)*1000
        assert result==project(game,save,club),'Cached roster differs from the save'
        times.append(dict(club=club,ms=round(ms,2)))
    with patch('lineup_data.FifaDatabase',side_effect=AssertionError('Unchanged save parsed again')):
        assert project(game,save,1043,cache)['club']==1043
    with tempfile.TemporaryDirectory(prefix='xi-cache-') as temporary:
        root=Path(temporary);copy=root/'DATA';copy.write_bytes(save.read_bytes());cache=ProjectionCache()
        expected=project(game,copy,1035,cache);old=cache.dbs
        stat=copy.stat();os.utime(copy,ns=(stat.st_atime_ns,stat.st_mtime_ns+2_000_000_000))
        assert project(game,copy,1035,cache)==expected and cache.dbs is not old
        measurements=[]
        for label in ('cold','warm'):
            output=root/label;start=time.perf_counter();convert(case/'model.ff3d',output,portable_paths.read_asset,root/'materials')
            measurements.append(dict(stage=label,ms=round((time.perf_counter()-start)*1000,2)))
            for p in (case/'assets-before').iterdir():assert p.read_bytes()==(output/p.name).read_bytes(),p.name
        damaged=next((root/'materials').glob('*.rx3'));damaged.write_bytes(b'RX3l')
        repaired=root/'repaired';convert(case/'model.ff3d',repaired,portable_paths.read_asset,root/'materials')
        for p in (case/'assets-before').iterdir():assert p.read_bytes()==(repaired/p.name).read_bytes()
    assert hashlib.sha256(save.read_bytes()).hexdigest()==before
    report=dict(projection=times,materials=measurements,original_assets_byte_identical=True,save_unchanged=True)
    (case/'cache_test.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))
    print('PASS real XI: cached/uncached rosters match; save revision invalidates cache; corrupt material rebuilt; correct material bytes unchanged; save unchanged')


if __name__=='__main__':run(*sys.argv[1:])
