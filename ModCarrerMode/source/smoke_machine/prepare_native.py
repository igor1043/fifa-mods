"""Prepare shared launch sites without regenerating the maintained native runtime."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parent
shutil.copy2(root.parent/'stadium_pyrotechnics/presentation.h',root/'presentation.h')
assert (root/'smoke_machine.cpp').is_file()
assert (root/'launch_sites.h').read_bytes()==(root.parent/'stadium_pyrotechnics/launch_sites.h').read_bytes()
print('Prepared shared policy; maintained smoke-machine runtime preserved')
