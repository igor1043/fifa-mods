"""Prepare published assets; refresh the palette only for an explicit game path."""
from pathlib import Path
import argparse
import shutil
from export_palettes import export_palettes

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--game-dir',type=Path,help='Regenerate colors from this FIFA database; otherwise keep the published palette')
args=parser.parse_args()
root=Path(__file__).resolve().parent
if args.game_dir:
    export_palettes(args.game_dir,root)
elif not (root/'team_palettes.h').is_file():
    raise FileNotFoundError('Published team_palettes.h is missing; restore it or supply --game-dir')
shutil.copy2(root.parent/'smoke_machine/launch_sites.h',root/'launch_sites.h')
destination=root/'build/assets';destination.mkdir(parents=True,exist_ok=True)
for name in ('stadium_pyrotechnics_0.lnx','stadium_pyrotechnics_0.rx3'):
    shutil.copy2(root/'assets'/name,destination/name)
print('Prepared Stadium Pyrotechnics assets for any home team; current runtime preserved')
