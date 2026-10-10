#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <wchar.h>
#include <stdint.h>

/* Experimental asset compatibility bridge. This does not patch the decoder
 * or claim to remove any bitrate limit. Existing IAT hooks are chained. */
typedef HANDLE (WINAPI *OpenAFn)(LPCSTR,DWORD,DWORD,LPSECURITY_ATTRIBUTES,DWORD,DWORD,HANDLE);
typedef HANDLE (WINAPI *OpenWFn)(LPCWSTR,DWORD,DWORD,LPSECURITY_ATTRIBUTES,DWORD,DWORD,HANDLE);
typedef BOOL (WINAPI *ReadFn)(HANDLE,LPVOID,DWORD,LPDWORD,LPOVERLAPPED);
typedef BOOL (WINAPI *CloseFn)(HANDLE);
static OpenAFn original_a;
static OpenWFn original_w;
static ReadFn original_read;
static CloseFn original_close;
static wchar_t active[MAX_PATH], alternate[MAX_PATH];
static char log_path[MAX_PATH];
static volatile LONG started;
static SRWLOCK lock=SRWLOCK_INIT;
typedef struct { HANDLE handle; ULONGLONG bytes; DWORD reads; } Track;
static Track tracks[16];

static void log_event(const char *format, ...) {
    DWORD saved=GetLastError(); FILE *f=NULL; va_list args;
    AcquireSRWLockExclusive(&lock);
    if (!fopen_s(&f,log_path,"a") && f) {
        fprintf(f,"%llu ",(unsigned long long)GetTickCount64());
        va_start(args,format); vfprintf(f,format,args); va_end(args);
        fputc('\n',f); fclose(f);
    }
    ReleaseSRWLockExclusive(&lock); SetLastError(saved);
}
static BOOL matches(LPCWSTR path,DWORD access,DWORD creation) {
    wchar_t full[MAX_PATH]; DWORD count; size_t i;
    if (!path || creation!=OPEN_EXISTING || !(access&GENERIC_READ) ||
        (access&(GENERIC_WRITE|DELETE|FILE_WRITE_DATA|FILE_APPEND_DATA))) return FALSE;
    count=GetFullPathNameW(path,MAX_PATH,full,NULL);
    if (!count || count>=MAX_PATH) return FALSE;
    for(i=0;full[i];i++) if(full[i]==L'/') full[i]=L'\\';
    return !_wcsicmp(full,active);
}
static void remember(HANDLE h) {
    size_t i;
    if(h==INVALID_HANDLE_VALUE) return;
    AcquireSRWLockExclusive(&lock);
    for(i=0;i<16;i++) if(!tracks[i].handle) {
        tracks[i].handle=h; tracks[i].bytes=0; tracks[i].reads=0; break;
    }
    ReleaseSRWLockExclusive(&lock);
}
static HANDLE WINAPI open_w(LPCWSTR p,DWORD a,DWORD s,LPSECURITY_ATTRIBUTES x,DWORD c,DWORD f,HANDLE t) {
    HANDLE h; DWORD error;
    if(!matches(p,a,c)) return original_w(p,a,s,x,c,f,t);
    h=original_w(alternate,a,s,x,c,f,t); error=GetLastError();
    if(h==INVALID_HANDLE_VALUE) {
        log_event("override_failed error=%lu fallback=original",error);
        h=original_w(p,a,s,x,c,f,t); error=GetLastError();
    } else log_event("movie_open override=1 handle=%p",h);
    remember(h); SetLastError(error); return h;
}
static HANDLE WINAPI open_a(LPCSTR p,DWORD a,DWORD s,LPSECURITY_ATTRIBUTES x,DWORD c,DWORD f,HANDLE t) {
    wchar_t path[MAX_PATH]; char target[MAX_PATH]; HANDLE h; DWORD error;
    if(!p || !MultiByteToWideChar(CP_ACP,0,p,-1,path,MAX_PATH) || !matches(path,a,c))
        return original_a(p,a,s,x,c,f,t);
    if(!WideCharToMultiByte(CP_ACP,WC_NO_BEST_FIT_CHARS,alternate,-1,target,MAX_PATH,NULL,NULL))
        return original_a(p,a,s,x,c,f,t);
    h=original_a(target,a,s,x,c,f,t); error=GetLastError();
    if(h==INVALID_HANDLE_VALUE) {
        log_event("override_failed error=%lu fallback=original",error);
        h=original_a(p,a,s,x,c,f,t); error=GetLastError();
    } else log_event("movie_open override=1 handle=%p",h);
    remember(h); SetLastError(error); return h;
}
static BOOL WINAPI read_file(HANDLE h,LPVOID b,DWORD count,LPDWORD got,LPOVERLAPPED ov) {
    BOOL result=original_read(h,b,count,got,ov); DWORD error=GetLastError(); size_t i; BOOL tracked=FALSE;
    AcquireSRWLockExclusive(&lock);
    for(i=0;i<16;i++) if(tracks[i].handle==h) {
        tracks[i].reads++; if(result && got) tracks[i].bytes+=*got; tracked=TRUE; break;
    }
    ReleaseSRWLockExclusive(&lock);
    if(tracked && !result && error!=ERROR_IO_PENDING)
        log_event("movie_read_failed error=%lu requested=%lu",error,count);
    SetLastError(error); return result;
}
static BOOL WINAPI close_file(HANDLE h) {
    BOOL result; DWORD error; size_t i; ULONGLONG bytes=0; DWORD reads=0; BOOL tracked=FALSE;
    /* Remove before closing: Windows may immediately reuse the handle. */
    AcquireSRWLockExclusive(&lock);
    for(i=0;i<16;i++) if(tracks[i].handle==h) {
        bytes=tracks[i].bytes; reads=tracks[i].reads; tracks[i].handle=NULL; tracked=TRUE; break;
    }
    ReleaseSRWLockExclusive(&lock);
    result=original_close(h); error=GetLastError();
    if(tracked) log_event("movie_close result=%d reads=%lu synchronous_bytes=%llu",result,reads,(unsigned long long)bytes);
    SetLastError(error); return result;
}
static BOOL patch(void **slot,void *replacement,void **previous) {
    DWORD old,unused; void *current=*slot;
    if(!VirtualProtect(slot,sizeof(void*),PAGE_READWRITE,&old)) return FALSE;
    *previous=current;
    InterlockedExchangePointer((PVOID volatile*)slot,replacement);
    VirtualProtect(slot,sizeof(void*),old,&unused); return TRUE;
}
static unsigned install_hooks(void) {
    BYTE *base=(BYTE*)GetModuleHandleW(NULL);
    IMAGE_DOS_HEADER *dos=(IMAGE_DOS_HEADER*)base;
    IMAGE_NT_HEADERS64 *nt; IMAGE_IMPORT_DESCRIPTOR *desc; unsigned installed=0;
    if(dos->e_magic!=IMAGE_DOS_SIGNATURE) return 0;
    nt=(IMAGE_NT_HEADERS64*)(base+dos->e_lfanew);
    if(nt->Signature!=IMAGE_NT_SIGNATURE || nt->OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC) return 0;
    if(!nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress) return 0;
    desc=(IMAGE_IMPORT_DESCRIPTOR*)(base+nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress);
    for(;desc->Name;desc++) {
        IMAGE_THUNK_DATA64 *names,*slots;
        if(!desc->OriginalFirstThunk) continue;
        names=(IMAGE_THUNK_DATA64*)(base+desc->OriginalFirstThunk);
        slots=(IMAGE_THUNK_DATA64*)(base+desc->FirstThunk);
        for(;names->u1.AddressOfData;names++,slots++) {
            IMAGE_IMPORT_BY_NAME *item;
            if(IMAGE_SNAP_BY_ORDINAL64(names->u1.Ordinal)) continue;
            item=(IMAGE_IMPORT_BY_NAME*)(base+names->u1.AddressOfData);
            if(!strcmp((char*)item->Name,"CreateFileW")) installed+=patch((void**)&slots->u1.Function,(void*)open_w,(void**)&original_w);
            else if(!strcmp((char*)item->Name,"CreateFileA")) installed+=patch((void**)&slots->u1.Function,(void*)open_a,(void**)&original_a);
            else if(!strcmp((char*)item->Name,"ReadFile")) installed+=patch((void**)&slots->u1.Function,(void*)read_file,(void**)&original_read);
            else if(!strcmp((char*)item->Name,"CloseHandle")) installed+=patch((void**)&slots->u1.Function,(void*)close_file,(void**)&original_close);
        }
    }
    return installed;
}
__declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(void) {return 1;}
__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *root) {
    wchar_t exe[MAX_PATH],mod[MAX_PATH]; wchar_t *last; unsigned hooks;
    if(!root || !root[0]) return FALSE;
    if(InterlockedCompareExchange(&started,1,0)) return TRUE;
    if(!GetModuleFileNameW(NULL,exe,MAX_PATH) ||
       !MultiByteToWideChar(CP_ACP,0,root,-1,mod,MAX_PATH)) return FALSE;
    last=wcsrchr(exe,L'\\'); if(!last) return FALSE; *last=0;
    if(swprintf_s(active,MAX_PATH,L"%s\\data\\movies\\bootflowoutro.vp8",exe)<0 ||
       swprintf_s(alternate,MAX_PATH,L"%s\\vp8_compat\\test_1080p_high.vp8",mod)<0 ||
       sprintf_s(log_path,MAX_PATH,"%s\\vp8_compat\\vp8_compat.log",root)<0) return FALSE;
    if(GetFileAttributesW(alternate)==INVALID_FILE_ATTRIBUTES) {
        log_event("start_failed missing_test_movie"); return FALSE;
    }
    hooks=install_hooks();
    log_event("start hooks=%u mode=legacy_webm_asset_override decoder_patch=0",hooks);
    return hooks>0;
}
BOOL WINAPI DllMain(HINSTANCE h,DWORD why,LPVOID reserved) {
    (void)reserved; if(why==DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(h); return TRUE;
}
