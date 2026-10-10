#define UI_ASSETS_TEST
#include "career_ui_assets.c"
#include "path_hooks.inc"
#define CHECK(x) do {if(!(x)){printf("FAIL %d %s\n",__LINE__,#x);return 1;}} while(0)
static int __cdecl test_print_core(void *writer,void *object,const char *format,va_list arguments) {
    struct {char *buffer;size_t written;size_t capacity;} *sink=object;
    (void)writer;return vsnprintf(sink->buffer,sink->capacity,format,arguments);
}
static void __cdecl test_string_core(void *object,const char *format,va_list arguments) {
    char **parts=object;size_t capacity=(size_t)(parts[2]-parts[0]);
    int length=vsnprintf(parts[0],capacity,format,arguments);
    parts[1]=parts[0]+(length>=0 && (size_t)length<capacity?length:0);
}
int main(void) {
    BYTE rows[2*0x5c]={0};int id=2240,type=3,asset=848;char name[MAX_PATH],resolved[MAX_PATH];
    memcpy(rows,&id,4);memcpy(rows+4,&type,4);memcpy(rows+12,"CRTR",5);
    memcpy(rows+17,"cm_pst_champions_trophy",23);memcpy(rows+0x54,&asset,4);
    CHECK(resolve_rows(rows,2,id)==848);CHECK(!resolve_rows(rows,2,2239));
    memcpy(rows+0x5c,rows,0x5c);CHECK(!resolve_rows(rows,2,id));memset(rows+0x5c,0,0x5c);
    rows[12]='C';rows[13]='1';CHECK(!resolve_rows(rows,2,id));memcpy(rows+12,"CRTR",5);
    asset=999;memcpy(rows+0x54,&asset,4);CHECK(!resolve_rows(rows,2,id));
    CHECK(strict_id("l848.DDS","l%d.dds%n",&id) && id==848);
    CHECK(!strict_id("l848.dds.bad","l%d.dds%n",&id));
    strcpy(game_dir,"U:\\fifa 16");build_catalog();
    CHECK(competition_art[688]==723);CHECK(competition_art[691]==726);
    CHECK(Fifa16UiAssetsResolveCompetition(688,NULL)==723);
    CHECK(existing_league(206)); /* Packed stock DDS must also be recognized. */
    CHECK(!resolve_image_path("imgAssets/league/light/l848.dds",resolved,sizeof(resolved)));
    CHECK(resolve_image_path("imgAssets/league/light/l3.dds",resolved,sizeof(resolved)) && !strcmp(resolved,"imgAssets/league/light/l723.dds"));
    CHECK(resolve_image_path("artAssets/cmCalendarCompetitions/cmcomp_848.swf",resolved,sizeof(resolved)) && !strcmp(resolved,"imgAssets/league/light/l848.dds"));
    CHECK(!resolve_image_path("artAssets/cmCalendar/cmcalendar_8.swf",resolved,sizeof(resolved)));
    CHECK(!resolve_image_path("imgAssets/kits/notfound.dds",resolved,sizeof(resolved)));
    CHECK(!resolve_image_path("invalid/imgAssets/league/light/l3.dds",resolved,sizeof(resolved)));
    CHECK(!resolve_image_path("ui/imgAssets/kits/j30_110636_0.dds",resolved,sizeof(resolved)));
    strcpy(name,"30_110636_0");CHECK(!normalize_output(name,sizeof(name)) && !strcmp(name,"30_110636_0"));
    native_print_core=test_print_core;native_string_core=test_string_core;
    CHECK(ui_print(name,sizeof(name),"kit %d %s",30,"preserved")==16 && !strcmp(name,"kit 30 preserved"));
    CHECK(ui_print(name,sizeof(name),"artAssets/cmCalendarCompetitions/cmcomp_%d.swf",848)==(int)strlen("imgAssets/league/light/l848.dds") && !strcmp(name,"imgAssets/league/light/l848.dds"));
    CHECK(ui_print(name,4,"%s","abcdef")==6 && !strcmp(name,"abc"));
    {char *parts[3]={name,name,name+sizeof(name)};
     CHECK(ui_string(parts,"artAssets/cmCalendarCompetitions/cmcomp_%d.swf",848)==parts);
     CHECK(!strcmp(name,"imgAssets/league/light/l848.dds") && parts[1]==name+strlen(name));
     ui_string(parts,"ui/imgAssets/kits/j%d_%d_0.dds",30,110636);
     CHECK(!strcmp(name,"ui/imgAssets/kits/j30_110636_0.dds"));}
    puts("PASS: preseason identity, existing-art catalogue, packed resources, original icon paths, kits and unrelated requests preserved");return 0;
}
