#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
typedef BOOL (WINAPI *StartFn)(const char*);
static void put(const char *path,const char *text) {
    DWORD wrote; HANDLE h=CreateFileA(path,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,0,NULL);
    if(h==INVALID_HANDLE_VALUE || !WriteFile(h,text,(DWORD)strlen(text),&wrote,NULL)) ExitProcess(2);
    CloseHandle(h);
}
static void check_a(const char *path,const char *expected) {
    DWORD got=0; char data[32]={0}; HANDLE h=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,0,NULL);
    if(h==INVALID_HANDLE_VALUE || !ReadFile(h,data,31,&got,NULL) || strcmp(data,expected)) {
        fprintf(stderr,"FAIL %s got=%s\n",path,data); ExitProcess(3);
    }
    CloseHandle(h);
}
int main(void) {
    HMODULE dll; StartFn start; HANDLE h; DWORD got; char data[32]={0};
    CreateDirectoryA("data",NULL); CreateDirectoryA("data\\movies",NULL);
    CreateDirectoryA("fixture_mods",NULL); CreateDirectoryA("fixture_mods\\vp8_compat",NULL);
    put("data\\movies\\bootflowoutro.vp8","ORIGINAL");
    put("other.vp8","OTHER");
    put("fixture_mods\\vp8_compat\\test_1080p_high.vp8","OVERRIDE");
    dll=LoadLibraryA("vp8_compat.dll"); if(!dll) return 4;
    start=(StartFn)GetProcAddress(dll,"Fifa16ModStart");
    if(!start || !start("fixture_mods")) return 5;
    check_a("data/movies/bootflowoutro.vp8","OVERRIDE");
    h=CreateFileW(L"data\\movies\\bootflowoutro.vp8",GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,0,NULL);
    if(h==INVALID_HANDLE_VALUE || !ReadFile(h,data,31,&got,NULL) || strcmp(data,"OVERRIDE")) return 6;
    CloseHandle(h);
    check_a("other.vp8","OTHER");
    put("data\\movies\\bootflowoutro.vp8","WRITE_PASSTHROUGH");
    check_a("data\\movies\\bootflowoutro.vp8","OVERRIDE");
    if(!DeleteFileA("fixture_mods\\vp8_compat\\test_1080p_high.vp8")) return 7;
    check_a("data\\movies\\bootflowoutro.vp8","WRITE_PASSTHROUGH");
    puts("PASS: ANSI/Unicode redirect, slash normalization, unrelated files, writes, missing asset fallback");
    /* IAT hook lifetime is process lifetime; do not FreeLibrary while hooked. */
    return 0;
}
