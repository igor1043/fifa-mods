"""Build the portable club globe from the installed FIFA 16 catalog."""
import argparse
import base64
import configparser
import csv
import io
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unicodedata
import zlib
import zipfile
from PIL import Image, ImageDraw, ImageFont
from fifa_db import FifaDatabase, catalog
from club_save_details import build_detail

ROOT = Path(__file__).resolve().parent
CAREER_NATIVE = ROOT.parents[1] / 'source' / 'career_native'
NATIVE_ATTRIBUTE_FIELDS = (
    'acceleration', 'sprintspeed', 'agility', 'reactions', 'balance', 'shotpower',
    'finishing', 'longshots', 'volleys', 'penalties', 'vision', 'crossing',
    'shortpassing', 'longpassing', 'curve', 'freekickaccuracy', 'ballcontrol',
    'dribbling', 'strength', 'stamina', 'jumping', 'aggression', 'interceptions',
    'positioning', 'marking', 'standingtackle', 'slidingtackle', 'headingaccuracy',
    'gkdiving', 'gkhandling', 'gkkicking', 'gkpositioning', 'gkreflexes', 'potential',
)
PLAYER_APPEARANCE_FIELDS = (
    'headtypecode', 'headclasscode', 'hairtypecode', 'haircolorcode', 'skintonecode',
    'skintypecode', 'facialhairtypecode', 'facialhaircolorcode', 'shoetypecode',
    'shoedesigncode', 'gender', 'height', 'weight', 'bodytypecode', 'eyecolorcode',
    'eyebrowcode', 'sideburnscode', 'jerseysleevelengthcode', 'jerseyfit',
    'jerseystylecode', 'socklengthcode', 'shortstyle', 'gkglovetypecode',
)
POSITION_LABELS = (
    'GOL', 'LIB', 'ALA D', 'LD', 'ZAG D', 'ZAG', 'ZAG E', 'LE', 'ALA E',
    'VOL D', 'VOL', 'VOL E', 'MD', 'MC D', 'MC', 'MC E', 'ME', 'MEI D',
    'MEI', 'MEI E', 'SA D', 'SA', 'SA E', 'PD', 'ATA D', 'ATA', 'ATA E', 'PE',
)
ISO3 = {
    'AR':'ARG','AT':'AUT','BE':'BEL','BO':'BOL','BR':'BRA','CL':'CHL','CN':'CHN',
    'CO':'COL','HR':'HRV','CZ':'CZE','DK':'DNK','EC':'ECU','GB':'GBR','FR':'FRA',
    'DE':'DEU','GR':'GRC','IT':'ITA','JP':'JPN','MX':'MEX','NL':'NLD','NO':'NOR',
    'PE':'PER','PL':'POL','PT':'PRT','QA':'QAT','KR':'KOR','RO':'ROU','SA':'SAU',
    'ES':'ESP','SE':'SWE','CH':'CHE','TR':'TUR','UA':'UKR','US':'USA','UY':'URY',
    'VE':'VEN','IE':'IRL',
}
COUNTRY_NAME_PT = {
    'AR': 'Argentina', 'AT': 'Áustria', 'BE': 'Bélgica', 'BO': 'Bolívia',
    'BR': 'Brasil', 'CH': 'Suíça', 'CL': 'Chile', 'CN': 'China',
    'CO': 'Colômbia', 'CZ': 'República Tcheca', 'DE': 'Alemanha',
    'DK': 'Dinamarca', 'EC': 'Equador', 'ES': 'Espanha', 'FR': 'França',
    'GB': 'Inglaterra', 'GR': 'Grécia', 'HR': 'Croácia', 'IE': 'Irlanda',
    'IT': 'Itália', 'JP': 'Japão', 'KR': 'Coreia do Sul', 'MX': 'México',
    'NL': 'Países Baixos', 'NO': 'Noruega', 'PE': 'Peru', 'PL': 'Polônia',
    'PT': 'Portugal', 'PY': 'Paraguai', 'QA': 'Catar', 'RO': 'Romênia',
    'SA': 'Arábia Saudita', 'SE': 'Suécia', 'TR': 'Turquia', 'UA': 'Ucrânia',
    'US': 'Estados Unidos', 'UY': 'Uruguai', 'VE': 'Venezuela',
}
CLUB_COORDINATES = {
    # GeoNames city15000 omits these smaller towns; keep the selected label and
    # place the marker at the town/club location rather than another country.
    130903: ('El Alto', -16.5048, -68.1624),
    130243: ('Bulo Bulo (Entre Ríos)', -17.25412, -64.36429),
    101147: ('Kashima', 35.965, 140.644),
    130267: ('Venda Nova do Imigrante', -20.3326, -41.1296),
    130465: ('Nova Veneza', -28.63737, -49.49976),
    130417: ('Castelo', -20.60361, -41.18472),
    # The Federal District league also includes clubs from nearby Goiás.
    130263: ('Formosa', -15.53722, -47.33444),
    113124: ('Luziânia', -16.2525, -47.95028),
}
BRAZIL_STATE_CAPITALS = {
    'AC': 'Rio Branco', 'AL': 'Maceió', 'AP': 'Macapá', 'AM': 'Manaus',
    'BA': 'Salvador', 'CE': 'Fortaleza', 'DF': 'Brasília', 'ES': 'Vitória',
    'GO': 'Goiânia', 'MA': 'São Luís', 'MT': 'Cuiabá', 'MS': 'Campo Grande',
    'MG': 'Belo Horizonte', 'PA': 'Belém', 'PB': 'João Pessoa', 'PR': 'Curitiba',
    'PE': 'Recife', 'PI': 'Teresina', 'RJ': 'Rio de Janeiro', 'RN': 'Natal',
    'RS': 'Porto Alegre', 'RO': 'Porto Velho', 'RR': 'Boa Vista',
    'SC': 'Florianópolis', 'SP': 'São Paulo', 'SE': 'Aracaju', 'TO': 'Palmas',
}
BRAZIL_ADMIN1_TO_UF = {
    '01': 'AC', '02': 'AL', '03': 'AP', '04': 'AM', '05': 'BA', '06': 'CE',
    '07': 'DF', '08': 'ES', '11': 'MS', '13': 'MA', '14': 'MT', '15': 'MG',
    '16': 'PA', '17': 'PB', '18': 'PR', '20': 'PI', '21': 'RJ', '22': 'RN',
    '23': 'RS', '24': 'RO', '25': 'RR', '26': 'SC', '27': 'SP', '28': 'SE',
    '29': 'GO', '30': 'PE', '31': 'TO',
}
BRAZIL_FEDERATION_STATES = {
    2: 'PI', 34: 'MA', 35: 'AL', 43: 'MT', 44: 'RN', 45: 'PB',
    48: 'AM', 86: 'RO', 90: 'MS', 92: 'TO', 94: 'RR', 95: 'AP',
    96: 'AC', 100: 'PR', 101: 'SP', 102: 'SC', 103: 'RS', 104: 'MG',
    105: 'RJ', 107: 'SE', 108: 'GO', 109: 'PA', 112: 'DF', 113: 'PE',
    114: 'BA', 115: 'CE', 1004: 'ES',
}
BRAZIL_LEAGUE_ORDER = (7, 83, 350, 351, 352, 355, 356, 354)


