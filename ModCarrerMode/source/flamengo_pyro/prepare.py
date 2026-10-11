"""Prepare the canonical, unversioned installed module from the studied revision."""
from pathlib import Path
from copy import deepcopy
import xml.etree.ElementTree as E
import runpy
p=Path(__file__).parent
runpy.run_path(str(p/'export_palettes.py'))
out=p/'build/assets'
source=(p/'flamengo_pyro_v17.cpp').read_text()
source=source.replace('flamengo_v17','flamengo_pyro').replace('flamengo_pyro_v17.log','flamengo_pyro.log')
source=source.replace('installed v17 automatic_intro_and_Flamengo_goals','installed automatic_intro_and_Flamengo_goals smoke_layers=2')
source=source.replace('particles/flamengo_1043.', 'particles/flamengo_pyro_1043.')
# Only the native callback is accepted. There is one loaded module, no legacy chain.
start=source.index('        if (!acceptable && target) {')
end=source.index('        if (check_signatures(image) && acceptable)',start)
source=source[:start]+source[end:]
source=source.replace('#include "goal_v11.h"','#include "goals.h"\n#include "teams.h"')
source=source.replace('static int clubSide=-1;\n','')
source=source.replace('if(home!=1043 && away!=1043)continue;', 'if(!pyro_team_valid(home) || !pyro_team_valid(away))continue;')
source=source.replace('clubSide=home==1043?0:1;key=(uintptr_t)row.bits;return key!=0;', 'key=pyro_team_key((uintptr_t)row.bits,(int)home,(int)away);return key!=0;')
source=source.replace('bool supported=false;', 'int clubIds[2]={};')
source=source.replace('if (!(clubId>0 && clubId<=1000000) || teamSide!=(double)i) return false;', 'if (!pyro_team_valid(clubId) || teamSide!=(double)i) return false;')
source=source.replace('if (clubId==1043) { supported=true; clubSide=i; }', 'clubIds[i]=(int)clubId;')
source=source.replace('return supported && key;', 'key=pyro_team_key(key,clubIds[0],clubIds[1]);return key!=0;')
source=source.replace('    clubSide=clubs[0]==1043?0:(clubs[1]==1043?1:-1);\n','')
source=source.replace('return key && (clubs[0]==1043 || clubs[1]==1043);','key=pyro_team_key(key,clubs[0],clubs[1]);return key!=0;')
source=source.replace('goals.update(now,home,away,clubSide)','goals.update(now,home,away)').replace('goals.update(now,h,a,clubSide)','goals.update(now,h,a)')
source=source.replace('FLAMENGO_GOAL_CONFIRMED','GOAL_CONFIRMED').replace('Flamengo=1043','teams=any asset=1043').replace('automatic_intro_and_Flamengo_goals','automatic_intro_and_any_team_goals')
source=source.replace('#include "teams.h"','#include "teams.h"\n#include "palette.h"')
source=source.replace('static bool goalShow=false;','static bool goalShow=false;\nstatic int matchHomeTeam=0;')
source=source.replace('key=pyro_team_key((uintptr_t)row.bits,(int)home,(int)away);return key!=0;', 'key=pyro_team_key((uintptr_t)row.bits,(int)home,(int)away);matchHomeTeam=(int)home;return key!=0;')
source=source.replace('key=pyro_team_key(key,clubIds[0],clubIds[1]);return key!=0;', 'key=pyro_team_key(key,clubIds[0],clubIds[1]);matchHomeTeam=clubIds[0];return key!=0;')
source=source.replace('key=pyro_team_key(key,clubs[0],clubs[1]);return key!=0;', 'key=pyro_team_key(key,clubs[0],clubs[1]);matchHomeTeam=clubs[0];return key!=0;')
source=source.replace('static void forget_resource() {','#include "palette_runtime.inc"\nstatic void forget_resource() {\n    paletteHome=0;paletteEffect=0;')
source=source.replace('    activeEffect=effect;\n    for (int i=0;i<active_count();++i)', '    activeEffect=effect;\n    if(!apply_home_palette())return false;\n    for (int i=0;i<active_count();++i)')
source=source.replace('GOAL_CONFIRMED automatic_show_armed','HOME_GOAL_CONFIRMED automatic_show_armed').replace('automatic_intro_and_any_team_goals','automatic_intro_and_home_goals')
source=source.replace('SHOW_STARTED confetti_red_black','SHOW_STARTED confetti_home_palette')
source=source.replace('goalShow=false; lifecycle=PyroLifecycle{};', 'goalShow=false; lifecycle=PyroLifecycle{}; paletteHome=0;paletteEffect=0;')
source=source.replace('#include "lifecycle_v17.h"','#include "lifecycle_v17.h"\n#include "ending.h"')
source=source.replace('static bool emitterStarted[emitterCount]={};','static bool emitterStarted[emitterCount]={};\nstatic bool emitterDraining[emitterCount]={};')
source=source.replace('        emitterStarted[i]=false;', '        emitterStarted[i]=false; emitterDraining[i]=false;')
source=source.replace('#include "native_signatures_v6.h"','#include "native_signatures.h"')
normal_end='''static void finish_naturally() {
    // Normally all sources drained for >=7s. If rendering stalled or was paused,
    // do not freeze/clear particles merely because wall-clock time has elapsed.
    if(showing && owned()) {
        bool waited=false;
        for(int i=0;i<active_count();++i)if(!emitterDraining[i] && valid_slot(i)) {
            if(!waited) {wait_jobs();waited=true;}
            ((Slot)(image+0x441c980))((void*)activeManager,handles[i]);
            emitterDraining[i]=true;
        }
    }
    showing=false;deadline=0;
    log_event("SHOW_FINISHED natural_fade particle_lists_retained");
}
'''
source=source.replace('static bool configure() {','static int active_count();\n'+normal_end+'static bool configure() {')
source=source.replace('if (pyro_show_expired(now,showStarted,goalShow)) { cleanup(); consumed=true; return; }','if (pyro_show_expired(now,showStarted,goalShow)) { finish_naturally(); consumed=true; return; }')
drain='''        for(int i=0;i<active_count();++i) {
            if(emitterStarted[i] && !emitterDraining[i] && pyro_drain_due(now,showStarted,goalShow,i)) {
                if(!waited) {wait_jobs();waited=true;}
                if(!valid_slot(i)) {cleanup();consumed=true;return;}
                // Native state 2 suppresses new emission but continues particle updates.
                ((Slot)(image+0x441c980))((void*)activeManager,handles[i]);
                emitterDraining[i]=true;
                if(i%2==0)log_event("SHOW_DRAIN_STEP paired_sources_stop_emitting existing_particles_fade");
            }
        }
'''
marker='''        return;
    }
    if (consumed) return;'''
