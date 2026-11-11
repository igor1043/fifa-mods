/* Observe the owned options row. Stock GameSettings still owns every setting,
 * native button, keyboard event and mouse callback. No career/save writes. */
#include "scoreboard_options_wire.h"
static int scoreboard_options_capture(const char *wire)
{
    static const unsigned offsets[]={232,192,136,472};
    uintptr_t node=0;char page[96],folder[MAX_PATH],path[MAX_PATH],temp[MAX_PATH];
    unsigned i;FILE *file;FILETIME created,exit,kernel,user;ULARGE_INTEGER identity;
    if(!bank_mail_string(wire,128)||!scoreboard_options_wire_valid(wire))return 0;
    if(!read_card_scope((uintptr_t)g_module_base+0x3809030,&node,8))return 0;
    for(i=0;i<4;++i)if(!node||!read_card_scope(node+offsets[i],&node,8))return 0;
    if(!node||!read_card_scope(node,page,sizeof(page))||!memchr(page,0,sizeof(page))
       ||strcmp(page,"game/screens/settings/GameSettings"))return 0;
    if(!GetProcessTimes(GetCurrentProcess(),&created,&exit,&kernel,&user))return 0;
    identity.LowPart=created.dwLowDateTime;identity.HighPart=created.dwHighDateTime;
    if(snprintf(folder,sizeof(folder),"%s\\runtime\\scoreboard_selector",g_mod_dir)>=(int)sizeof(folder))return 0;
    CreateDirectoryA(folder,NULL);
    if(snprintf(path,sizeof(path),"%s\\request.tsv",folder)>=(int)sizeof(path))return 0;
    if(snprintf(temp,sizeof(temp),"%s.new",path)>=(int)sizeof(temp))return 0;
    file=fopen(temp,"wb");if(!file)return 0;
    fprintf(file,"schema=1\npid=%lu\ncreated=%llu\ncaptured_tick=%llu\nwire=%s\n",
            GetCurrentProcessId(),(unsigned long long)identity.QuadPart,(unsigned long long)GetTickCount64(),wire);
    if(fclose(file))return 0;
    return MoveFileExA(temp,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;
}