def normalize_name(value):
    text = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii').casefold()
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def load_geo_sources():
    alpha3 = {}
    for line in (ROOT / 'vendor/countryInfo.txt').read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            fields = line.split('\t')
            alpha3[fields[0]] = fields[1]
    city_rows = []
    with zipfile.ZipFile(ROOT / 'vendor/cities15000.zip') as archive:
        with archive.open('cities15000.txt') as data:
            for raw in data:
                fields = raw.decode('utf-8').rstrip('\r\n').split('\t')
                city_rows.append({
                    'name': fields[1], 'normalized': normalize_name(fields[1]),
                    'aliases': [normalize_name(value) for value in fields[3].split(',')
                                if len(normalize_name(value)) >= 4],
                    'lat': float(fields[4]), 'lon': float(fields[5]),
                    'iso2': fields[8], 'admin1': fields[10], 'feature': fields[7],
                    'population': int(fields[14] or '0'),
                })
    by_country = {}
    by_name = {}
    for city in city_rows:
        by_country.setdefault(city['iso2'], []).append(city)
        if len(city['normalized']) >= 4:
            by_name.setdefault((city['iso2'], city['normalized']), []).append(city)
    for cities in by_country.values():
        cities.sort(key=lambda item: item['population'], reverse=True)
    by_state = {}
    for city in by_country.get('BR', []):
        state = BRAZIL_ADMIN1_TO_UF.get(city['admin1'])
        if state:
            by_state.setdefault(state, []).append(city)
    return alpha3, city_rows, by_country, by_name, by_state


def load_game_localization(game):
    """Read the installed game's Portuguese UI names without editing the game."""
    game = Path(game)
    database = game / 'data/loc/por_br.db'
    metadata = game / 'data/loc/por_br-meta.xml'
    if not database.is_file() or not metadata.is_file():
        return {}
    try:
        locale = FifaDatabase(game, database.read_bytes(), metadata, include_all_tables=True)
        rows = locale.rows('LanguageStrings', ['stringid', 'sourcetext'])
    except (OSError, ValueError, KeyError):
        return {}
    return {row['stringid']: row['sourcetext'] for row in rows
            if row['stringid'] and row['sourcetext']}


def distance_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(min(1.0, a)))


def inside_ring(lon, lat, ring):
    inside = False
    for index, (x2, y2) in enumerate(ring):
        x1, y1 = ring[index - 1]
        if (y1 > lat) != (y2 > lat):
            crossing = (x2 - x1) * (lat - y1) / (y2 - y1 + 1e-40) + x1
            if lon < crossing:
                inside = not inside
    return inside


def inside_geometry(lon, lat, geometry):
    if not geometry:
        return False
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    for polygon in polygons:
        if inside_ring(lon, lat, polygon[0]) and not any(
                inside_ring(lon, lat, ring) for ring in polygon[1:]):
            return True
    return False


def choose_city(candidates, lat, lon):
    if not candidates:
        return None
    return min(candidates, key=lambda city: distance_km(lat, lon, city['lat'], city['lon']))


def named_city(team_name, country_cities, lat=None, lon=None):
    normalized = ' ' + normalize_name(team_name) + ' '
    matches = []
    for city in country_cities:
        key = city['normalized']
        if len(key) >= 4 and (' ' + key + ' ') in normalized:
            matches.append((len(key), city))
    if matches:
        longest = max(length for length, _ in matches)
        matches = [city for length, city in matches if length == longest]
        return choose_city(matches, lat, lon) if lat is not None and lon is not None else max(
            matches, key=lambda item: item['population'])

    # FIFA club names often use a common-language spelling instead of the
    # GeoNames primary spelling (e.g. Moscow/Moskva, Aarhus/Århus). Accept an
    # alternate spelling only when it identifies one city, or when a nearby
    # FIFA point disambiguates multiple places with that spelling. Ambiguous
    # aliases such as "Rio Branco" must not override a full city-name match.
    alias_matches = []
    for city in country_cities:
        for alias in city['aliases']:
            if len(alias) >= 4 and (' ' + alias + ' ') in normalized:
                alias_matches.append((len(alias), city))
                break
    if alias_matches:
        longest = max(length for length, _ in alias_matches)
        candidates = list({city['name']: city for length, city in alias_matches
                           if length == longest}.values())
        if len(candidates) == 1:
            return candidates[0]
        if lat is not None and lon is not None:
            nearest = choose_city(candidates, lat, lon)
            if distance_km(lat, lon, nearest['lat'], nearest['lon']) <= 75:
                return nearest
    return None


def city_by_label(label, iso2, by_name, expected_state=None):
    key = normalize_name(label)
    candidates = by_name.get((iso2, key), [])
    if expected_state:
        candidates = [city for city in candidates
                      if BRAZIL_ADMIN1_TO_UF.get(city.get('admin1')) == expected_state]
    if candidates:
        return max(candidates, key=lambda item: item['population'])
    return None


def approximate_region_city(cities, lat, lon):
    nearest = choose_city(cities, lat, lon)
    if nearest and distance_km(lat, lon, nearest['lat'], nearest['lon']) <= 300:
        return nearest
    return None