assert marker in source
source=source.replace(marker,drain+marker)
source=source.replace('flamengo_pyro','stadium_pyrotechnics')
source=source.replace('assetId!=1043','assetId!=0').replace('const int asset=1043','const int asset=0').replace('asset=1043','asset=0').replace('stadium_pyrotechnics_1043','stadium_pyrotechnics_0')
source=source.replace('#include "ending.h"','#include "ending.h"\n#include "presentation.h"')
# Extract a real native fixture proof independently of the Lua preview metadata.
native_start=source.index('    uintptr_t manager=0,world=0,game=0,registry=0,pairs=0;')
native_end=source.index('    uintptr_t cache=0,rows=0; int home=0,away=0;',native_start)
native_body=source[native_start:native_end]
native_function='''static bool native_fixture(uintptr_t& key,int& home,int& away) {
'''+native_body+'''    home=clubs[0];away=clubs[1];
    key=registry ^ teams[0] ^ ((teams[1]<<11)|(teams[1]>>53));
    return key!=0;
}
static bool cachedFixture=false;
static uintptr_t fixtureKey=0;
static int fixtureHome=0,fixtureAway=0;
static ULONGLONG lastFixtureSample=0;
'''
source=source[:native_start]+'''    if(!cachedFixture)return false;
    const int clubs[2]={fixtureHome,fixtureAway};
'''+source[native_end:]
source=source.replace('    uintptr_t sceneKey=0;','    if(!cachedFixture)return false;\n    uintptr_t sceneKey=0;')
source=source.replace('if (stadium_match(sceneKey) || scene_match(sceneKey)) {',
    'if ((stadium_match(sceneKey) || scene_match(sceneKey)) && matchHomeTeam==fixtureHome) {')
