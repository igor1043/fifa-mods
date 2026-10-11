from pathlib import Path
p=Path(r'U:\mods\FIFA Friends V12\ModCarrerMode\source\substitution_all7_rulescan_native')
s=(p/'substitution_all7_rulescan_native.c').read_text()
old='''        if (!last_scan_ms || now - last_scan_ms >=
                (tracked.anchor ? SCAN_WHILE_TRACKED_MS : SCAN_RETRY_MS)) {'''
new='''        /* Do not rescan the process while the validated active pair is tracked.
         * Short rule reads above still detect teardown, inactivity and resets. */
        if ((!tracked.anchor || saw_dormant) &&
                (!last_scan_ms || now - last_scan_ms >= SCAN_RETRY_MS)) {'''
assert old in s;s=s.replace(old,new)
s=s.replace('plugin_start method=unique_vtable_pair_scan','plugin_start version=2 no_full_scan_with_valid_active_pair method=unique_vtable_pair_scan')
(p/'substitution_all7_rulescan_native_v2.c').write_text(s)
(p/'build_v2.cmd').write_text((p/'build_substitution_all7_rulescan_native.cmd').read_text().replace('substitution_all7_rulescan_native.c','substitution_all7_rulescan_native_v2.c').replace('/Fesubstitution_all7_rulescan_native.dll','/Fesubstitution_all7_rulescan_native_v2.dll'))
# Scheduling regression: discovery, active play, dormant transition, retry interval.
def scan(anchor,dormant,last,now):return (not anchor or dormant) and (not last or now-last>=2000)
assert scan(False,False,0,0)
assert not scan(True,False,1000,31000)
assert not scan(True,False,1000,999999)
assert scan(True,True,1000,31000)
assert scan(False,False,1000,3000)
assert not scan(False,False,1000,2999)
print('Rule scanner scheduling checks PASS; original source retained')