def resolve_location(team, iso2, iso3, setting, city_override, country_cities,
                     all_cities, cities_by_name, world_geometry, capitals,
                     federation_state=None, cities_by_state=None):
    team_id = int(team['teamid'])
    raw_lat, raw_lon = float(team['latitude']), float(team['longitude'])
    zoom = min(4.5, max(2.7, float(setting.get('zoom', '2.7')) * 1.10))
    if setting.get('city') and setting.get('lat') and setting.get('lon'):
        lat, lon = float(setting['lat']), float(setting['lon'])
        return setting['city'], lat, lon, zoom, 'verified'

    if team_id in CLUB_COORDINATES:
        city, lat, lon = CLUB_COORDINATES[team_id]
        return city, lat, lon, zoom, 'verified'

    state_cities = (cities_by_state or {}).get(federation_state, []) if federation_state else []
    if federation_state:
        if city_override:
            city = city_by_label(city_override, 'BR', cities_by_name, federation_state)
            if city:
                return city['name'], city['lat'], city['lon'], zoom, 'verified'

        text_city = named_city(team['teamname'], state_cities, raw_lat, raw_lon)
        if text_city:
            return text_city['name'], text_city['lat'], text_city['lon'], zoom, 'name-match'

        # Federation rosters identify the state even when FIFA's point is in
        # another country. Use a nearby city only if the point is city-level
        # and close to a city inside this state; otherwise use the state capital
        # as an explicitly approximate regional marker.
        if raw_lat.is_integer() is False and raw_lon.is_integer() is False and state_cities:
            nearest = choose_city(state_cities, raw_lat, raw_lon)
            if distance_km(raw_lat, raw_lon, nearest['lat'], nearest['lon']) <= 35:
                return nearest['name'], nearest['lat'], nearest['lon'], zoom, 'nearby-city'
        capital_name = BRAZIL_STATE_CAPITALS.get(federation_state)
        capital = city_by_label(capital_name, 'BR', cities_by_name, federation_state) if capital_name else None
        if capital:
            return f"Região de {capital['name']}", capital['lat'], capital['lon'], zoom, 'region'
        return 'Região aproximada', 0.0, 0.0, zoom, 'region'

    if city_override:
        city = city_by_label(city_override, iso2, cities_by_name)
        if city:
            return city_override, city['lat'], city['lon'], zoom, 'verified'
        if iso2 == 'JP' and normalize_name(city_override) == 'kashima':
            return city_override, 35.965, 140.644, zoom, 'verified'

    point_valid = -90 <= raw_lat <= 90 and -180 <= raw_lon <= 180
    matches_country = point_valid and inside_geometry(
        raw_lon, raw_lat, world_geometry.get(iso3))

    if country_cities and team_id:
        text_city = named_city(team['teamname'], country_cities, raw_lat, raw_lon)
        if text_city:
            # Choose the intended city spelling from the team's own name.
            return text_city['name'], text_city['lat'], text_city['lon'], zoom, 'name-match'

    # Brazilian state-coded clubs often inherit unrelated DB coordinates.
    if iso2 == 'BR':
        state_match = re.search(r'\b([A-Z]{2})\b', str(team['teamname']))
        if state_match and state_match.group(1) in BRAZIL_STATE_CAPITALS:
            city_name = BRAZIL_STATE_CAPITALS[state_match.group(1)]
            city = city_by_label(city_name, 'BR', cities_by_name)
            if city:
                # A state suffix narrows the location to a state, not a city.
                return f"Região de {city['name']}", city['lat'], city['lon'], zoom, 'region'

    if matches_country:
        nearest = choose_city(country_cities, raw_lat, raw_lon)
        if nearest:
            # Integer-degree FIFA points are too coarse to identify a city:
            # Arsenal, Brentford, and Crystal Palace all use (51, 0), which is
            # near Haywards Heath even though those clubs are in London. Only
            # infer a nearby city from fractional coordinates and a short
            # radius. Otherwise retain the game's point as an approximate area.
            has_city_level_point = not raw_lat.is_integer() and not raw_lon.is_integer()
            if has_city_level_point and distance_km(
                    raw_lat, raw_lon, nearest['lat'], nearest['lon']) <= 35:
                return nearest['name'], nearest['lat'], nearest['lon'], zoom, 'nearby-city'
            return 'Região aproximada', raw_lat, raw_lon, zoom, 'region'

    regional = approximate_region_city(country_cities, raw_lat, raw_lon) if point_valid else None
    if regional:
        return f"Região de {regional['name']}", regional['lat'], regional['lon'], zoom, 'region'

    # For a bad/missing FIFA point, use a representative point inside the
    # country and state clearly that the club city could not be verified.
    capital = capitals.get(iso2)
    if capital:
        return f"Região de {capital['name']}", capital['lat'], capital['lon'], zoom, 'region'
    if country_cities:
        largest = country_cities[0]
        return f"Região de {largest['name']}", largest['lat'], largest['lon'], zoom, 'region'

    # Rest-of-world clubs without a country are matched to a city name where
    # possible; otherwise they stay in a neutral fallback region.
    global_city = named_city(team['teamname'], all_cities, raw_lat, raw_lon)
    if global_city:
        return global_city['name'], global_city['lat'], global_city['lon'], zoom, 'name-match'
    if -90 <= raw_lat <= 90 and -180 <= raw_lon <= 180 and (raw_lat or raw_lon):
        nearest = choose_city(all_cities, raw_lat, raw_lon)
        if nearest:
            return 'Região aproximada', nearest['lat'], nearest['lon'], zoom, 'region'
    return 'Região aproximada', 0.0, 0.0, zoom, 'region'


def big_asset_index(game):
    indexed = {}
    prefixes = ('data/ui/imgassets/flags512x512/f_',
                'data/ui/imgassets/league/dark/l')
    for archive in game.glob('*.big'):
        try:
            with archive.open('rb') as stream:
                header = stream.read(16)
                if len(header) < 16 or header[:4] not in (b'BIG4', b'BIGF'):
                    continue
                count, directory_end = struct.unpack_from('>II', header, 8)
                size = archive.stat().st_size
                if count > 2_000_000 or not 16 <= directory_end <= min(size, 32 * 1024 * 1024):
                    continue
                directory = header + stream.read(directory_end - 16)
                cursor = 16
                for _ in range(count):
                    if cursor + 9 > len(directory):
                        break
                    offset, length = struct.unpack_from('>II', directory, cursor)
                    end = directory.find(b'\0', cursor + 8)
                    if end < 0:
                        break
                    name = directory[cursor + 8:end].decode('latin1').replace('\\', '/').casefold()
                    cursor = end + 1
                    if name.startswith(prefixes) and offset + length <= size:
                        indexed.setdefault(name, (archive, offset, length))
        except (OSError, ValueError, struct.error):
            continue
    return indexed