source=source.replace('key=registry ^ rows ^ teams[0] ^ ((teams[1]<<11)|(teams[1]>>53));','key=fixtureKey ^ rows;')
source=source.replace('// Read only stadium metadata, without waiting for player tables.',native_function+'\n// Read only stadium metadata, without waiting for player tables.')
source=source.replace('static void cleanup() {\n    if (showing && owned()) {','static void cleanup(bool clearRetained=false) {\n    if ((showing || clearRetained) && owned()) {')
page_helpers='''static PyroPage currentPage=PyroPage::Unreadable;
static char currentPageName[64]={};
static ULONGLONG lastPageSample=0;
static bool menuCleared=false;
static void sample_presentation(ULONGLONG now) {
    if(!lastPageSample || now-lastPageSample>=250) {
        const unsigned int offsets[]={232,192,136,472,0};
        uintptr_t address=0;char page[64]={};
        const bool known=chain(58757168,offsets,address) && get(address,page) && memchr(page,0,sizeof(page));
        const PyroPage next=pyro_page(page,known);
        page[sizeof(page)-1]=0;
        if(next!=currentPage || strcmp(currentPageName,page)) {
            char event[160];
            page[sizeof(page)-1]=0;
            _snprintf_s(event,sizeof(event),_TRUNCATE,"PRESENTATION_PAGE kind=%d path=%s",(int)next,known?page:"<unreadable>");
            log_event(event);memcpy(currentPageName,page,sizeof(page));
        }
        currentPage=next;lastPageSample=now;
    }
    if(currentPage==PyroPage::Match || currentPage==PyroPage::Pause) {
        if(!lastFixtureSample || now-lastFixtureSample>=(consumed && !showing?2000ULL:500ULL)) {
            cachedFixture=native_fixture(fixtureKey,fixtureHome,fixtureAway);lastFixtureSample=now;
        }
    } else {cachedFixture=false;lastFixtureSample=0;}
}
'''
source=source.replace('static bool restarted(ULONGLONG now) {',page_helpers+'static bool restarted(ULONGLONG now) {')
restart_start=source.index('    uintptr_t stats=0,pageAddress=0;')
restart_end=source.index('\n}',restart_start)
source=source[:restart_start]+'''    uintptr_t stats=0;int clock=0,h=0,a=0;
    const bool valid=get(image+56299464,stats) && stats && get(stats+5500,clock) &&
        clock>=0 && clock<100000000 && read_score(h,a);
    return lifecycle.sample(valid,clock,h,a,currentPage!=PyroPage::Match,now);'''+source[restart_end:]
