#ifndef SERVER16_SCOREBOARD_OPTIONS_WIRE_H
#define SERVER16_SCOREBOARD_OPTIONS_WIRE_H
#include <string.h>
/* Only a catalog identity and an index. No paths, file names or commands. */
static int scoreboard_options_wire_valid(const char *wire)
{
    const char *p;size_t n;unsigned value=0,i;
    if(!wire)return 0;
    n=strlen(wire);
    if(n<80||n>84||strncmp(wire,"S16SCORE1|",10))return 0;
    p=wire+10;
    if(strspn(p,"0123456789abcdef")!=64||p[64]!='|')return 0;
    p+=65;n=strspn(p,"0123456789");
    if(n<1||n>4||(n>1&&p[0]=='0')||strcmp(p+n,"|END"))return 0;
    for(i=0;i<n;++i)value=value*10+(unsigned)(p[i]-'0');
    return value<1024;
}
#endif