def decode_asset_container(data):
    if data.startswith(b'DDS '):
        return data
    if data.startswith(b'chunkzip') and len(data) >= 32:
        version, size = struct.unpack_from('>II', data, 8)
        count = struct.unpack_from('>I', data, 20)[0]
        if version != 2 or not 0 < size <= 64 * 1024 * 1024 or not 0 < count <= 1024:
            return None
        cursor, decoded = 32, bytearray()
        for _ in range(count):
            cursor = (cursor + 3) & ~3
            skipped = 0
            while cursor + 4 <= len(data) and data[cursor:cursor + 4] == b'\0\0\0\0' and skipped < 16:
                cursor += 4
                skipped += 1
            if cursor + 8 > len(data):
                return None
            stored, flag = struct.unpack_from('>II', data, cursor)
            cursor += 8
            if flag != 1 or not stored or cursor + stored > len(data):
                return None
            try:
                block = zlib.decompress(data[cursor:cursor + stored], -15)
            except zlib.error:
                return None
            if len(decoded) + len(block) > size:
                return None
            decoded.extend(block)
            cursor += stored
        return bytes(decoded) if len(decoded) == size and decoded.startswith(b'DDS ') else None
    return None


def render_game_icon(game, archive_index, relative_path, target, inline=False):
    if target.is_file() and not inline:
        return target.relative_to(ROOT).as_posix(), None
    source = game / Path(relative_path)
    data = source.read_bytes() if source.is_file() else None
    if data is None:
        archive_item = archive_index.get(relative_path.replace('\\', '/').casefold())
        if archive_item:
            archive, offset, length = archive_item
            with archive.open('rb') as stream:
                stream.seek(offset)
                data = stream.read(length)
    if not data:
        return '', None
    data = decode_asset_container(data)
    if not data:
        return '', None
    try:
        with Image.open(io.BytesIO(data)) as original:
            image = original.convert('RGBA')
            image.thumbnail((112, 112), Image.Resampling.LANCZOS)
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target, format='WEBP', quality=84, method=3)
            embed = None
            if inline:
                out = io.BytesIO()
                image.save(out, format='WEBP', quality=58, method=0)
                embed = 'data:image/webp;base64,' + base64.b64encode(out.getvalue()).decode('ascii')
            return target.relative_to(ROOT).as_posix(), embed
    except (OSError, ValueError):
        return '', None


def render_placeholder_icon(target, label):
    image = Image.new('RGBA', (112, 72), '#122334')
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 1, 110, 70), radius=6, outline='#49657d', width=2)
    draw.line((8, 55, 104, 55), fill='#29435a', width=3)
    try:
        font = ImageFont.truetype('arial.ttf', 23)
    except OSError:
        font = ImageFont.load_default()
    text = ''.join(word[0] for word in label.split()[:2]).upper() or 'FF'
    bounds = draw.textbbox((0, 0), text, font=font)
    draw.text(((112 - bounds[2]) / 2, (72 - bounds[3]) / 2 - 3), text, font=font, fill='#dceaf5')
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format='WEBP', quality=84, method=3)
    return target.relative_to(ROOT).as_posix()