gate='''    if(!stopping) {
        sample_presentation(now);
        if(!pyro_can_continue(currentPage,cachedFixture,sessionKey!=0)) {
            // Clear retained particles once when entering a menu, including a finished show's tail.
            if(showing || (currentPage==PyroPage::Outside && !menuCleared && configured)) {
                uintptr_t impl=0;
                if(!same((uintptr_t)batch,image+0x2214500) || !get((uintptr_t)batch+0x10,impl) || !impl)return;
                batchImpl=impl;cleanup(currentPage==PyroPage::Outside);
            }
            if(currentPage==PyroPage::Outside) {
                if(sessionKey)log_event("MATCH_LEFT_FOR_MENU rearm_opening_and_home_goals");
                sessionKey=0;consumed=false;goalShow=false;goals=PyroGoals{};lifecycle=PyroLifecycle{};
                cachedMatch=false;cachedZero=false;lastMatchSample=0;lastValid=0;
                candidateSince=0;kickoffSince=0;showStarted=0;deadline=0;
                paletteHome=0;paletteEffect=0;menuCleared=true;
            }
            return;
        }
        menuCleared=false;
    }
    const bool canStart=pyro_can_start(currentPage,cachedFixture);
'''
source=source.replace('    if(sessionKey && restarted(now)) {',gate+'    if(sessionKey && restarted(now)) {')
source=source.replace('if(!stopping && !showing && consumed && sessionKey && cachedMatch &&','if(!stopping && canStart && !showing && consumed && sessionKey && cachedMatch &&')
source=source.replace('    // Preload in the first available batch while the player tables are still loading.',
    '    if(!canStart && !showing)return;\n    // Preload in the first available batch while the player tables are still loading.')
source=source.replace('if ((pendingGoal || (read_score(h,a) && goals.update(now,h,a))) && enabled)',
    'if (canStart && (pendingGoal || (read_score(h,a) && goals.update(now,h,a))) && enabled)')
source=source.replace('    if (consumed) return;','    if (!canStart || consumed) return;')
source=source.replace('installed automatic_intro_and_home_goals','installed presentation_gate_native_two_teams automatic_intro_and_home_goals')
# Preserve the Server16 integration authored concurrently in the other chat.
source=source.replace('#include "presentation.h"','#include "presentation.h"\n#include "match_presentation.h"')
source=source.replace('static PyroGoals goals;', 'static MatchPresentationConfig presentationConfig;\nstatic PyroGoals goals;')
source=source.replace('    lastSample=now;', '    lastSample=now;\n    const auto& presentation=presentationConfig.read((DWORD)now);')
source=source.replace('if(!showing)preload(now);','if(!showing && (presentation.entrance_allowed() || presentation.goal_allowed()))preload(now);')
source=source.replace('consumed=!automatic || !zero;', 'consumed=!automatic || !zero || !presentation.entrance_allowed();')
source=source.replace('consumed=wasIntro?false:!zero;', 'consumed=wasIntro?!presentation.entrance_allowed():!zero;')
source=source.replace('goals.update(now,h,a))) && enabled)', 'goals.update(now,h,a))) && enabled && presentation.goal_allowed())')
source=source.replace('    if (!enabled) return;\n    if (showing)', '''    if (!enabled) return;
    if (!(goalShow ? presentation.goal_allowed() : presentation.entrance_allowed())) {
        if(showing)cleanup();
        consumed=true;
        return;
    }
    if (showing)''')
source=source.replace('    automatic=true;', '''    automatic=true;
    if(!presentationConfig.initialize())return FALSE;
    log_event("match_presentation_config separate_intro_and_goal_switches poll_ms=250");''')
(p/'stadium_pyrotechnics.cpp').write_text(source)
build=(p/'build_v17.cmd').read_text().replace('flamengo_pyro_v17','flamengo_pyro')
build=build.replace('cl /nologo /std:c++17 /W4 /WX /O2 /MT /LD','cl /nologo /std:c++17 /W4 /WX /O2 /MT ending_test.cpp /Fobuild\\ /Febuild\\ending_test.exe /link /NOLOGO\nif errorlevel 1 exit /b 1\nbuild\\ending_test.exe\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /W4 /WX /O2 /MT /LD')
build=build.replace('cl /nologo /std:c++17 /W4 /WX /O2 /MT /LD','cl /nologo /std:c++17 /W4 /WX /O2 /MT teams_test.cpp /Fobuild\\ /Febuild\\teams_test.exe /link /NOLOGO\nif errorlevel 1 exit /b 1\nbuild\\teams_test.exe\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /W4 /WX /O2 /MT /LD')
build=build.replace('cl /nologo /std:c++17 /W4 /WX /O2 /MT /LD','cl /nologo /std:c++17 /W4 /WX /O2 /MT palette_test.cpp /Fobuild\\ /Febuild\\palette_test.exe /link /NOLOGO\nif errorlevel 1 exit /b 1\nbuild\\palette_test.exe\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /W4 /WX /O2 /MT /LD')
(p/'build.cmd').write_text(build.replace('flamengo_pyro','stadium_pyrotechnics'))
build_path=p/'build.cmd'
build_path.write_text(build_path.read_text().replace('cl /nologo /std:c++17 /W4 /WX /O2 /MT /LD',
    'cl /nologo /std:c++17 /W4 /WX /O2 /MT presentation_test.cpp /Fobuild\\ /Febuild\\presentation_test.exe /link /NOLOGO\nif errorlevel 1 exit /b 1\nbuild\\presentation_test.exe\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /W4 /WX /O2 /MT /LD'))
