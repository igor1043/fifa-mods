# Skip FIFA 16 server shutdown notice

This optional native plugin watches FIFA 16's own readable private memory for
the exact Portuguese server shutdown notice. It requires the text to remain
present for 1.25 seconds and sends one Enter confirmation only while a FIFA
window is foreground. It stops searching after ten minutes.

The plugin does not modify game memory, files, or online services. Its runtime
log is written to ModCarrerMode\logs\skip_server_shutdown_notice.log.

Build with build.cmd. The resulting DLL is installed under
ModCarrerMode\mods\skip_server_shutdown_notice\.

Remove the skip_server_shutdown_notice\skip_server_shutdown_notice.dll entry
from ModCarrerMode\mods\enabled.txt to disable it.
