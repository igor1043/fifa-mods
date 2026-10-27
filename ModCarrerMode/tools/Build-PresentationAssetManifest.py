"""Inventory runtime presentation assets, without backups or local build metadata.

The complement is always verified against this committed inventory. Game paths
can be supplied to compare each source asset before publishing a release.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root, game=None):
    root = Path(root).resolve()
    tracked = {p.decode('utf8').casefold() for p in subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=root).split(b'\0') if p}
    base = root / 'data/sceneassets'
    groups = {}
    groups['mascots'] = sorted(p for p in (base/'mascot').glob('*/*')
        if p.parent.name.isdecimal() and p.name in
        {'model.rx3', 'model_animated.rx3', 'textures.rx3', 'locomotion_feet.bin'})
    groups['competition_presentations'] = sorted(p for p in
        (base/'entrance_props/competitions').glob('*/*')
        if p.name in {'asset.ini', 'model.rx3', 'template.rx3'})
    groups['replacement_ball_stands'] = sorted((base/'standball').rglob('*.rx3'))
    groups['pitchside_var_cabin'] = sorted((base/'var_cabin').glob('*.rx3'))
    groups['xi_neutral_lighting'] = sorted((base/'server16_club_xi/lighting').glob('*.rx3'))
    rows = []
    counts = {}
    for group, paths in groups.items():
        if not paths:
            raise ValueError('Missing asset group: '+group)
        counts[group] = 0
        for path in paths:
            relative = path.relative_to(root).as_posix()
            if relative.casefold() in tracked:
                continue
            size, sha = path.stat().st_size, digest(path)
            if game:
                installed = Path(game)/relative
                if not installed.is_file() or installed.stat().st_size != size or digest(installed) != sha:
                    raise ValueError('Development/game asset differs: '+relative)
            rows.append(dict(path=relative, bytes=size, sha256=sha, group=group))
            counts[group] += 1
    if len({r['path'].casefold() for r in rows}) != len(rows):
        raise ValueError('Duplicate presentation asset')
    return dict(schema=1, purpose='Static runtime assets complementing Git; no saves, caches or backups',
                groups=counts, files=rows)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument('--game', type=Path)
    a = p.parse_args()
    report = inventory(a.root, a.game)
    target = a.root/'ModCarrerMode/data/catalogs/presentation_assets.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.json.new')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    temporary.replace(target)
    print(json.dumps(dict(manifest=str(target), groups=report['groups'],
        files=len(report['files']), bytes=sum(r['bytes'] for r in report['files'])), indent=2))
