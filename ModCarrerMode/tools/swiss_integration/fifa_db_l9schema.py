#!/usr/bin/env python3
"""
fifa_db_l9schema.py - bringt eine FIFA-16-Datenbank (fifa_ng_db.db + fifa_ng_db-meta.xml)
auf das Feldschema von Linie 9. Enthaelt alle bisherigen Bit-Erweiterungen.

Was das Skript macht
  1. Zielschema: eingebettet ist das Schema der funktionierenden L9-DB (Stand 01.10.2026,
     2235 Integerfelder mit Bitbreite, rangelow, rangehigh). Darin stecken u. a.:
       - Namens-IDs: playernames 0..28999, dcplayernames ab 29000 (bis 120000), Spieler-Namensfelder
       - Spieler-/Team-/Stadion-IDs und alle Erweiterungen, die frueher mit DB Master gemacht wurden
       - formationid 12 Bit (formations bis 4095), customformations ab 4096 (rangelow 4096),
         temp_formations / teamformationteamstylelinks 13 Bit                      (L9-16)
       - Wettbewerbsknoten 13 Bit: career_competitionprogress.compobjid/stageid,
         career_users.primarycompobjid, career_newsban/managerawards/playerawards.compobjid,
         persistent_events.compobjid                                               (01.10.)
     Mit --ziel ANDERE_META.xml kann stattdessen jede andere Meta als Ziel dienen.
  2. Fuer jedes Integerfeld, das es in der Eingabe-DB gibt, wird es auf das Ziel GEBRACHT,
     wenn das Ziel breiter ist (mehr Bits, tieferes rangelow oder hoeheres rangehigh).
     Es wird NIE verkleinert. Felder/Tabellen, die nur in einer Seite existieren, bleiben.
  3. Tabellen MIT Datensaetzen werden umgepackt: nachfolgende Felder rutschen nach hinten,
     Strings bleiben byte-ausgerichtet, die Satzgroesse waechst bei Bedarf (Vielfaches von 4).
     Jeder Wert wird vor dem Schreiben auf den neuen Bereich geprueft.
  4. Sonderschritt Formationen 4096 (Standard an, abschaltbar mit --ohne-formationen4096):
     customformations-Saetze mit formationid < 4096 werden entfernt (Kopien bzw. alte eigene
     Formationen), damit der Bereich ab 4096 gesetzt werden kann. Passt zu L9-16.
  5. Alle Pruefsummen (CRC-32/MPEG-2) werden neu geschrieben: Dateikopf, Verzeichnis,
     Tabellenkoepfe und die Kette. Danach liest das Skript ALLE Tabellen neu ein und
     vergleicht jeden Wert mit dem Original.

Aufruf
  python3 fifa_db_l9schema.py fifa_ng_db.db fifa_ng_db-meta.xml AUSGABEORDNER [Optionen]
  Optionen:  --ziel META.xml           anderes Zielschema statt des eingebetteten
             --ohne-formationen4096     customformations nicht anfassen
             --nur-pruefen              nur auflisten, was geaendert wuerde
             --schema-export DATEI.json eingebettetes Zielschema als JSON ausgeben
             --nur MUSTER               nur passende Felder, z. B. --nur "formation|compobjid|stageid"

Hinweise
  - Ausgabe wird in einen eigenen Ordner geschrieben; die Eingabe bleibt unveraendert.
  - Nach einer Schemaaenderung lassen sich alte Karriere-Spielstaende nicht mehr laden.
  - String-, Real- und Datumsfelder werden nicht verbreitert.
"""
import struct, sys, os, re, json, zlib, base64, argparse

ZIEL_L9 = """
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
"""

def crc(b, c=0xFFFFFFFF):
    tab = crc.t
    for x in b:
        c = ((c << 8) & 0xFFFFFFFF) ^ tab[((c >> 24) ^ x) & 0xFF]
    return c
