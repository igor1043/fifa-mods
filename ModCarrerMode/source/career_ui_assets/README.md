# Dynamic career competition icons

Icon-only module for FIFA 16 x64, supported timestamp 577DE45C.
No kit conversion, new images, IDs or aliases. Existing artwork is indexed from
league DDS files and BIG directories. Calendar-to-league matches require identical
DDS contents. Ambiguous legacy IDs are ignored. Preseason events use their native
registry identity after checking all 61 expanded-layout patches.

Guarded native formatter adapters redirect calendar cmcomp requests to existing
league DDS paths, using the original game formatter and allocator. Unrelated
paths, including goalkeeper kits, are preserved. Database and saves are unchanged.

build.cmd runs identity, catalogue, packed-resource and formatter tests.
In-game rendering requires a restart and Calendar/Competition testing.
The module log records CATALOG, READY and RESOLVE. Earlier aliases are untouched;
this version creates no aliases. Disable through mods/enabled.txt.
