FIFA 16 — seven substitutions, native rule pair scan

This DLL is loaded by the existing ModCarrerMode host through mods/enabled.txt.
It scans the FIFA process for one validated live pair of match-rule records,
then sets both A78C limits to 7. The B03C used-substitution counters are never
written. It has no fixed heap address and needs no external program at runtime.

The previous hook-only DLL loaded but recorded no hit in the failed fourth-
substitution test. This build therefore detects the validated pair directly,
including heap allocations below 4 GB. It writes once when a match pair is
found and rearms after the counters reset or the pair becomes dormant.

Source and build:
  ModCarrerMode/build/substitution_all7_rulescan_native_20260926/
Log after FIFA starts:
  ModCarrerMode/logs/substitution_all7_rulescan_native.log

The paired RAM write was verified again in PID 57632. The automated DLL still
requires a fresh-start match test. A successful load or log alone does not
establish that all seven substitutions work in gameplay.
