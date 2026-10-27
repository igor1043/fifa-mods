#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>

typedef unsigned int (WINAPI *VersionFn)(void);
typedef BOOL (WINAPI *StartFn)(const char *);

int main(int argc, char **argv)
{
    HMODULE bridge;
    VersionFn version;
    StartFn start;
    BOOL result;
    if (argc != 4 && argc != 5) return 2;
    if (argc == 5 && !LoadLibraryA(argv[4])) return 7;
    bridge = LoadLibraryA(argv[1]);
    if (!bridge) return 3;
    version = (VersionFn)(void *)GetProcAddress(bridge, "Fifa16ModGetApiVersion");
    start = (StartFn)(void *)GetProcAddress(bridge, "Fifa16ModStart");
    if (!version || version() != 1 || !start) return 4;
    result = start(argv[2]);
    printf("started=%d payload_loaded=%d\n", result,
        GetModuleHandleA("SubsOn.dll") != NULL);
    if (result) {
        if (!start(argv[2])) return 5;
        Sleep(500);
    }
    return (result != 0) == (argv[3][0] == '1') ? 0 : 6;
}
