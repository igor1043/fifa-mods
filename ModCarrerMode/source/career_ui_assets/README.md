# Dedicated career calendar DDS icons (version 3)

## Automatic artwork import (Server16)

Users can place PNG/JPG/WEBP/BMP artwork directly in `data/ui/imgAssets/careerCompetitionIcons/`
and open the updated Server16 before FIFA. Name the file after the installed competition ID
(for example `1761.png` in the Honduras base) or its full FSW movies/Scoreboard name. Server16 generates
`COMPETICOES.txt` in that directory with accepted filenames for the selected installation.
It converts to the validated 128x128 DXT5 canvas, preserves the original, resolves the visual ID
with the host's explicit-map/TrophyName/C<ID> precedence, and updates `host_available`
internally for that visual only. Users do not edit `index.tsv` or the mapping table.
Ambiguous/unknown names, duplicate sources for one visual ID and invalid artwork are skipped
and explained in Server16 Logs. Backups live in `runtime/backups/career_competition_icons/`.
Import runs only with FIFA closed; the launch button flushes pending images before starting FIFA.
This imports artwork for installed competitions; it does not create competition structures.
The native DDS lookup and its index remain compatible with manual/prebuilt asset packages.

## Native catalogue

The Honduras update resolves explicit artwork mappings by the installed CompData's
exact name/display identity. The internal map now has four pipe-separated fields:
numeric hint, visual ID, CompData name and display. Numeric hints never override a
different installed identity. Legacy two-field maps are accepted only when the
installed root confirms the same visual ID. Both Server16 and the native host use
this rule; the user-facing image import requires no table editing.

The calendar's competition images live in `data/ui/imgAssets/careerCompetitionIcons/c<ID_VISUAL>.dds`.
These DDSs, their local `index.tsv` and generated metadata are excluded from the source package.
The published mod retains the directory lookup, validation, ID availability and fallback rules.
The host's existing competition/stage resolution chooses the visual ID. This is not necessarily the
league ID or the raw career competition object ID. Official competition IDs are not remapped by
this module. `index.tsv` preserves the original host's ID availability through `host_available`:
1 accepts an initial ID; 0 avoids activating an old ambiguous alias which the host did not accept.
The module's `HasCompetition` export reads this availability from the new directory, allowing the
host's old DDS existence checks to fall back to the new catalogue without changing the ID order.
The installed index must explicitly allow the visual IDs referenced by
`ModCarrerMode/data/catalogs/career_competition_icon_map.tsv`. Legacy indices can mark these
as unavailable even when their DDS exists, causing a fallback to an outdated competition alias.
When importing new league artwork, rebuild the dedicated calendar images and set
`host_available=1` for the mapped visual IDs, leaving unrelated availability entries intact.
Use the supplied dark variant for the calendar when available; common light/dark league images
remain separate. Validate the 128x128 DXT5 canvas and the upper-left 48x48 logo bounds.
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

Career stadium photos use the host's local image conversion and native movie
package writer. The host reads the photo selected by FSW (or the career database
fallback), preserves the original, and converts its pixels to DDS in
`data/ui/imgAssets/stadium/stadium_<key>.dds`. It then generates a minimal six-member
`image_mc` BIG in `data/ui/artAssets/stadium/stadium_cmphoto_<content-hash>.big`.
Only the movie dimensions and rectangle geometry are adjusted; the embedded DDS
is byte identical. The published stadium helper key names this generated package.
No manual stadium BIG is needed. Missing/invalid photos or failed package writes
keep the slot hidden. Source changes receive another content key, avoiding stale
fallback cache entries. Existing game stadium BIGs are never overwritten.

The earlier formatter redirect to loose stadium DDSs was removed: live RAM showed
the card still requesting a movie and falling back to `notfound.big`, without any
formatter redirect. A generated native package with the correct Elcyrzao DDS was
confirmed in-game on 14 October 2026. The automatic writer is separately covered
by tests for member offsets, exact DDS pixels, geometry, repair, content changes
and invalid input; its installation still requires a game restart.

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

## Squad management and formations goalkeeper (17 October 2026)

The root fix is now in `career_native/src/host/swiss_byte_patches.h`: all SIX
keeper entries retain the original signed JLE automatic fallback while retaining
the unsigned shift for positive packed IDs. The central unsigned-key adaptation
previously changed JLE to JE, converting the automatic -1 into team 262143.
This affects five Squad-family producers plus the Starting XI serializer. The
visible active Squad path is RVA `409ACB5`, distinct from the saved-roster paths.
The two local guards below remain compatible with corrected central descriptors.
`career_native/scripts/tests/test_keeper_auto_keys.cmd` executes all six actual
native keeper branches using the production byte table, seven clubs and six
selectors. The Starting XI signature check accepts both the older JE and the
corrected JLE, requiring the rest of the live branch to match exactly.

The editable roster and formation screens have two separate producers, both
different from StartingXIDP. Both requested `2_262143_0` for the keeper while the
ten outfield rows correctly requested `0_1043_0` for Flamengo. Formation uses
the branch at RVA `40948A5`; the editable roster uses RVA `409979E`. Repairing
one does not cover the other, and the Starting XI serializer covers neither.

`keeper_squad_hook.inc` validates the x64 executable timestamp and the complete
31-byte formation and 24-byte roster branches, then changes their conditional
opcodes at `40948AD` and `40997A3` from JE to JLE. A nonpositive selector now uses the native sheet TeamID, matching
the outfield branch. Positive explicit selectors retain their native decoding.
The branch length, target, source sheet and ten outfield instructions are untouched.
The installer accepts an already corrected branch and rejects other signatures.
`Fifa16UiAssetsSquadKeeperReady` reports activation independently of Starting XI.

`test_keeper_squad.c` executes both captured native x64 branches for all eleven
positions on BOTH screens, seven club IDs, automatic, negative and positive explicit selectors.
It reproduces the original keeper's invalid team, verifies type 2 for the keeper
and type 0 for automatic outfield rows, preserves positive overrides and source
sheets, and tests signature rejection. `build.cmd` runs it alongside the existing
Starting XI and calendar tests. The normal worker now requires all three repairs
before reporting READY. No image, lineup or career-save replacement is involved.
