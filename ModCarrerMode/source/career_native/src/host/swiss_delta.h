#ifndef FIFA_SWISS_DELTA_H
#define FIFA_SWISS_DELTA_H
#include <windows.h>
/* Adds selected Swiss routines to the original host and original L9.65.
 * Never starts the Swiss DLL or its whole-module initializer. */
BOOL swiss_delta_start(HMODULE host, const char *game_dir, const char *mod_dir);
#endif
