# Dedicated career calendar DDS icons (version 3)

The calendar's competition images live in `data/ui/imgAssets/careerCompetitionIcons/c<ID_VISUAL>.dds`.
These DDSs, their local `index.tsv` and generated metadata are excluded from the source package.
The published mod retains the directory lookup, validation, ID availability and fallback rules.
The host's existing competition/stage resolution chooses the visual ID. This is not necessarily the
league ID or the raw career competition object ID. Official competition IDs are not remapped by
this module. `index.tsv` preserves the original host's ID availability through `host_available`:
1 accepts an initial ID; 0 avoids activating an old ambiguous alias which the host did not accept.
The module's `HasCompetition` export reads this availability from the new directory, allowing the
host's old DDS existence checks to fall back to the new catalogue without changing the ID order.
New IDs absent from the index are accepted when a valid dedicated DDS exists. Preseason identity
continues to use the guarded native competition registry.

`prepare_calendar_icons.py` copies the exact embedded DDS payload of each working `cmcomp_<ID>.big`.
It performs no resampling, recoloring or re-encoding. `index.tsv` records the source and DDS SHA-256.
The prepared images use DXT5/BC3, a 128x128 transparent canvas, and a proportional logo within the
upper-left 48x48 area. Center the logo within that 48x48 area, not within the whole canvas.

Guarded formatter adapters redirect `artAssets/cmCalendarCompetitions/cmcomp_<ID>.swf`/`.big`
and the legacy flat/light/dark DDS requests in the `cmCalendarCompetitions` namespace to the
dedicated DDS directory. There is no runtime league/light, league/dark or BIG scan
for these images. Existing images can be replaced directly; restart the game after changing DDSs.
Market/transfer events in `cmCalendar`, club crests, kit paths and the calendar screen stay unchanged.
Missing or malformed DDSs leave the original path untouched rather than redirecting to a broken file.
Existing BIGs remain as rollback/fallback resources, but successfully redirected icons do not use them.

The module preserves the installed version's goalkeeper-thumbnail alias compatibility and exports.
It requires FIFA 16 x64 timestamp `577DE45C`, the verified expanded-layout patches, and the original
formatter bytes. It refuses to overwrite other hooks. DLLs are pinned and activate on the next launch.

Preparation and installation from PowerShell:

```powershell
py -3 .\prepare_calendar_icons.py --source 'U:\fifa 16' --destination 'U:\fifa 16'
.\build.cmd
.\Install-Game.ps1 -GameDirectory 'U:\fifa 16'
```

`build.cmd` creates synthetic transparent DDSs in its ignored test fixture; no game images, league or BIG
resources are required. Tests cover ID bounds, bad/missing DDSs, path prefixes, unrelated UI paths,
formatter truncation, and native preseason identity. Installation backs up the previous module and
enabled list and provides `Restore-CalendarDds.ps1`. It installs only the module and preserves local DDSs
and their availability index. Without local icons the module keeps the original path. It does not replace `dinput8.dll`.

The runtime log `ModCarrerMode/logs/career_ui_assets.log` records `CATALOG`, `READY` and `RESOLVE`.
Actual calendar rendering must also be checked in the game; unit tests do not verify its display.

## Career Starting XI goalkeeper (14 October 2026)

StartingXIDP reads one SHARED team-kit selector at team-sheet offset `+8`.
The goalkeeper interprets `-1` as unsigned team `262143`; the outfield branch
already treats negative selectors as automatic team selection. The initial
repair incorrectly wrote `(TeamID << 14) | 2` into that shared field, making
all eleven players request the keeper kit. This regression was reported in-game.

The final repair normalizes only `UINT32_MAX` to ZERO in a local `0x2DC`-byte
sheet copy. Zero restores the native role-specific behavior: the keeper uses
kit type 2 and the ten outfield players use type 0 for the sheet's own TeamID.
It never writes the positive keeper key to the shared selector. Saved sheets,
valid existing overrides and all other fields remain unchanged.

`keeper_pitch_hook.inc` wraps only the StartingXIDP serializer call at native
RVA `40B59F2`, on x64 timestamp `577DE45C`, with exact live signatures checked
before installing. No DDS, APT or BIG replacement is needed.

`test_keeper_pitch_sheet.c` now executes the actual native x64 keeper and
outfield instruction sequences from `keeper_native_branches.h`. It reproduces
both the original invalid-team failure and the all-keepers regression, then
verifies all eleven rows for seven clubs with sentinel and automatic selectors.
The ten outfield results must match their original native results exactly.
The same tests compare all eleven outputs with the signed fallback branches
read directly from the user-opened mod backup (PID 38504).
The original source, valid keys, invalid teams and unrelated bytes are checked.
`build.cmd` runs these tests and the existing UI asset resolver tests.

The user-provided original and mod backups have matching executable hashes.
The current Starting XI bytecode matches both; pitch/player resources and
Flamengo's team/kit records match the mod backup, including keeper teamkitid
1692. The issue is the shared selector's runtime interpretation. The live backup
uses a signed <=0 fallback; the current expanded-ID path checks only zero.
Normalizing the sentinel restores the reference behavior for both roles.

The production module is `ModCarrerMode/mods/career_ui_assets/career_ui_assets.dll`.
Installation preserves the DLL's existing public exports and the calendar
resolver. A restart loads the corrected module; a process with restricted RAM
access cannot be updated live from this session. On 14 October 2026, the user
confirmed the final correction in-game. Earlier APT and native experiments are archived
in the study directory and are not included in the production build.

The international crowd change remains separate: a six-point bonus for type-1
confederations and the type-0 FIFA world node, preserving the 90-percent cap
and manual overrides. Domestic and preseason country nodes receive no bonus.