def _save_club_detail_legacy(game, saved_db, base_db, club_id):
    """Build the selected career club panel from the save and installed assets."""
    if not club_id or 'default_teamsheets' not in saved_db.tables or 'players' not in saved_db.tables:
        return None

    fields = ['teamid', 'teamname', 'domesticprestige', 'attackrating',
              'midfieldrating', 'defenserating', 'overallrating',
              'teamcolor1r', 'teamcolor1g', 'teamcolor1b']
    team = next((row for row in saved_db.rows('teams', fields)
                 if row['teamid'] == club_id), None)
    if not team:
        return None

    sheet_fields = ['teamid'] + [f'playerid{i}' for i in range(11)] + [f'position{i}' for i in range(11)]
    sheet = next((row for row in saved_db.rows('default_teamsheets', sheet_fields)
                  if row['teamid'] == club_id), None)
    if not sheet:
        return None

    player_ids = [sheet.get(f'playerid{i}') for i in range(11)]
    player_ids = [player_id for player_id in player_ids if player_id]
    if len(player_ids) != 11:
        return None
    player_fields = ['playerid', 'commonnameid', 'firstnameid', 'lastnameid',
                     'overallrating', 'preferredposition1']
    players = {row['playerid']: row for row in saved_db.rows('players', player_fields)
               if row['playerid'] in player_ids}

    names = {row['nameid']: row['name'] for row in base_db.rows('playernames', ['nameid', 'name'])}
    if 'dcplayernames' in saved_db.tables:
        names.update({row['nameid']: row['name'] for row in
                      saved_db.rows('dcplayernames', ['nameid', 'name']) if row['name']})
    edited_names = {}
    if 'editedplayernames' in saved_db.tables:
        edited_names = {row['playerid']: row for row in saved_db.rows(
            'editedplayernames', ['playerid', 'firstname', 'surname', 'commonname', 'playerjerseyname'])}

    position_labels = {
        0: 'GOL', 1: 'LD', 2: 'ZAG', 3: 'ZAG', 4: 'ZAG', 5: 'LE', 6: 'LE',
        7: 'VOL', 8: 'VOL', 9: 'MEI', 10: 'MEI', 11: 'MEI', 12: 'MEI',
        13: 'MEI', 14: 'MEI', 15: 'PE', 16: 'PE', 17: 'PE', 18: 'MEI',
        19: 'PD', 20: 'PD', 21: 'ATA', 22: 'ATA', 23: 'ATA', 24: 'ATA',
        25: 'ATA', 26: 'ATA', 27: 'ATA',
    }
    shape = [
        (0.50, 0.89), (0.37, 0.72), (0.63, 0.72), (0.14, 0.72), (0.86, 0.72),
        (0.38, 0.54), (0.62, 0.54), (0.15, 0.35), (0.50, 0.35), (0.85, 0.35),
        (0.50, 0.15),
    ]

    def image_asset(source, target, bounds, quality):
        if target.is_file():
            return target.relative_to(ROOT).as_posix()
        if not source.is_file():
            return ''
        try:
            with Image.open(source) as original:
                image = original.convert('RGBA')
                image.thumbnail(bounds, Image.Resampling.LANCZOS)
                target.parent.mkdir(parents=True, exist_ok=True)
                image.save(target, format='WEBP', quality=quality, method=4)
            return target.relative_to(ROOT).as_posix()
        except (OSError, ValueError):
            return ''

    game = Path(game)

    def display_name(player):
        custom = edited_names.get(player['playerid'], {})
        for field in ('playerjerseyname', 'commonname'):
            if custom.get(field):
                return custom[field]
        common = names.get(player.get('commonnameid')) if player.get('commonnameid') else ''
        if common:
            return common
        first = custom.get('firstname') or names.get(player.get('firstnameid'), '')
        last = custom.get('surname') or names.get(player.get('lastnameid'), '')
        return ' '.join(part for part in (first, last) if part) or f'Jogador {player["playerid"]}'

    starters = []
    for index, player_id in enumerate(player_ids):
        player = players.get(player_id)
        if not player:
            continue
        portrait = image_asset(
            game / 'data/ui/imgAssets/heads' / f'p{player_id}.dds',
            ROOT / 'assets/players' / f'{player_id}.webp', (160, 160), 82)
        starters.append({
            'id': player_id, 'name': display_name(player),
            'position': position_labels.get(sheet.get(f'position{index}'), 'JOG'),
            'overall': player.get('overallrating') or 0,
            'portrait': portrait, 'x': shape[index][0], 'y': shape[index][1],
        })
    if len(starters) != 11:
        return None

    roster_ids = {row['playerid'] for row in saved_db.rows(
        'teamplayerlinks', ['teamid', 'playerid']) if row['teamid'] == club_id}
    all_player_fields = ['playerid', 'commonnameid', 'firstnameid', 'lastnameid',
                         'overallrating', 'preferredposition1']
    # The compact save DB stores the roster and its ratings. Only five portraits
    # are included in the highlight strip; the 11 starters above remain the 3D scene.
    ratings = {row['playerid']: row for row in saved_db.rows('players', all_player_fields)
               if row['playerid'] in roster_ids}
    highlights = []
    for player in sorted(ratings.values(), key=lambda row: row['overallrating'] or 0, reverse=True)[:5]:
        portrait = image_asset(
            game / 'data/ui/imgAssets/heads' / f'p{player["playerid"]}.dds',
            ROOT / 'assets/players' / f'{player["playerid"]}.webp', (160, 160), 82)
        highlights.append({
            'id': player['playerid'], 'name': display_name(player),
            'position': position_labels.get(player.get('preferredposition1'), 'JOG'),
            'overall': player.get('overallrating') or 0, 'portrait': portrait,
        })

    stadium_id = next((row['stadiumid'] for row in base_db.rows(
        'teamstadiumlinks', ['teamid', 'stadiumid']) if row['teamid'] == club_id), None)
    stadium = None
    if stadium_id:
        stadium_row = next((row for row in base_db.rows(
            'stadiums', ['stadiumid', 'name', 'capacity']) if row['stadiumid'] == stadium_id), None)
        if stadium_row:
            stadium = {
                'id': stadium_id, 'name': stadium_row['name'],
                'capacity': stadium_row['capacity'],
                'image': image_asset(
                    ROOT.parent.parent / 'assets/ui/my_office/stadium_day_generic.png',
                    ROOT / 'assets/stadiums' / 'stadium_generic.webp', (720, 360), 78),
            }

    kit_rows = [row for row in base_db.rows(
        'teamkits', ['teamtechid', 'teamkitid', 'teamkittypetechid', 'year',
                     'teamcolorprimr', 'teamcolorprimg', 'teamcolorprimb',
                     'teamcolorsecr', 'teamcolorsecg', 'teamcolorsecb',
                     'teamcolortertr', 'teamcolortertg', 'teamcolortertb'])
        if row['teamtechid'] == club_id]
    kits = []
    for kind, label in ((2, 'Goleiro'), (0, 'Mandante'), (1, 'Visitante')):
        candidates = [row for row in kit_rows if row['teamkittypetechid'] == kind]
        if not candidates:
            continue
        kit = next((row for row in candidates if row['year'] == 0), candidates[0])
        kits.append({
            'id': kit['teamkitid'], 'name': label,
            'primary': [kit['teamcolorprimr'], kit['teamcolorprimg'], kit['teamcolorprimb']],
            'secondary': [kit['teamcolorsecr'], kit['teamcolorsecg'], kit['teamcolorsecb']],
            'tertiary': [kit['teamcolortertr'], kit['teamcolortertg'], kit['teamcolortertb']],
        })

    colors = [team.get('teamcolor1r'), team.get('teamcolor1g'), team.get('teamcolor1b')]
    return {
        'clubId': club_id, 'name': team['teamname'],
        'overall': team.get('overallrating') or 0,
        'reputation': team.get('domesticprestige') or 0,
        'attack': team.get('attackrating') or 0,
        'midfield': team.get('midfieldrating') or 0,
        'defense': team.get('defenserating') or 0,
        'primary': colors, 'starters': starters, 'highlights': highlights,
        'stadium': stadium, 'kits': kits,
    }


def save_club_detail(game, saved_db, base_db, club_id, saved_manager=None, history_records=None):
    return build_detail(ROOT, CAREER_NATIVE, Path(game), saved_db, base_db, club_id,
                        saved_manager=saved_manager, history_records=history_records,render_native=os.environ.get('FF_PREVIEW_SKIP_RENDER')!='1')


