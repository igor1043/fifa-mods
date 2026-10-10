/* Catalogue existing artwork. Never creates or renames assets. */
typedef struct {int id;uint64_t hash;DWORD size;} UiDigest;
static int competition_art[65536],legacy_art[65536];
static unsigned char packed_leagues[65536];
static volatile LONG catalog_ready;
static int strict_id(const char *name,const char *pattern,int *id) {
    int used=0;char lower_name[512],lower_pattern[128];size_t i;
    if(strlen(name)>=sizeof(lower_name) || strlen(pattern)>=sizeof(lower_pattern))return 0;
    strcpy(lower_name,name);strcpy(lower_pattern,pattern);
    for(i=0;lower_name[i];i++)if(lower_name[i]>='A'&&lower_name[i]<='Z')lower_name[i]+='a'-'A';
    for(i=0;lower_pattern[i];i++)if(lower_pattern[i]>='A'&&lower_pattern[i]<='Z')lower_pattern[i]+='a'-'A';
    return sscanf(lower_name,lower_pattern,id,&used)==1 && used>0 && !lower_name[used] && *id>0;
}
static BYTE *dds_bytes(const char *path,DWORD *size,uint64_t *hash) {
    FILE *file;BYTE *data;long length;size_t i;uint64_t value=14695981039346656037ULL;
    if(!valid_dds(path) || !(file=fopen(path,"rb")))return NULL;
    if(fseek(file,0,SEEK_END) || (length=ftell(file))<128 || length>8*1024*1024 || fseek(file,0,SEEK_SET)){fclose(file);return NULL;}
    data=(BYTE*)malloc((size_t)length);if(!data){fclose(file);return NULL;}
    if(fread(data,1,(size_t)length,file)!=(size_t)length){free(data);fclose(file);return NULL;}fclose(file);
    for(i=0;i<(size_t)length;i++){value^=data[i];value*=1099511628211ULL;}
    *size=(DWORD)length;*hash=value;return data;
}
static BOOL equal_art(const BYTE *bytes,DWORD size,int asset) {
    char path[MAX_PATH];BYTE *other;DWORD length;uint64_t hash;BOOL equal;
    snprintf(path,sizeof(path),"%s/data/ui/imgAssets/league/light/l%d.dds",game_dir,asset);
    other=dds_bytes(path,&length,&hash);if(!other)return FALSE;
    equal=length==size && !memcmp(bytes,other,size);free(other);return equal;
}
static DWORD big_integer(const BYTE *p) {return ((DWORD)p[0]<<24)|((DWORD)p[1]<<16)|((DWORD)p[2]<<8)|p[3];}
static void index_packed(const char *path) {
    FILE *file=fopen(path,"rb");BYTE header[16],*index;DWORD end,count,offset=0,i;
    if(!file)return;
    if(fread(header,1,16,file)!=16 || (memcmp(header,"BIGF",4) && memcmp(header,"BIG4",4))){fclose(file);return;}
    count=big_integer(header+8);end=big_integer(header+12);
    if(end<16 || end>16*1024*1024 || count>1000000){fclose(file);return;}
    index=(BYTE*)malloc(end-16);if(!index){fclose(file);return;}
    if(fread(index,1,end-16,file)!=end-16){free(index);fclose(file);return;}fclose(file);
    for(i=0;i<count && offset+9<=end-16;i++) {
        char name[512];BYTE *stop;size_t length,j;int id;
        offset+=8;stop=(BYTE*)memchr(index+offset,0,end-16-offset);if(!stop)break;
        length=(size_t)(stop-(index+offset));
        if(length<sizeof(name)) {
            memcpy(name,index+offset,length);name[length]=0;
            for(j=0;j<length;j++){if(name[j]=='\\')name[j]='/';else if(name[j]>='A'&&name[j]<='Z')name[j]+='a'-'A';}
            if((strict_id(name,"data/ui/imgassets/league/light/l%d.dds%n",&id) || strict_id(name,"data/ui/imgassets/league/dark/l%d.dds%n",&id)) && id<65536)packed_leagues[id]=1;
        }
        offset+=(DWORD)length+1;
    }
    free(index);
}
static BOOL existing_league(int asset) {
    char path[MAX_PATH];
    if(asset<=0 || asset>2000000)return FALSE;
    snprintf(path,sizeof(path),"%s/data/ui/imgAssets/league/light/l%d.dds",game_dir,asset);
    if(valid_dds(path))return TRUE;
    snprintf(path,sizeof(path),"%s/data/ui/imgAssets/league/dark/l%d.dds",game_dir,asset);
    return valid_dds(path) || (asset<65536 && packed_leagues[asset]);
}
static void build_catalog(void) {
    WIN32_FIND_DATAA info;HANDLE find;char pattern[MAX_PATH],path[MAX_PATH],line[512];
    UiDigest *digests=(UiDigest*)calloc(4096,sizeof(UiDigest));size_t count=0,i;int matches=0,id;FILE *file;
    if(!digests)return;
    snprintf(pattern,sizeof(pattern),"%s/*.big",game_dir);find=FindFirstFileA(pattern,&info);
    if(find!=INVALID_HANDLE_VALUE){do {snprintf(path,sizeof(path),"%s/%s",game_dir,info.cFileName);index_packed(path);}while(FindNextFileA(find,&info));FindClose(find);}
    snprintf(pattern,sizeof(pattern),"%s/data/ui/imgAssets/league/light/l*.dds",game_dir);find=FindFirstFileA(pattern,&info);
    if(find!=INVALID_HANDLE_VALUE){do {
        BYTE *data;DWORD size;uint64_t hash;
        if(!strict_id(info.cFileName,"l%d.dds%n",&id) || count>=4096)continue;
        snprintf(path,sizeof(path),"%s/data/ui/imgAssets/league/light/%s",game_dir,info.cFileName);
        data=dds_bytes(path,&size,&hash);if(!data)continue;free(data);
        digests[count++]=(UiDigest){id,hash,size};
    }while(FindNextFileA(find,&info));FindClose(find);}
    snprintf(pattern,sizeof(pattern),"%s/data/ui/imgAssets/cmCalendarCompetitions/cmCalendarCompetitions*.dds",game_dir);find=FindFirstFileA(pattern,&info);
    if(find!=INVALID_HANDLE_VALUE){do {
        BYTE *data;DWORD size;uint64_t hash;int selected=0;
        if(!strict_id(info.cFileName,"cmCalendarCompetitions%d.dds%n",&id) || id>=65536)continue;
        snprintf(path,sizeof(path),"%s/data/ui/imgAssets/cmCalendarCompetitions/%s",game_dir,info.cFileName);
        data=dds_bytes(path,&size,&hash);if(!data)continue;
        for(i=0;i<count;i++)if(digests[i].size==size && digests[i].hash==hash && (!selected || digests[i].id<selected) && equal_art(data,size,digests[i].id))selected=digests[i].id;
        free(data);if(selected){competition_art[id]=selected;matches++;}
    }while(FindNextFileA(find,&info));FindClose(find);}
    free(digests);
    snprintf(path,sizeof(path),"%s/dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata/compobj.txt",game_dir);
    file=fopen(path,"rb");if(file){while(fgets(line,sizeof(line),file)) {
        int root,type,parent,asset,canonical;char name[64],display[160];
        if(sscanf(line,"%d,%d,%63[^,],%159[^,],%d",&root,&type,name,display,&parent)!=5 || type!=3 || root<=0 || root>=65536 || name[0]!='C')continue;
        asset=atoi(name+1);canonical=competition_art[root];
        if(asset>0 && asset<65536 && canonical>0){if(!legacy_art[asset])legacy_art[asset]=canonical;else if(legacy_art[asset]!=canonical)legacy_art[asset]=-1;}
    }fclose(file);}
    InterlockedExchange(&catalog_ready,1);log_line("CATALOG existing league art/root matches",(int)count,matches);
}
__declspec(dllexport) int WINAPI Fifa16UiAssetsHasCompetition(int asset) {return existing_league(asset);}
__declspec(dllexport) int WINAPI Fifa16UiAssetsResolveCompetition(int root,const void *registry) {
    int asset;
    if(root<=0 || root>=65536)return 0;
    asset=Fifa16UiAssetsResolvePreseason(root,registry);if(asset)return asset;
    return InterlockedCompareExchange(&catalog_ready,0,0)?competition_art[root]:0;
}
static int resolve_image_path(const char *input,char *out,size_t capacity) {
    const char *relative=input;char normalized[MAX_PATH],prefix[MAX_PATH],theme[16];size_t i;int id,used=0,asset=0;
    if(strlen(input)>=sizeof(normalized))return 0;
    snprintf(normalized,sizeof(normalized),"%s",input);
    for(i=0;normalized[i];i++)if(normalized[i]=='\\')normalized[i]='/';
    relative=normalized;
    if(!_strnicmp(relative,"data/ui/",8)){relative+=8;snprintf(prefix,sizeof(prefix),"data/ui/");}
    else if(!_strnicmp(relative,"ui/",3)){relative+=3;snprintf(prefix,sizeof(prefix),"ui/");}
    else if(!_strnicmp(relative,"imgAssets/",10) || !_strnicmp(relative,"artAssets/",10))prefix[0]=0;
    else return 0;
    if(sscanf(relative,"imgAssets/league/%15[^/]/l%d.dds%n",theme,&id,&used)==2 && used>0 && !relative[used] && id>0 && id<65536) {
        if(existing_league(id))return 0;
        asset=competition_art[id]?competition_art[id]:legacy_art[id];
        if(asset>0 && existing_league(asset))return snprintf(out,capacity,"%simgAssets/league/%s/l%d.dds",prefix,theme,asset)>0;
    }
    used=0;
    if((sscanf(relative,"artAssets/cmCalendarCompetitions/cmcomp_%d.big%n",&id,&used)==1 && used>0 && !relative[used] && existing_league(id)) ||
       (used=0,sscanf(relative,"artAssets/cmCalendarCompetitions/cmcomp_%d.swf%n",&id,&used)==1 && used>0 && !relative[used] && existing_league(id))) {
        return snprintf(out,capacity,"%simgAssets/league/light/l%d.dds",prefix,id)>0;
    }
    return 0;
}
