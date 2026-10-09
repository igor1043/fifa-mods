# Tournament compatibility — experimental revision 3

This is a restricted recovery experiment, not a save-schema expansion.
It reads the current compobj root catalog and the installed 11-bit field metadata.
For a tournament load, it replaces the two runtime selection-cache integers only
when exactly one root has the saved low 11 bits. Club league is diagnostic only.
Collisions (including 63/2111 and 130/2178) are never resolved by guessing.
No DB, XML, compdata, user record or save is written by this DLL.

The original L9 worker still owns its complete 61-site/400-entry layout patch.
The plugin adapts its two incompatible descriptors and gates the load hook on
all 61 changes being present. Executable timestamp and instruction signatures
must match the supported captured build.

The captured creation count CALL at EXE+05ABC377 receives a null object for a
FAKEEVENT without children. A narrowly scoped replacement returns zero for
NULL, otherwise the original signed count at +20h, preserving flags. The 16-byte
aligned CALL region is exchanged atomically; surrounding bytes are preserved.

This does not restore every field truncated in a save, prove competition identity
across changed compdata, or guarantee that advancing a recovered tournament works.
Use with saves created against the current 11-bit schema and matching compdata.
Ambiguous roots retain original behavior and may still crash.

Build and isolated tests: run build_tournament_compat.cmd from this directory.
Tests execute the actual RX load relay and creation guard, reproduce the league
351 / stored 160 regression, refuse collisions, reject non-tournament records,
check unchanged user records, future IDs, and the 61-site layout gate.

Enable: tournament_compat_native\tournament_compat_native.dll in mods/enabled.txt.
Disable with FIFA closed: comment/remove only that entry.
Log: ModCarrerMode/logs/tournament_compat_native.log. Look for START plugin=3,
CREATION GUARD installed, READY version=3, and LOAD RECOVERED or LOAD UNCHANGED.

In-game test: create a new affected tournament, play/advance, save, exit the
whole game, restart, reopen the save, then play/advance and save/reopen again.
Compare with a tournament known to work. On 2026-10-09 the user reported
"acho que funcionou" after testing and authorized publishing this revision.
This is a preliminary positive report; detailed tournament/advance coverage
and ambiguous-root behavior have not been confirmed in game.