def load_sample_career(game, slot, installed_catalog):
    if not slot:
        return None
    user_root = Path(os.environ.get('USERPROFILE') or Path.home())
    save_path = user_root / 'Documents' / 'FIFA 16' / '0' / 'FIFA16' / slot / 'DATA'
    if not save_path.is_file():
        return None
    editor_dir = ROOT.parent / 'career_birthdate_2006'
    import sys
    sys.path.insert(0, str(editor_dir))
    try:
        import birthdate_editor
    except ImportError:
        return None
    try:
        data = save_path.read_bytes()
        outer_databases = birthdate_editor.find_databases(data)
        base_db = FifaDatabase(game, include_all_tables=True)
        manager_team_id = None
        saved_catalog = None
        detail = None
        saved_manager = None
        history_records = []
        manager_stats = {}
        for outer in outer_databases:
            manager_table = birthdate_editor.find_table(outer, b'biWl')
            if manager_table and manager_table.written:
                manager_field = birthdate_editor.find_field(manager_table, b'NTyS')
                if manager_field:
                    # NTyS is career_managerinfo.clubteamid. The FIFA metadata
                    # stores it with range-low -1, unlike the generic save parser.
                    manager_field = birthdate_editor.Field(
                        manager_field.short, manager_field.bit, manager_field.depth, -1)
                    offset = birthdate_editor.row_offset(outer, manager_table, 0)
                    manager_team_id = birthdate_editor.read_packed(data, offset, manager_field)

            raw_database = data[outer.start:outer.start + outer.declared_size]
            save_db = FifaDatabase(game, raw_database, include_all_tables=True)
            if 'career_managerinfo' in save_db.tables:
                for row in save_db.rows('career_managerinfo',['clubteamid','boardconfidence','managerreputation','wage']):
                    if row.get('clubteamid',-1)>0:manager_stats[row['clubteamid']]=row
            if 'career_managerhistory' in save_db.tables:
                history_fields = ['season', 'leagueid', 'teamid', 'games_played', 'wins',
                                  'draws', 'losses', 'goals_for', 'goals_against', 'points',
                                  'tableposition', 'leaguetrophies', 'domesticcuptrophies',
                                  'continentaltrophies']
                history_records.extend(save_db.rows('career_managerhistory', history_fields))
            if 'manager' in save_db.tables:
                for manager_row in save_db.rows('manager', ['firstname', 'surname', 'teamid']):
                    if manager_row.get('teamid') == manager_team_id:
                        saved_manager = manager_row
                        break
            if not {'teams', 'leagues', 'leagueteamlinks'} <= save_db.tables.keys():
                continue
            saved_teams = {team['teamid']: team for team in save_db.rows(
                'teams', ['teamid', 'teamname', 'latitude', 'longitude', 'domesticprestige',
                          'attackrating', 'midfieldrating', 'defenserating',
                          'overallrating', 'teamcolor1r', 'teamcolor1g', 'teamcolor1b'])}
            saved_leagues = save_db.rows('leagues', ['leagueid', 'countryid', 'level'])
            saved_links = save_db.rows(
                'leagueteamlinks', ['teamid', 'leagueid', 'secondarytable'])
            memberships = {}
            for link in saved_links:
                if not link['secondarytable']:
                    memberships.setdefault(link['teamid'], set()).add(link['leagueid'])

            installed_by_id = {league['leagueid']: league for league in installed_catalog}
            nations = {nation['nationid']: nation for nation in base_db.rows(
                'nations', ['nationid', 'nationname', 'isocountrycode'])}
            saved_catalog = []
            for league in saved_leagues:
                base = installed_by_id.get(league['leagueid'])
                if not base or league['leagueid'] == 78 or not 1 <= league['level'] <= 7:
                    continue
                clubs = [team for team in saved_teams.values()
                         if league['leagueid'] in memberships.get(team['teamid'], set())
                         and memberships[team['teamid']] == {league['leagueid']}]
                if not clubs:
                    continue
                country = nations.get(league['countryid'], base['country'])
                saved_catalog.append({
                    **base, 'countryid': league['countryid'], 'level': league['level'],
                    'country': country, 'clubs': sorted(clubs, key=lambda item: item['teamname'].casefold()),
                })
            break

        if not saved_catalog:
            return None
        valid_team_ids = {club['teamid'] for league in saved_catalog for club in league['clubs']}
        if manager_team_id not in valid_team_ids:
            manager_team_id = None
        if manager_team_id:
            for outer in outer_databases:
                raw_database = data[outer.start:outer.start + outer.declared_size]
                candidate = FifaDatabase(game, raw_database, include_all_tables=True)
                if {'teamplayerlinks', 'players', 'teams'} <= candidate.tables.keys():
                    if not saved_manager and 'manager' in candidate.tables:
                        saved_manager = next((row for row in candidate.rows(
                            'manager', ['firstname', 'surname', 'teamid'])
                            if row.get('teamid') == manager_team_id), None)
                    saved_manager={**(saved_manager or {}),**manager_stats.get(manager_team_id,{})}
                    detail = save_club_detail(game, candidate, base_db, manager_team_id,
                                              saved_manager, history_records)
                    if detail:
                        break
        return {'club_id': manager_team_id, 'leagues': saved_catalog,
                'slot': slot, 'detail': detail}
    except Exception:
        return None


def render_crest(game, team_id, inline=False):
    target = ROOT / 'crests' / f'{team_id}.webp'
    if target.is_file() and not inline:
        return 'crests/' + target.name, None
    source = next((game / f'data/ui/imgAssets/crest/{theme}/l{team_id}.dds'
                   for theme in ('light', 'dark')
                   if (game / f'data/ui/imgAssets/crest/{theme}/l{team_id}.dds').is_file()), None)
    if not source:
        return '', None
    with Image.open(source) as original:
        image = original.convert('RGBA')
        image.thumbnail((96, 96), Image.Resampling.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, format='WEBP', quality=76, method=2)
        embed = None
        if inline:
            out = io.BytesIO()
            image.save(out, format='WEBP', quality=48, method=0)
            embed = 'data:image/webp;base64,' + base64.b64encode(out.getvalue()).decode('ascii')
        return 'crests/' + target.name, embed


