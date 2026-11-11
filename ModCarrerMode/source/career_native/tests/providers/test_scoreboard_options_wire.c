#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../../src/host/scoreboard_options_wire.h"
int main(void)
{
    char wire[160];const char *hash="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    const char *invalid[]={"-1","1024","9999","01","1/../","1|OTHER","", "NaN"};unsigned i;
    for(i=0;i<sizeof(invalid)/sizeof(invalid[0]);++i){snprintf(wire,sizeof(wire),"S16SCORE1|%s|%s|END",hash,invalid[i]);assert(!scoreboard_options_wire_valid(wire));}
    for(i=0;i<1024;++i){snprintf(wire,sizeof(wire),"S16SCORE1|%s|%u|END",hash,i);assert(scoreboard_options_wire_valid(wire));}
    assert(!scoreboard_options_wire_valid(NULL));assert(!scoreboard_options_wire_valid("S16SCORE1|wrong|0|END"));
    puts("Scoreboard wire: 1024 valid indices; malformed, stale-shape and path payloads rejected");return 0;
}
