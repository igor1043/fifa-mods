"""Read-only audit of preparation/deployment against the backed-up working base."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re
import struct
import sys
import pefile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'format_lab'))
import fifa_formats as formats

def sha(blob):
    return hashlib.sha256(blob).hexdigest()

def resource(raw, identifier):
    pe = pefile.PE(data=raw)
    for kind in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if kind.id == 10:
            for name in kind.directory.entries:
                if name.id == identifier:
                    entry = name.directory.entries[0].data.struct
                    return pe.get_data(entry.OffsetToData, entry.Size)
    raise ValueError(f'Missing RCDATA {identifier}')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--installed', action='store_true')
    args = parser.parse_args()
    repo, game, backup = args.repo, args.game, args.backup
    baseline = json.loads((backup / 'working-baseline.json').read_text(encoding='utf-8-sig'))
    for item in baseline:
        if sha((backup / item['area'] / item['path']).read_bytes()) != item['sha256']:
            raise ValueError(f'Backup mismatch {item["path"]}')
    source = repo / 'ModCarrerMode/source/career_native'
    old = (backup / 'dev-working/dinput8.dll').read_bytes()
    new = (repo / 'dinput8.dll').read_bytes()
    original_resource = (source / 'resources/active_chain_resource.bin').read_bytes()
    assert resource(old, 101) == resource(new, 101) == original_resource
    payload = (source / 'resources/swiss_delta_resource.bin').read_bytes()
    assert resource(new, 102) == payload and not payload.startswith(b'MZ')
    native_manifest = json.loads((repo / 'ModCarrerMode/docs/swiss-native-resource.json').read_text())
    assert sha(payload) == native_manifest['payload_sha256']
    assert len(native_manifest['selected_functions']) == 18
    forbidden = {0x20A0,0x24C0,0x6D80,0xA4B0,0xD760}
    assert not forbidden & {f['begin'] for f in native_manifest['selected_functions']}
    exports = lambda raw: sorted((e.name, e.ordinal) for e in pefile.PE(data=raw).DIRECTORY_ENTRY_EXPORT.symbols)
    assert exports(old) == exports(new)
    wrapper = source / 'src/host/dinput8_wrapper.c'
    old_wrapper = backup / 'dev-working/ModCarrerMode/source/career_native/src/host/dinput8_wrapper.c'
    normalize = lambda blob: blob.replace(b'\r\n',b'\n')
    reduced = normalize(wrapper.read_bytes()).replace(b'#include "swiss_delta.h"\n',b'').replace(
        b'    if (SUCCEEDED(result)) (void)swiss_delta_start(g_self,g_game_dir,g_mod_dir);\n',b'')
    assert reduced == normalize(old_wrapper.read_bytes())
    old_ini = (backup / 'dev-working/dinput8_L9.ini').read_bytes()
    new_ini = (repo / 'dinput8_L9.ini').read_bytes()
    assert new_ini.startswith(old_ini.replace(b'Basis=350000',b'Basis=460000'))
    ini_sections = re.findall(rb'(?m)^\[([^]]+)\]', new_ini)
    assert len(set(ini_sections)) == len(ini_sections)
    old_winmm = (backup / 'dev-working/winmm.dll').read_bytes()
    new_winmm = (repo / 'winmm.dll').read_bytes()
    winmm_differences = [i for i,(a,b) in enumerate(zip(old_winmm,new_winmm)) if a!=b]
    assert len(new_winmm) == len(old_winmm) and winmm_differences == [0xEC60,0xEC61]
    undone = bytearray(new_winmm)
    struct.pack_into('<I',undone,0xEC60,7000)
    assert bytes(undone) == old_winmm
    old_memory = (backup / 'game-working/memoryfw.ini').read_bytes()
    new_memory = (game / 'memoryfw.ini' if args.installed else repo / 'ModCarrerMode/assets/swiss/memoryfw.ini').read_bytes()
    decode = lambda blob: formats.refpack_decode(blob) if blob.startswith(b'\x10\xfb') else blob
    expected_memory, replaced = re.subn(rb'(?m)^(AddAllocator[ \t]+SaveLoadPP[ \t]+PPMallocMutex[ \t]+\[[ \t]*size=)14([Mm])',
        lambda match: match[1]+b'24'+match[2], decode(old_memory))
    assert replaced == 1 and decode(new_memory) == expected_memory
    assert old_memory != new_memory
    assets = json.loads((repo / 'ModCarrerMode/docs/swiss-assets-manifest.json').read_text())
    counts = collections.Counter(row['action'] for row in assets)
    assert counts == {'added':693,'preserved-identical':118,'preserved-original':40}
    for row in assets:
        path = Path(row['path'])
        if row['action'] == 'added':
            assert sha((repo / path).read_bytes()) == row['delivery_sha256']
            if args.installed:
                assert sha((game / path).read_bytes()) == row['delivery_sha256']
        else:
            assert sha((game / path).read_bytes()) == row['base_sha256']
            assert not (repo / path).exists()
    unchanged = []
    for relative in ('FIFA16.exe','data/db/fifa_ng_db.db','data/db/fifa_ng_db-meta.xml',
                     'dinput8_orig.dll','dinput8_patch.ini','Server16Python.exe',
                     'ModCarrerMode/retirement_offline_worker.exe','ModCarrerMode/mods/enabled.txt'):
        before_path = backup / 'game-working' / relative
        if not before_path.exists():
            before_path = backup / 'dev-working' / relative
        before = before_path.read_bytes()
        current = (game / relative).read_bytes()
        assert before == current, f'Original changed: {relative}'
        unchanged.append({'path':relative,'sha256':sha(current)})
    descriptors = json.loads((repo / 'ModCarrerMode/docs/swiss-byte-patches.json').read_text())
    assert len(descriptors) == 52
    for i, a in enumerate(descriptors):
        for b in descriptors[i+1:]:
            assert max(a['rva'],b['rva']) >= min(a['rva']+a['length'],b['rva']+b['length'])
    if args.installed:
        for relative in ('dinput8.dll','dinput8_L9.ini','winmm.dll'):
            assert (repo / relative).read_bytes() == (game / relative).read_bytes()
        assert (game / 'dinput8_l9_chain.dll').read_bytes() == original_resource
    result = {'stage':'installed' if args.installed else 'prepared',
        'backup_files_verified':len(baseline),'original_l965_sha256':sha(original_resource),
        'host_sha256':sha(new),'selected_functions':18,'selected_code_bytes':native_manifest['code_bytes'],
        'reconstructed_c_byte_sites':52,'original_wrapper_only_include_and_post_input_call':True,
        'exports_preserved':True,'asset_counts':dict(counts),'winmm_byte_offsets':winmm_differences,
        'memory_byte_differences':sum(a!=b for a,b in zip(old_memory,new_memory)),
        'memory_before_size':len(old_memory),'memory_after_size':len(new_memory),
        'memory_decoded_only_saveload_changed':True,'unchanged_game_files':unchanged,
        'game_runtime_tested':False}
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='unchanged_game_files'}))

if __name__ == '__main__':
    main()