capture=Path(r'J:\mods\fifa 16\01_Projetos\mascotes\mod\diagnostics\20261007_102226_826631_mascot_native_observation\fifa16.image.bin')
with capture.open('rb') as binary:
    binary.seek(0x441c980);sig=binary.read(16)
guard=(p/'native_signatures_v6.h').read_text().replace('used by v6','used by the module')
guard=guard.replace('    return true;', '    const unsigned char sig11[16]={'+','.join(f'0x{x:02x}' for x in sig)+'};\n    if (!get(base+0x441c980,found) || memcmp(found,sig11,16)) return false;\n    return true;')
(p/'native_signatures.h').write_text(guard)
with capture.open('rb') as binary:
    for index,address in ((12,0x3c8e060),(13,0x45b0a70)):
        binary.seek(address);signature=binary.read(16)
        guard=guard.replace('    return true;', '    const unsigned char sig%d[16]={%s};\n    if (!get(base+0x%x,found) || memcmp(found,sig%d,16)) return false;\n    return true;'%(index,','.join(f'0x{x:02x}' for x in signature),address,index))
(p/'native_signatures.h').write_text(guard)

tree=E.parse(out/'flamengo_v17_1043.lnx')
effect=tree.getroot().find('particleEffect');effect.set('name','stadium_pyrotechnics')
for name in ('smoke_trail','smoke_base','smoke_black'):
    original=effect.find(f"particleGroup[@name='{name}']")
    assert original is not None
    clone=deepcopy(original);clone_name=name+'_overlay';clone.set('name',clone_name)
    for par in clone.iter('parameter'):
        value=par.get('value','')
        if par.get('name','').startswith('r') and value.startswith(name+'/'):
            par.set('value',clone_name+value[len(name):])
    effect.insert(list(effect).index(original)+1,clone)
tree.write(out/'stadium_pyrotechnics_0.lnx',encoding='utf-8')
(out/'stadium_pyrotechnics_0.rx3').write_bytes((out/'flamengo_v17_1043.rx3').read_bytes())

