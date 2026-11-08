"""Validate the editable manager registry against the game's original SLC files.

This packaging helper never copies or rewrites manager models. The FIFA SLC
assets stay in their native directory and are selected by their source IDs.
"""
from pathlib import Path
import argparse
import shutil

try:
    from .coach_registry import load
except ImportError:
    from coach_registry import load


def prepare(game, output):
    game = Path(game).resolve()
    output = Path(output).resolve()
    if output == game or game in output.parents or (output.exists() and any(output.iterdir())):
        raise ValueError('Use an empty staging directory outside the game')
    registry = game / 'ModCarrerMode/data/manager_market/manager_registry.ini'
    entries = load(registry)
    if not entries:
        raise ValueError('The manager registry is missing or invalid')
    for coach in entries.values():
        if not coach['model_enabled']:
            continue
        slc_id = coach['source_slc_club_id']
        if not 0 < slc_id <= 200000:
            raise ValueError('Invalid source SLC ID for ' + coach['name'])
        for weather in (0, 1):
            for suffix in ('', '_textures'):
                source = game / f'data/sceneassets/slc/specificmanager_{slc_id}_0_{weather}{suffix}.rx3'
                with source.open('rb') as stream:
                    if source.stat().st_size < 32 or stream.read(4) not in (b'RX3l', b'RX3b'):
                        raise ValueError('Invalid native SLC model: ' + str(source))
    target = output / 'ModCarrerMode/data/manager_market/manager_registry.ini'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(registry, target)
    return sum(bool(row['model_enabled']) for row in entries.values())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print('Validated coaches using original SLC files:', prepare(args.game, args.output))
