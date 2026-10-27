"""Export institutional RGB colors from an explicitly selected FIFA installation."""
from pathlib import Path
import argparse
import hashlib
import json

from fifa_db import FifaDatabase


def export_palettes(game, output):
    game, output = Path(game), Path(output)
    database = FifaDatabase(game)
    fields = ['teamid', 'teamname'] + [
        f'teamcolor{n}{c}' for n in (1, 2) for c in ('r', 'g', 'b')]
    rows = sorted(database.rows('teams', fields), key=lambda row: row['teamid'])
    palette = []
    for row in rows:
        colors = [[row[f'teamcolor{n}{c}'] for c in ('r', 'g', 'b')] for n in (1, 2)]
        if not isinstance(row['teamid'], int) or not 0 < row['teamid'] <= 1000000:
            raise ValueError(f"Invalid team ID: {row['teamid']}")
        if not all(isinstance(v, int) and 0 <= v <= 255 for rgb in colors for v in rgb):
            raise ValueError(f"Invalid team colors: {row['teamid']}")
        palette.append(dict(team=row['teamid'], name=row['teamname'],
                            primary=colors[0], secondary=colors[1]))
    if not palette or len({row['team'] for row in palette}) != len(palette):
        raise ValueError('Empty or duplicate team palette')
    lines = ['// Generated from the installed FIFA database; no per-frame database reads.',
             'static const TeamPalette teamPalettes[]={']
    for row in palette:
        lines.append('    {%d,{%s},{%s}},' % (
            row['team'], ','.join(map(str, row['primary'])), ','.join(map(str, row['secondary']))))
    lines.append('};')
    output.mkdir(parents=True, exist_ok=True)
    (output/'team_palettes.h').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    manifest = output/'build/team_palettes.json'
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(dict(
        database=str(game/'data/db/fifa_ng_db.db'),
        sha256=hashlib.sha256(database.data).hexdigest(), teams=palette),
        ensure_ascii=False, indent=2), encoding='utf-8')
    print('Exported two RGB colors for', len(palette), 'teams')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game_dir', type=Path, help='FIFA installation containing data/db and metadata')
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    export_palettes(args.game_dir, args.output_dir)