verify=(p/'verify_v17.py').read_text().replace('flamengo_v17','flamengo_pyro').replace('flamengo_pyro_v17','flamengo_pyro')
verify=verify.replace('len(groups)==8 and len(names)==8','len(groups)==11 and len(names)==11')
verify=verify.replace('capacity<54000','capacity==78010')
verify=verify.replace("native_signatures_v6.h", "native_signatures.h").replace('len(rvas)==len(signatures)==11','len(rvas)==len(signatures)==12').replace('11 runtime signature guards','12 runtime signature guards')
verify=verify.replace('len(rvas)==len(signatures)==12','len(rvas)==len(signatures)==14').replace('12 runtime signature guards','14 runtime signature guards')
verify+='''
# Overlay must preserve the emitter's location, velocity, palette and duration.
from copy import deepcopy
for name in ('smoke_trail','smoke_base','smoke_black'):
    original=effect.find("particleGroup[@name='%s']"%name)
    clone=deepcopy(effect.find("particleGroup[@name='%s_overlay']"%name))
    assert clone is not None
    clone.set('name',name)
    for par in clone.iter('parameter'):
        if par.get('name','').startswith('r'):
            par.set('value',par.get('value','').replace(name+'_overlay/',name+'/'))
    assert ET.tostring(original)==ET.tostring(clone),name
assert 'flamengo_pyro_v' not in source
assert 'flamengo_v' not in source
print('Two identical smoke layers at each source; rockets and confetti unchanged: PASS')
normal_end=source[source.index('static void finish_naturally()'):source.index('static bool configure()')]
assert '441c940' not in normal_end and '441c720' not in normal_end and '441c980' in normal_end
assert 'pyro_drain_due(now,showStarted,goalShow,i)' in source and '441c980' in source
assert 'finish_naturally(); consumed=true;' in source
assert 'emitterDraining[i]=false' in source
assert max(int(g.find("particleAction[@className='ParticleActionKillAge']/parameter[@name='iAgeMs']").get('value')) for g in groups)<=6500
print('Normal ending drains emission in pairs, preserves particles, and includes 7s tail within show duration: PASS')
matching=source[source.index('static bool stadium_match('):source.index('// Never pass a handle')]
assert '1043' not in matching and 'clubSide' not in source
assert matching.count('pyro_team_key(')==3
assert 'GOAL_CONFIRMED' in source and 'FLAMENGO_GOAL_CONFIRMED' not in source
assert 'goals.update(now,home,away)' in source and 'goals.update(now,h,a)' in source
print('Every validated team pair eligible; home-goal detection and home palette selection: PASS')
assert source.count('matchHomeTeam=')>=4
assert source.index('wait_jobs();',source.index('static bool emit()'))<source.index('apply_home_palette()',source.index('static bool emit()'))
palette_runtime=(root/'palette_runtime.inc').read_text()
assert 'paletteHome==matchHomeTeam && paletteEffect==activeEffect' in palette_runtime
assert 'pyro_palette(matchHomeTeam)' in palette_runtime
assert 'bindings[i].previous[3]' in palette_runtime
assert 'type!=8' in palette_runtime and 'length!=1' in palette_runtime
assert 'if(!apply_home_palette())return false;' in source
assert 'PALETTE_UNAVAILABLE' in palette_runtime
assert 'HOME_GOAL_CONFIRMED' in source
print('Palette applied before emission, cached per effect/home, alpha preserved, missing colors fail closed: PASS')
'''
verify=verify.replace('flamengo_pyro_1043','stadium_pyrotechnics_0').replace('flamengo_pyro','stadium_pyrotechnics')
verify=verify.replace("source.index('if(!showing)preload(now);')", "source.index('preload(now);',source.index('static void tick('))")
verify=verify.replace("source.index('static void cleanup()')", "source.index('static void cleanup(')")
verify+='''
assert tick.index('sample_presentation(now)')<tick.index('restarted(now)')<tick.index('// Dormant gameplay path:')
assert 'canStart && (pendingGoal ||' in tick
assert 'if (!canStart || consumed) return;' in tick
assert 'cleanup(currentPage==PyroPage::Outside)' in tick
assert 'cachedFixture=native_fixture(' in source
assert 'currentPage=next;lastPageSample=now;' in source
assert 'presentationConfig.read((DWORD)now)' in tick
assert 'presentation.entrance_allowed()' in tick and 'presentation.goal_allowed()' in tick
assert 'match_presentation.ini' in (root/'match_presentation.h').read_text()
print('Page/native-fixture gate precedes all triggers; menus rearm; Server16 switches retained: PASS')
'''
verify+="\nassert 'flamengo' not in source.lower()\nassert 'assetId!=0' in source and 'const int asset=0' in source\n"
(p/'verify.py').write_text(verify)
print('Prepared canonical module, effect, assets and log; three smoke overlays, existing event logic preserved')
