/* Native GameSettings owns the row; only queue a bounded, fixture-bound value. */
static int attendance_options_capture(const char *wire)
{
    static const unsigned offsets[]={232,192,136,472};
    typedef struct {DWORD owner,heartbeat,pid;LONG generation,home,away,phase;} CrowdHeader;
    uintptr_t node=0;char page[96],folder[MAX_PATH],path[MAX_PATH],temp[MAX_PATH];
    HANDLE mapping;const CrowdHeader *shared;CrowdHeader state;
    FILETIME created,exit,kernel,user;ULARGE_INTEGER identity;FILE *file;unsigned i;
    int percent;char canonical[32];
    if(!bank_mail_string(wire,32)||sscanf(wire,"S16CROWD1|%3d|END",&percent)!=1)return 0;
    if(percent!=-1&&(percent<0||percent>100||percent%5))return 0;
    snprintf(canonical,sizeof(canonical),"S16CROWD1|%d|END",percent);
    if(strcmp(wire,canonical))return 0;
    if(!read_card_scope((uintptr_t)g_module_base+0x3809030,&node,8))return 0;
    for(i=0;i<4;++i)if(!node||!read_card_scope(node+offsets[i],&node,8))return 0;
    if(!node||!read_card_scope(node,page,sizeof(page))||!memchr(page,0,sizeof(page))
       ||strcmp(page,"game/screens/settings/GameSettings"))return 0;
    mapping=OpenFileMappingW(FILE_MAP_READ,FALSE,L"Local\\CGFS16_Crowd_v1");if(!mapping)return 0;
    shared=(const CrowdHeader *)MapViewOfFile(mapping,FILE_MAP_READ,0,0,sizeof(state));
    if(!shared){CloseHandle(mapping);return 0;}
    memcpy(&state,shared,sizeof(state));UnmapViewOfFile(shared);CloseHandle(mapping);
    if(!state.owner||state.pid!=GetCurrentProcessId()||state.phase!=1||state.home<=0||state.away<=0
       ||(DWORD)(GetTickCount()-state.heartbeat)>=2000)return 0;
    if(!GetProcessTimes(GetCurrentProcess(),&created,&exit,&kernel,&user))return 0;
    identity.LowPart=created.dwLowDateTime;identity.HighPart=created.dwHighDateTime;
    if(snprintf(folder,sizeof(folder),"%s\\runtime\\crowd_selector",g_mod_dir)>=(int)sizeof(folder))return 0;
    CreateDirectoryA(folder,NULL);
    if(snprintf(path,sizeof(path),"%s\\request.tsv",folder)>=(int)sizeof(path))return 0;
    if(snprintf(temp,sizeof(temp),"%s.new",path)>=(int)sizeof(temp))return 0;
    file=fopen(temp,"wb");if(!file)return 0;
    fprintf(file,"schema=1\npid=%lu\ncreated=%llu\ngeneration=%ld\nhome=%ld\naway=%ld\ncaptured_tick=%llu\nwire=%s\n",
        GetCurrentProcessId(),(unsigned long long)identity.QuadPart,state.generation,state.home,state.away,
        (unsigned long long)GetTickCount64(),wire);
    if(fclose(file))return 0;
    return MoveFileExA(temp,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;
}
