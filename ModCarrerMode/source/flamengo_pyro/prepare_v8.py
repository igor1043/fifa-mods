from pathlib import Path
import xml.etree.ElementTree as E
p=Path(__file__).parent
s=(p/'flamengo_pyro_v7.cpp').read_text().replace('flamengo_v7','flamengo_v8').replace('flamengo_pyro_v7.log','flamengo_pyro_v8.log')
s=s.replace('#include "timing_v6.h"','#include "timing_v6.h"\n#include "goal_v8.h"')
s=s.replace('static bool enabled=false, automatic=false, f7Down=false, f9Down=false;','static bool enabled=true, automatic=true;\nstatic int clubSide=-1;\nstatic PyroGoals goals;\nstatic bool goalShow=false;')
s=s.replace('if (clubId==1043) supported=true;','if (clubId==1043) { supported=true; clubSide=i; }')
s=s.replace('scoreZero=home==0 && away==0;\n    key=registry','clubSide=clubs[0]==1043?0:(clubs[1]==1043?1:-1);\n    scoreZero=home==0 && away==0;\n    key=registry')
start=s.index('    // Default opt-in.')
end=s.index('    uintptr_t key=0; bool zero=false;',start)
s=s[:start]+'    // Fully automatic: keyboard input cannot arm, cancel or restart the show.\n'+s[end:]
s=s.replace('now-lastValid>2000','now-lastValid>30000')
s=s.replace('candidateSince=now; kickoffSince=0;\n    }','candidateSince=now; kickoffSince=0; goals=PyroGoals{}; goalShow=false;\n        log_event("MATCH_DETECTED automatic_intro_armed");\n    }',1)
start=s.index('    if (request && enabled)')
end=s.index('    if (!enabled) return;',start)
s=s[:start]+'''    int h=0,a=0;
    if (read_score(h,a) && goals.update(now,h,a,clubSide) && enabled) {
        cleanup(); consumed=false; candidateSince=now; kickoffSince=0; goalShow=true;
        log_event("FLAMENGO_GOAL_CONFIRMED automatic_show_armed");
    }
'''+s[end:]
s=s.replace('if (pyro_expired(now,showStarted,kickoffSince))','if (goalShow ? (now<showStarted || now-showStarted>=8000) : pyro_expired(now,showStarted,kickoffSince))')
s=s.replace('static bool gameplay_present() {','''static bool read_score(int& home,int& away) {
    uintptr_t cache=0,rows=0,again=0; int h2=0,a2=0;
    return get(image+0x34a30b0,cache) && same(cache,image+0x21141f0) &&
        get(cache+8,rows) && same(rows+21*16+8,image+0x3acc040) &&
        same(rows+6*16+8,image+0x3acc040) && get(rows+21*16,home) &&
        get(rows+6*16,away) && home>=0 && home<=99 && away>=0 && away<=99 &&
        get(rows+21*16,h2) && get(rows+6*16,a2) && h2==home && a2==away &&
        get(image+0x34a30b0,again) && again==cache;
}
static bool gameplay_present() {''')
s=s.replace('installed v7 confetti_red_black six_emitters opt_in F7_enable F8_start F9_stop no_instance_delete','installed v8 automatic_intro_and_Flamengo_goals no_hotkeys finite_confetti no_instance_delete')
s=s.replace('enabled=GetPrivateProfileIntA("pyro","enabled",0,configPath)!=0;','enabled=GetPrivateProfileIntA("pyro","enabled",1,configPath)!=0;')
s=s.replace('automatic=GetPrivateProfileIntA("pyro","automatic",0,configPath)!=0;','automatic=true;')
s=s.replace('static bool consumed, configured, keyDown;','static bool consumed, configured;')
(p/'flamengo_pyro_v8.cpp').write_text(s)
b=(p/'build_v7.cmd').read_text().replace('flamengo_pyro_v7','flamengo_pyro_v8')
b=b.replace('cl /nologo /std:c++17 /W4 /WX /O2 /MT /LD', 'cl /nologo /std:c++17 /W4 /WX /O2 /MT goal_v8_test.cpp /Fobuild\\ /Febuild\\goal_v8_test.exe /link /NOLOGO\nif errorlevel 1 exit /b 1\nbuild\\goal_v8_test.exe\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /W4 /WX /O2 /MT /LD')
(p/'build_v8.cmd').write_text(b)
out=p/'build'/'assets'
tree=E.parse(out/'flamengo_v7_1043.lnx');tree.getroot().find('particleEffect').set('name','flamengo_v8')
tree.write(out/'flamengo_v8_1043.lnx',encoding='utf-8')
(out/'flamengo_v8_1043.rx3').write_bytes((out/'flamengo_v7_1043.rx3').read_bytes())
(p/'verify_v8.py').write_text((p/'verify_v7.py').read_text().replace('flamengo_v7','flamengo_v8').replace('flamengo_pyro_v7','flamengo_pyro_v8'))
install=(p/'install_v7.py').read_text().replace('v7_teste','v8_teste').replace('flamengo_pyro_v7','flamengo_pyro_v8').replace('flamengo_v7','flamengo_v8').replace('pyro v7: opt-in via F7/pyro.ini','pyro v8: automatic intro and Flamengo goals').replace('Installed v7, effects disabled by default','Installed v8, effects automatic by default')
install=install.replace('enabled=0','enabled=1').replace('; F7 habilita/desabilita. F8 dispara. F9 para.','; Automatico: abertura e gols do Flamengo. Sem teclas.').replace("'effect_default':'disabled'","'effect_default':'enabled'")
(p/'install_v8.py').write_text(install)
print('v8 prepared: automatic intro, confirmed Flamengo goals, no hotkeys, finite asset unchanged')