crc.t = []
for i in range(256):
    c = i << 24
    for _ in range(8):
        c = ((c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if c & 0x80000000 else (c << 1) & 0xFFFFFFFF
    crc.t.append(c)

def lade_db(D):
    nt = struct.unpack_from('<I', D, 0x10)[0]; dirend = 0x18 + nt * 8
    eintr = [(bytes(D[0x18+i*8:0x1c+i*8]), struct.unpack_from('<I', D, 0x1c+i*8)[0] + dirend) for i in range(nt)]
    return nt, dirend, eintr

def pruefe_crc(D):
    nt, dirend, eintr = lade_db(D); f = []
    if struct.unpack_from('<I', D, 8)[0] != len(D): f.append('Dateigroesse')
    if struct.unpack_from('<I', D, 0x14)[0] != crc(D[:0x14]): f.append('Kopf')
    offs = sorted(a for _, a in eintr)
    if crc(D[0x18:dirend]) != struct.unpack_from('<I', D, offs[0])[0]: f.append('Verzeichnis')
    for i, a in enumerate(offs):
        if struct.unpack_from('<I', D, a+0x24)[0] != crc(D[a+4:a+0x24]): f.append('Tabellenkopf %x' % a)
        end = offs[i+1] if i+1 < len(offs) else len(D) - 4
        if struct.unpack_from('<I', D, end)[0] != crc(D[a+0x28:end]): f.append('Kette %x' % a)
    return f

def lies_meta(text):
    tabs = {}
    for tm in re.finditer(r'<table name="([^"]+)" shortname="([^"]+)"[^>]*>(.*?)</table>', text, re.S):
        felder = {}
        for fm in re.finditer(r'<field ([^>]*?)/>', tm.group(3)):
            at = dict(re.findall(r'(\w+)="([^"]*)"', fm.group(1)))
            felder[at.get('name')] = at
        tabs[tm.group(1)] = (tm.group(2), felder)
    return tabs

class Tabelle:
    def __init__(self, D, a, ende):
        self.kopf = bytearray(D[a:a+0x28])
        self.rs = struct.unpack_from('<I', D, a+8)[0]
        self.nrec = struct.unpack_from('<H', D, a+0x14)[0]
        nf = D[a+0x1c]
        self.felder = [list(struct.unpack_from('<II4sI', D, a+0x28+j*16)) for j in range(nf)]
        base = a + 0x28 + nf*16
        self.saetze = [bytes(D[base+r*self.rs:base+(r+1)*self.rs]) for r in range(self.nrec)]
        self.rest = bytes(D[base+self.nrec*self.rs:ende])     # sollte leer sein
    def werte(self, lo_von):
        """alle Felder aller Saetze: dict kurzname -> Liste (int-Wert inkl. rangelow, sonst Rohbytes)"""
        out = {}
        for ty, bo, sn, dp in self.felder:
            lo = lo_von.get(sn, 0) if ty == 3 else 0
            v = []
            for s in self.saetze:
                if ty == 0: v.append(s[bo//8:bo//8+dp//8])
                else:
                    iv = int.from_bytes(s, 'little'); v.append(((iv >> bo) & ((1 << dp) - 1)) + lo)
            out[sn] = v
        return out
    def bytes_(self):
        b = bytearray(self.kopf)
        for f in self.felder: b += struct.pack('<II4sI', *f)
        for s in self.saetze: b += s
        return b + self.rest

def main():
    ap = argparse.ArgumentParser(description='FIFA 16 DB auf das L9-Feldschema bringen')
    ap.add_argument('db'); ap.add_argument('meta'); ap.add_argument('aus', nargs='?')
    ap.add_argument('--ziel'); ap.add_argument('--ohne-formationen4096', action='store_true')
    ap.add_argument('--nur-pruefen', action='store_true'); ap.add_argument('--schema-export')
    ap.add_argument('--nur', help='nur Felder, deren "tabelle.feld" auf diesen regulaeren Ausdruck passt')
    a = ap.parse_args()
    if a.ziel:
        ziel = {}
        for tn, (_, fl) in lies_meta(open(a.ziel, encoding='utf-8', errors='replace').read()).items():
            for fn, at in fl.items():
                if at.get('type') == 'DBOFIELDTYPE_INTEGER':
                    ziel[tn+'.'+fn] = [int(at['depth']), int(at.get('rangelow', 0)), int(at.get('rangehigh', 0))]
    else:
        ziel = json.loads(zlib.decompress(base64.b64decode(''.join(ZIEL_L9.split()))))
    if a.schema_export:
        json.dump(ziel, open(a.schema_export, 'w'), indent=0); print('Zielschema exportiert:', len(ziel), 'Felder')
        if not a.aus: return
    if not a.aus and not a.nur_pruefen: sys.exit('AUSGABEORDNER fehlt')

    D = bytearray(open(a.db, 'rb').read())
    f = pruefe_crc(D)
    if f: sys.exit('Eingabe-DB hat ungueltige Pruefsummen: %s' % f[:5])
    meta = open(a.meta, 'r', encoding='utf-8', newline='').read()
    mt = lies_meta(meta)
    nt, dirend, eintr = lade_db(D)
    offs = sorted(o for _, o in eintr)
    tab = {}
    for sn, o in eintr:
        i = offs.index(o); end = offs[i+1] if i+1 < len(offs) else len(D) - 4
        tab[sn] = Tabelle(D, o, end)
    name_zu_sn = {tn: sn.encode() for tn, (sn, _) in mt.items()}
    alt_werte = {}
    for tn, sn in name_zu_sn.items():
        if sn in tab:
            lo = {at['shortname'].encode(): int(at.get('rangelow', 0)) for at in mt[tn][1].values() if 'shortname' in at}
            alt_werte[tn] = tab[sn].werte(lo)

    aenderungen = []          # (tabelle, feld, alt(depth,lo,hi), neu(depth,lo,hi))
    meta_neu = meta
    # Sonderschritt Formationen 4096
    if not a.ohne_formationen4096 and ziel.get('customformations.formationid', [0, 0])[1] >= 4096 and 'customformations' in name_zu_sn:
        t = tab[name_zu_sn['customformations']]
        fsn = mt['customformations'][1]['formationid']['shortname'].encode()
        lo = int(mt['customformations'][1]['formationid'].get('rangelow', 0))
        vor = len(t.saetze)
        if lo < 4096 and vor:
            ids = alt_werte['customformations'][fsn]
            t.saetze = [s for s, v in zip(t.saetze, ids) if v >= 4096]
            entfernt = vor - len(t.saetze)
            alt_werte['customformations'] = {k: [x for x, v in zip(vals, ids) if v >= 4096] for k, vals in alt_werte['customformations'].items()}
            print('Formationen 4096: customformations %d Saetze mit formationid < 4096 entfernt' % entfernt)

    for tn, (sn_s, felder) in sorted(mt.items()):
        sn = sn_s.encode()
        if sn not in tab: continue
        t = tab[sn]
        plan = {}
        for fn, at in felder.items():
            if at.get('type') != 'DBOFIELDTYPE_INTEGER': continue
            z = ziel.get(tn+'.'+fn)
            if not z: continue
            if a.nur and not re.search(a.nur, tn+'.'+fn): continue
            d0, lo0, hi0 = int(at['depth']), int(at.get('rangelow', 0)), int(at.get('rangehigh', 0))
            dz, loz, hiz = z
            lo1 = min(lo0, loz) if not (fn == 'formationid' and tn == 'customformations' and loz >= 4096) else loz
            hi1 = max(hi0, hiz)
            d1 = max(d0, dz)
            while lo1 + (1 << d1) - 1 < hi1: d1 += 1
            if (d1, lo1, hi1) == (d0, lo0, hi0): continue
            vals = alt_werte.get(tn, {}).get(at['shortname'].encode(), [])
            if vals and (min(vals) < lo1 or max(vals) > lo1 + (1 << d1) - 1):
                print('  UEBERSPRUNGEN %s.%s: vorhandene Werte %d..%d passen nicht in %d..%d' % (tn, fn, min(vals), max(vals), lo1, lo1 + (1 << d1) - 1))
                continue
            plan[at['shortname'].encode()] = (d1, lo1, hi1, lo0)
            aenderungen.append((tn, fn, (d0, lo0, hi0), (d1, lo1, hi1), len(t.saetze)))
        if not plan: continue
        # neues Layout
        alt_layout = [list(f) for f in t.felder]
        ordnung = sorted(range(len(t.felder)), key=lambda j: t.felder[j][1])
        schub = 0
        neu_bo = {}
        for j in ordnung:
            ty, bo, fs, dp = t.felder[j]
            nb = bo + schub
            if ty == 0 and nb % 8: schub += 8 - nb % 8; nb = bo + schub
            neu_bo[j] = nb
            if fs in plan and ty == 3: schub += plan[fs][0] - dp
        ende = max(neu_bo[j] + (plan[t.felder[j][2]][0] if t.felder[j][2] in plan else t.felder[j][3]) for j in ordnung)
        rs_neu = max(t.rs, ((ende + 7) // 8 + 3) // 4 * 4)
        lo_alt = {at['shortname'].encode(): int(at.get('rangelow', 0)) for at in felder.values() if 'shortname' in at}
        neu_saetze = []
        for s in t.saetze:
            iv = int.from_bytes(s, 'little'); nv = 0; nb_ = bytearray(rs_neu)
            strings = []
            for j in range(len(t.felder)):
                ty, bo, fs, dp = alt_layout[j]
                if ty == 0:
                    strings.append((neu_bo[j] // 8, s[bo//8:bo//8+dp//8])); continue
                raw = (iv >> bo) & ((1 << dp) - 1)
                if ty == 3 and fs in plan:
                    d1, lo1, hi1, lo0 = plan[fs]
                    raw = raw + lo0 - lo1; dp = d1
                nv |= raw << neu_bo[j]
            nb_[:] = nv.to_bytes(rs_neu, 'little')
            for p, bb in strings: nb_[p:p+len(bb)] = bb
            neu_saetze.append(bytes(nb_))
        for j in range(len(t.felder)):
            t.felder[j][1] = neu_bo[j]
            if t.felder[j][2] in plan and t.felder[j][0] == 3: t.felder[j][3] = plan[t.felder[j][2]][0]
        t.saetze = neu_saetze
        if rs_neu != t.rs:
            struct.pack_into('<II', t.kopf, 8, rs_neu, rs_neu * 8 - 1); t.rs = rs_neu
        # Meta
        tm = re.search(r'(<table name="%s" shortname="[^"]+"[^>]*>)(.*?)(</table>)' % re.escape(tn), meta_neu, re.S)
        inner = tm.group(2)
        for fs, (d1, lo1, hi1, lo0) in plan.items():
            fm = re.search(r'<field [^>]*shortname="%s"[^>]*/>' % re.escape(fs.decode()), inner)
            alt_f = fm.group(0)
            neu_f = re.sub(r'depth="\d+"', 'depth="%d"' % d1, alt_f)
            neu_f = re.sub(r'rangelow="-?\d+"', 'rangelow="%d"' % lo1, neu_f)
            neu_f = re.sub(r'rangehigh="-?\d+"', 'rangehigh="%d"' % hi1, neu_f)
            inner = inner.replace(alt_f, neu_f, 1)
        meta_neu = meta_neu[:tm.start(2)] + inner + meta_neu[tm.end(2):]
    # Satzanzahl customformations aktualisieren
    for t in tab.values(): struct.pack_into('<HH', t.kopf, 0x14, len(t.saetze), len(t.saetze))

    print('%d Feldaenderungen:' % len(aenderungen))
    for tn, fn, alt, neu, n in aenderungen:
        print('  %-34s %-26s %2d Bit %d..%d  ->  %2d Bit %d..%d  (%d Saetze)' % (tn, fn, alt[0], alt[1], alt[2], neu[0], neu[1], neu[2], n))
    if a.nur_pruefen: return

    # Datei neu aufbauen
    teile = {o: tab[sn].bytes_() for sn, o in eintr}
    kopf = bytearray(D[:0x18]); verz = bytearray(D[0x18:dirend])
    neu_off = {}; pos = dirend
    for o in offs: neu_off[o] = pos; pos += len(teile[o])
    for i, (sn, o) in enumerate(eintr): struct.pack_into('<I', verz, i*8 + 4, neu_off[o] - dirend)
    N = kopf + verz
    for o in offs: N += teile[o]
    N += b'\0\0\0\0'
    struct.pack_into('<I', N, 8, len(N)); struct.pack_into('<I', N, 0x14, crc(N[:0x14]))
    no = [neu_off[o] for o in offs]
    struct.pack_into('<I', N, no[0], crc(N[0x18:dirend]))
    for x in no: struct.pack_into('<I', N, x + 0x24, crc(N[x+4:x+0x24]))
    for i, x in enumerate(no):
        end = no[i+1] if i+1 < len(no) else len(N) - 4
        struct.pack_into('<I', N, end, crc(N[x+0x28:end]))
    f = pruefe_crc(N)
    if f: sys.exit('Ausgabe fehlerhaft: %s' % f[:5])
    # Gegenprobe: alle Werte neu lesen
    mt2 = lies_meta(meta_neu); nt2, de2, e2 = lade_db(N); o2 = sorted(o for _, o in e2); fehler = 0
    for sn, o in e2:
        i = o2.index(o); end = o2[i+1] if i+1 < len(o2) else len(N) - 4
        t2 = Tabelle(N, o, end)
        tn = next((k for k, v in mt2.items() if v[0].encode() == sn), None)
        if tn is None or tn not in alt_werte: continue
        lo = {at['shortname'].encode(): int(at.get('rangelow', 0)) for at in mt2[tn][1].values() if 'shortname' in at}
        w2 = t2.werte(lo)
        for k, v in alt_werte[tn].items():
            if w2.get(k) != v: fehler += 1; print('  ABWEICHUNG', tn, k)
    if fehler: sys.exit('Gegenprobe fehlgeschlagen - nichts geschrieben')
    os.makedirs(a.aus, exist_ok=True)
    open(os.path.join(a.aus, 'fifa_ng_db.db'), 'wb').write(N)
    open(os.path.join(a.aus, 'fifa_ng_db-meta.xml'), 'w', encoding='utf-8', newline='').write(meta_neu)
    print('geschrieben: %d -> %d Byte; Pruefsummen gueltig; Gegenprobe: alle Werte aller Tabellen unveraendert' % (len(D), len(N)))

if __name__ == '__main__':
    main()