def position(section, fallback):
    lat = float(section.get('lat', fallback['lat']))
    lon = float(section.get('lon', fallback['lon']))
    zoom = float(section.get('zoom', fallback['zoom']))
    if not -90 <= lat <= 90 or not -180 <= lon <= 180 or not .75 <= zoom <= 10:
        raise ValueError('Coordenadas ou zoom fora do limite no INI')
    return lat, lon, zoom


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inline', type=Path, help='also write the conversation preview')
    args = parser.parse_args()
    config = configparser.ConfigParser(interpolation=None)
    config.read(ROOT / 'clubes.ini', encoding='utf-8-sig')
    game = Path(config['fifa']['game_path'])
    installed_catalog = catalog(game)
    sample_career = load_sample_career(
        game, config['fifa'].get('sample_save_slot', '').strip(), installed_catalog)
    fifa_leagues = sample_career['leagues'] if sample_career else installed_catalog
    game_text = load_game_localization(game)
    alpha3, all_cities, cities_by_country, cities_by_name, cities_by_state = load_geo_sources()
    capitals = {}
    for city in all_cities:
        if city['feature'] == 'PPLC' and city['iso2'] not in capitals:
            capitals[city['iso2']] = city
    for iso2, cities in cities_by_country.items():
        capitals.setdefault(iso2, cities[0])
    country_names = json.loads((ROOT / 'club_city_overrides.json').read_text(encoding='utf-8'))
    archive_index = big_asset_index(game)
    world = json.loads((ROOT / 'world.json').read_text(encoding='utf-8'))
    world_geometry = {feature['properties']['id']: feature['geometry']
                      for feature in world['features']}

    # Match the in-game selector: exclude national teams and invalid league levels.
    eligible = [l for l in fifa_leagues
                if l['leagueid'] != 78 and 1 <= l['level'] <= 7 and l['clubs']]
    memberships = {}
    for league in eligible:
        for club in league['clubs']:
            memberships.setdefault(club['teamid'], set()).add(league['leagueid'])
    eligible = [
        {**l, 'clubs': [t for t in l['clubs'] if memberships[t['teamid']] == {l['leagueid']}]}
        for l in eligible
    ]
    eligible = [l for l in eligible if l['clubs']]
    eligible.sort(key=lambda l: l['leagueid'])

    country_index, country_rows, league_rows = {}, [], []
    inline_ids = {int(s.split('.', 1)[1]) for s in config.sections()
                  if s.startswith('club.') and s.split('.', 1)[1].isdigit()}
    missing_flags, missing_league_icons = 0, 0
    for l in eligible:
        nation = l['country']
        iso2 = (nation.get('isocountrycode') or '').upper()
        original_name = nation.get('nationname') or 'País desconhecido'
        nation_id = int(nation.get('nationid') or l['countryid'])
        is_brazil_nation = iso2 == 'BR' or (
            iso2 == 'XX' and any(word in original_name.casefold() for word in ('brasil', 'brazil')))
        # FIFA separates the Brazilian state/federation pools into pseudo-
        # nations. Put all of them under the real Brazil row in the selector.
        if is_brazil_nation:
            nation_id = 54
        country_id = 'N' + str(nation_id)
        iso3 = 'BRA' if is_brazil_nation else (alpha3.get(iso2) or ISO3.get(iso2))
        location_iso2 = 'BR' if is_brazil_nation else iso2
        localized_country = game_text.get(f'NationName_{nation_id}')
        name = localized_country or {
            'england': 'Inglaterra', 'scotland': 'Escócia', 'wales': 'País de Gales',
            'northern ireland': 'Irlanda do Norte', 'free agents country': 'Agentes livres',
            'rest of world': 'Resto do mundo',
        }.get(original_name.casefold(), COUNTRY_NAME_PT.get(iso2, original_name))
        flag_path = f'data/ui/imgAssets/flags512x512/f_{nation_id}.dds'
        country_icon, inline_country_icon = render_game_icon(
            game, archive_index, flag_path, ROOT / 'icons' / 'countries' / f'{nation_id}.webp')
        if not country_icon:
            missing_flags += 1
            country_icon = render_placeholder_icon(
                ROOT / 'icons' / 'countries' / f'{nation_id}.webp', name)
        if country_id not in country_index:
            country_index[country_id] = len(country_rows)
            country_rows.append({
                'id': country_id, 'name': name, 'iso3': iso3,
                'nationId': nation_id, 'icon': country_icon, 'leagueIds': [],
            })
        elif country_id == 'BRA' and not country_rows[country_index[country_id]].get('icon'):
            country_rows[country_index[country_id]].update({'nationId': nation_id, 'icon': country_icon})

        league_key = 'league.' + str(l['leagueid'])
        league_setting = config[league_key] if league_key in config else {}
        league_default = {'lat': 0, 'lon': 0, 'zoom': 1.25}
        federation_state = BRAZIL_FEDERATION_STATES.get(l['leagueid']) if is_brazil_nation else None
        if federation_state:
            capital = city_by_label(BRAZIL_STATE_CAPITALS[federation_state], 'BR',
                                    cities_by_name, federation_state)
            if capital:
                league_default = {'lat': capital['lat'], 'lon': capital['lon'], 'zoom': 1.65}
        elif l['leagueid'] in (7, 350, 351, 352, 354, 355, 356):
            league_default = {'lat': -14.2, 'lon': -51.9, 'zoom': 1.35}
        elif iso3 == 'ESP':
            league_default = {'lat': 39.8, 'lon': -3.8, 'zoom': 1.65}
        try:
            center = dict(zip(('lat', 'lon', 'zoom'), position(league_setting, league_default)))
        except (TypeError, ValueError, KeyError):
            center = league_default.copy()

        clubs = []
        for t in sorted(l['clubs'], key=lambda item: (item['teamname'].casefold(), item['teamid'])):
            section_key = 'club.' + str(t['teamid'])
            club_setting = config[section_key] if section_key in config else {}
            location, lat, lon, zoom, precision = resolve_location(
                t, location_iso2, iso3, club_setting, country_names.get(str(t['teamid']), ''),
                cities_by_country.get(location_iso2, []), all_cities, cities_by_name,
                world_geometry, capitals,
                federation_state,
                cities_by_state)
            crest_path, inline_crest = render_crest(
                game, t['teamid'], bool(args.inline and t['teamid'] in inline_ids))
            clubs.append({
                'id': t['teamid'],
                'name': game_text.get(f"TeamName_{t['teamid']}", t['teamname']),
                'lat': lat, 'lon': lon, 'zoom': zoom,
                'located': True, 'crest': (inline_crest or crest_path),
                'city': location, 'precision': precision,
                'reputation': t.get('domesticprestige', 0),
                'overall': t.get('overallrating', 0),
                'attack': t.get('attackrating', 0),
                'midfield': t.get('midfieldrating', 0),
                'defense': t.get('defenserating', 0),
                'primary': [t.get('teamcolor1r', 0), t.get('teamcolor1g', 0), t.get('teamcolor1b', 0)],
            })
        if not any(key in league_setting for key in ('lat', 'lon', 'zoom')) \
                and not federation_state and l['leagueid'] not in (7, 350, 351, 352, 354, 355, 356) \
                and iso3 != 'ESP' and clubs:
            lat = sum(club['lat'] for club in clubs) / len(clubs)
            longitude_x = sum(math.cos(math.radians(club['lon'])) for club in clubs)
            longitude_y = sum(math.sin(math.radians(club['lon'])) for club in clubs)
            lon = math.degrees(math.atan2(longitude_y, longitude_x))
            center = {'lat': lat, 'lon': lon, 'zoom': 1.55}
        league_icon_path = f'data/ui/imgAssets/league/dark/l{l["leagueid"]}.dds'
        league_icon, inline_league_icon = render_game_icon(
            game, archive_index, league_icon_path,
            ROOT / 'icons' / 'leagues' / f'{l["leagueid"]}.webp')
        if not league_icon:
            missing_league_icons += 1
        entry = {
            'id': l['leagueid'], 'countryId': country_id,
            'label': game_text.get(f"LeagueName_{l['leagueid']}", l['leaguename']),
            'division': f"{l['level']}ª {game_text.get('division', 'Divisão').casefold()}",
            'name': game_text.get(f"LeagueName_{l['leagueid']}", l['leaguename']),
            'level': l['level'], 'icon': league_icon,
            'clubs': clubs, **center,
        }
        league_rows.append(entry)
        country_rows[country_index[country_id]]['leagueIds'].append(l['leagueid'])

    brazil = next((item for item in country_rows if item['nationId'] == 54), None)
    if brazil:
        league_priority = {league_id: index
                           for index, league_id in enumerate(BRAZIL_LEAGUE_ORDER)}
        # Keep the national pyramid together: Série A, B, C, the Série D tiers,
        # then the access division; state federations retain their catalog order.
        brazil['leagueIds'].sort(
            key=lambda league_id: (league_id not in league_priority,
                                   league_priority.get(league_id, 0)))

    league_index = {l['id']: l for l in league_rows}
    default_league_id = int(config['fifa'].get('default_league_id', '7'))
    if default_league_id not in league_index:
        default_league_id = league_rows[0]['id']
    valid_team_ids = {club['id'] for league_row in league_rows for club in league_row['clubs']}
    sample_slot = sample_career['slot'] if sample_career else ''
    sample_team_id = sample_career['club_id'] if sample_career else None
    if sample_team_id:
        sample_league = next((item for item in league_rows
                              if any(club['id'] == sample_team_id for club in item['clubs'])), None)
        if sample_league:
            default_league_id = sample_league['id']
    default_league = league_index[default_league_id]
    if not default_league['clubs']:
        raise ValueError(f"A liga selecionada [{default_league_id}] não tem clubes.")
    default_team = next((club for club in default_league['clubs'] if club['id'] == sample_team_id),
                        default_league['clubs'][0])
    default_country_id = default_league['countryId']
    default_view = {k: default_team[k] for k in ('lat', 'lon', 'zoom')}
    country_rows.sort(key=lambda item: (item['id'] != default_country_id, item['name'].casefold()))

    payload = {
        'countries': country_rows, 'leagues': league_rows, 'world': world,
        'defaultCountryId': default_country_id, 'defaultLeagueId': default_league_id,
        'defaultTeamId': default_team['id'], 'defaultView': default_view,
        'sampleSaveSlot': sample_slot or None,
        'sampleClubDetail': sample_career.get('detail') if sample_career else None,
    }
    template = (ROOT / 'template.html').read_text(encoding='utf-8')
    app_script = (ROOT / 'app.js').read_text(encoding='utf-8')
    controls_script = (ROOT / 'spatial_navigation.js').read_text(encoding='utf-8') + '\n' + (ROOT / 'club_data_client.js').read_text(encoding='utf-8') + '\n' + (ROOT / 'control_hints.js').read_text(encoding='utf-8') + '\n' + (ROOT / 'pointer_cursor.js').read_text(encoding='utf-8')
    inline_payload = json.loads(json.dumps(payload, ensure_ascii=False))
    fragment = template.replace(
        '__FF_DATA__',
        json.dumps(inline_payload, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    )
    fragment = fragment.replace('__FF_CONTROLS__', '<script>' + controls_script + '</script>')
    fragment = fragment.replace(
        '__FF_D3__', '<script>' + (ROOT / 'vendor/d3.min.js').read_text(encoding='utf-8') + '</script>'
    ).replace('__FF_APP__', app_script)
    fragment_size = len(fragment.encode('utf-8'))
    if args.inline and fragment_size > 1_000_000:
        raise ValueError(f'Prévia inline maior que 1 MB: {fragment_size} bytes')

    standalone_payload = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    standalone_fragment = template.replace('__FF_DATA__', standalone_payload)
    standalone_fragment = standalone_fragment.replace(
        '__FF_CONTROLS__', '<script>' + controls_script + '</script>')
    standalone_fragment = standalone_fragment.replace(
        '__FF_D3__', '<script>' + (ROOT / 'vendor/d3.min.js').read_text(encoding='utf-8') + '</script>'
    ).replace('__FF_APP__', app_script)
    standalone = (
        '<!doctype html>\n<html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>FIFA Friends · Outros clubes</title>'
        '<style>body{margin:0;background:#080e18}button{cursor:pointer}</style>'
        '</head><body>\n' + standalone_fragment + '\n</body></html>\n'
    )
    compact_leagues = [
        {**league_row, 'clubs': [
            {**club, 'crest': 'crests/' + str(club['id']) + '.webp'
             if club['crest'] and not str(club['crest']).startswith('crests/') else club['crest']}
            for club in league_row['clubs']
        ]}
        for league_row in league_rows
    ]
    compact_data = {
        'countries': country_rows, 'leagues': compact_leagues,
        'defaultCountryId': default_country_id, 'defaultLeagueId': default_league_id,
        'defaultTeamId': default_team['id'], 'sampleSaveSlot': sample_slot or None,
        'sampleClubDetail': sample_career.get('detail') if sample_career else None,
    }
    (ROOT / 'clubes.json').write_text(
        json.dumps(compact_data, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'index.html').write_text(standalone, encoding='utf-8')
    preview_context = {'clubId': sample_team_id or 0, 'clubName': default_team['name'] if sample_team_id else '', 'saveSlot': sample_slot, 'detail': sample_career.get('detail') if sample_career else {}}
    (ROOT / 'preview-data.js').write_text('window.FF_PREVIEW_CONTEXT=' + json.dumps(preview_context, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c') + ';\n', encoding='utf-8')
    if args.inline:
        args.inline.parent.mkdir(parents=True, exist_ok=True)
        args.inline.write_text(fragment, encoding='utf-8')

    club_count = sum(len(l['clubs']) for l in league_rows)
    missing = sum(not c['crest'] for l in league_rows for c in l['clubs'])
    unlocated = sum(not c['located'] for l in league_rows for c in l['clubs'])
    print(f'Prévia do banco FIFA: {club_count} clubes, {len(league_rows)} ligas, '
          f'{len(country_rows)} países/regiões; {missing} sem escudo, '
          f'{missing_flags} bandeiras e {missing_league_icons} emblemas de liga não encontrados.')
    if args.inline:
        print(f'Visualização: {fragment_size / 1_000_000:.2f} MB.')
    if sample_team_id:
        print(f'Save-base {sample_slot}: {default_team["name"]} · {default_team["city"]}.')
    else:
        print(f'Padrão: {default_league["label"]} · {default_team["name"]}.')


if __name__ == '__main__':
    main()
