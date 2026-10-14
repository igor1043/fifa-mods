"""Prepare the current unversioned assets and palette; preserve runtime source."""
from pathlib import Path
import runpy,shutil
root=Path(__file__).resolve().parent
shutil.copy2(root.parent/'smoke_machine/launch_sites.h',root/'launch_sites.h')
runpy.run_path(str(root/'export_palettes.py'))
destination=root/'build/assets';destination.mkdir(parents=True,exist_ok=True)
for name in ('stadium_pyrotechnics_0.lnx','stadium_pyrotechnics_0.rx3'):
    shutil.copy2(root/'assets'/name,destination/name)
print('Prepared Stadium Pyrotechnics assets for any home team; current runtime preserved')
