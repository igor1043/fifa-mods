# EASFC Hide Plugin - safe replacement

This replacement keeps the original 80-byte EASFC reconnect-widget signature and
the three `0x73 -> 0x74` widget changes. Unlike the legacy binary, all signature
reads and writes are guarded against access violations. If FIFA changes or frees
a region while it is being scanned, that region is skipped and the worker
continues without changing memory.

Build with `build_easfc_hide_plugin_safe.cmd`. The resulting DLL is placed in
`build\\easfc_hide_plugin.dll` and is intended to replace the optional plugin in
`ModCarrerMode\\mods` after FIFA has been closed.
