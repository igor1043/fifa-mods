"""Read FIFA 16's installed T3DB and metadata without changing either file."""
from pathlib import Path
import struct
import xml.etree.ElementTree as ET


class FifaDatabase:
    def __init__(self, game, database_bytes=None, metadata_path=None, include_all_tables=False):
        game = Path(game)
        self.data = database_bytes if database_bytes is not None else (
            game / 'data/db/fifa_ng_db.db').read_bytes()
        if self.data[:4] != b'DB\0\x08':
            raise ValueError('Banco FIFA incompatível')
        metadata = ET.parse(metadata_path or game / 'data/db/fifa_ng_db-meta.xml')
        descriptions = {t.get('shortname'): t for t in metadata.iter('table')}
        count = self.u32(16)
        base = 28 + count * 8
        self.tables = {}
        for i in range(count):
            directory = 24 + i * 8
            key = self.data[directory:directory+4].decode('ascii')
            if key not in descriptions:
                continue
            meta = descriptions[key]
            if not include_all_tables and meta.get('name') not in (
                    'teams', 'leagues', 'leagueteamlinks', 'nations'):
                continue
            start = base + self.u32(directory + 4)
            stride = self.u32(start + 4)
            allocated, rows = struct.unpack_from('<HH', self.data, start + 16)
            field_count = self.data[start + 24]
            records = start + 36 + field_count * 16
            block = records + allocated * stride
            length = self.u32(start + 12)
            if rows > allocated or block + length > len(self.data):
                raise ValueError('Limites de tabela inválidos')
            names = {f.get('shortname'): f for f in meta.iter('field')}
            fields = {}
            for j in range(field_count):
                p = start + 36 + j * 16
                short = self.data[p+8:p+12].decode('ascii')
                if short not in names:
                    continue
                f = names[short]
                fields[f.get('name')] = (self.u32(p), self.u32(p+4), self.u32(p+12), int(f.get('rangelow', '0')))
            self.tables[meta.get('name')] = dict(stride=stride, rows=rows, records=records, block=block, length=length, fields=fields)

    def u32(self, offset):
        return struct.unpack_from('<I', self.data, offset)[0]

    def value(self, table, row, name):
        field = table['fields'].get(name)
        if field is None:
            return None
        kind, bit, depth, low = field
        record = table['records'] + row * table['stride']
        if kind in (3, 4):
            return sum(((self.data[record+(bit+k)//8] >> ((bit+k) % 8)) & 1) << k for k in range(depth)) + low
        if kind == 0:
            raw = self.data[record+bit//8:record+bit//8+depth//8].split(b'\0', 1)[0]
            return raw.decode('utf-8')
        if kind not in (13, 14):
            return None
        pointer = self.u32(record+bit//8)
        if pointer == 0xffffffff:
            return ''
        block, length = table['block'], table['length']
        prefix = 2 if kind == 14 else 1
        size = int.from_bytes(self.data[block+pointer:block+pointer+prefix], 'big')
        cursor, decoded = (pointer+prefix)*8, bytearray()
        for _ in range(size):
            node = 0
            for _ in range(32):
                if cursor >= length*8 or node*4+3 >= pointer:
                    raise ValueError('Texto comprimido inválido')
                side = (self.data[block+cursor//8] >> (7-cursor % 8)) & 1
                cursor += 1
                child, symbol = self.data[block+node*4+side*2:block+node*4+side*2+2]
                if child:
                    node = child
                else:
                    decoded.append(symbol)
                    break
            else:
                raise ValueError('Árvore de texto inválida')
        return decoded.decode('utf-8')

    def rows(self, name, fields):
        t = self.tables[name]
        return [{f: self.value(t, i, f) for f in fields} for i in range(t['rows'])]


def catalog(game):
    db = FifaDatabase(game)
    teams = {t['teamid']: t for t in db.rows('teams', [
        'teamid', 'teamname', 'latitude', 'longitude', 'domesticprestige',
        'overallrating', 'attackrating', 'midfieldrating', 'defenserating',
        'teamcolor1r', 'teamcolor1g', 'teamcolor1b',
    ])}
    nations = {n['nationid']: n for n in db.rows('nations', ['nationid', 'nationname', 'isocountrycode'])}
    leagues = db.rows('leagues', ['leagueid', 'leaguename', 'countryid', 'level'])
    links = db.rows('leagueteamlinks', ['teamid', 'leagueid', 'secondarytable'])
    for league in leagues:
        league['country'] = nations.get(league['countryid'], {})
        ids = {r['teamid'] for r in links if r['leagueid'] == league['leagueid'] and not r['secondarytable']}
        league['clubs'] = sorted([teams[i] for i in ids if i in teams], key=lambda t: t['teamname'])
    return leagues
