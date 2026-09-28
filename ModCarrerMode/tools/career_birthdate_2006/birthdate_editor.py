#!/usr/bin/env python3
"""Safe FIFA 16 Player Career birthdate editor.

The default operation is a read-only dry run.  A file is replaced only when
``--apply`` is explicitly supplied.  The editor works on a copy in memory,
validates the embedded T3DB databases and container CRC, creates a sibling
backup, then uses an atomic replace.

This is an offline save editor.  It is independent from the in-game memory
plugin and does not use Cheat Engine or attach to FIFA.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import zlib
from dataclasses import dataclass


SIGNATURE = b"DB\x00\x08\x00\x00\x00\x00"
CONTAINER_CRC_OFFSET = 132
CONTAINER_DATA_START = 160
CDCD = 0xCDCDCDCD
FIFA_EPOCH = dt.date(1582, 10, 14)
DEFAULT_DATE = dt.date(2007, 1, 1)

TABLE_PLAYERS = b"CZUM"
TABLE_PLAYAS_PLAYER = b"bxis"
TABLE_GROWTH = b"tRqR"
TABLE_CALENDAR = b"GJUr"

FIELD_PLAYER_ID = b"ykFq"
FIELD_BIRTHDATE = b"WVIU"
FIELD_IS_RETIRING = b"kvuF"
FIELD_STARTING_AGE = b"LEvg"
FIELD_CURRENT_DATE = b"aLZZ"


class EditorError(RuntimeError):
    pass


@dataclass(frozen=True)
class Field:
    short: bytes
    bit: int
    depth: int
    low: int


@dataclass(frozen=True)
class Table:
    name: bytes
    offset: int
    record_size: int
    field_count: int
    written: int
    compressed_length: int
    fields: tuple[Field, ...]
    records_offset: int
    crc_offset: int


@dataclass(frozen=True)
class Database:
    start: int
    end: int
    declared_size: int
    tables: tuple[Table, ...]


def u16(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def put_u32(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", data, offset, value & 0xFFFFFFFF)


def field_low(table_name: bytes, field_short: bytes) -> int:
    if table_name == TABLE_PLAYAS_PLAYER and field_short == FIELD_PLAYER_ID:
        return -1
    if field_short == FIELD_STARTING_AGE:
        return 12
    if field_short == FIELD_CURRENT_DATE:
        return 20_080_101
    return 0


def parse_database(data: bytes | bytearray, start: int, end: int) -> Database:
    if end - start < 40 or bytes(data[start:start + 8]) != SIGNATURE:
        raise EditorError(f"Invalid T3DB signature at 0x{start:X}.")
    declared = u32(data, start + 8)
    if declared < 40 or declared > end - start:
        raise EditorError(f"Invalid T3DB size at 0x{start:X}: {declared}.")
    count = u32(data, start + 16)
    if count == 0 or count > 200 or 24 + count * 8 >= declared:
        raise EditorError(f"Invalid T3DB table directory at 0x{start:X}.")

    tables: list[Table] = []
    directory = start + 24
    for index in range(count):
        name = bytes(data[directory + index * 8:directory + index * 8 + 4])
        relative = u32(data, directory + index * 8 + 4)
        table_offset = 28 + count * 8 + relative
        if table_offset < 0 or table_offset + 36 > declared:
            raise EditorError(f"Table {name!r} has an invalid offset.")
        table = start + table_offset
        record_size = u32(data, table + 4)
        compressed_length = u32(data, table + 12)
        written = u16(data, table + 18)
        field_count = data[table + 24]
        if not 1 <= record_size <= declared or not 1 <= field_count <= 250:
            raise EditorError(f"Table {name!r} has invalid dimensions.")
        descriptors_end = table_offset + 36 + field_count * 16
        records_offset = descriptors_end
        records_end = records_offset + written * record_size
        crc_offset = records_end + ((compressed_length + 7) & ~7 if compressed_length else 0)
        if crc_offset + 4 > declared:
            raise EditorError(f"Table {name!r} exceeds its T3DB container.")

        fields: list[Field] = []
        for field_index in range(field_count):
            descriptor = table + 36 + field_index * 16
            storage_type = u32(data, descriptor)
            short = bytes(data[descriptor + 8:descriptor + 12])
            bit = u32(data, descriptor + 4)
            depth = u32(data, descriptor + 12)
            if storage_type == 3:
                if depth == 0 or depth > 32 or bit + depth > record_size * 8:
                    raise EditorError(f"Field {short!r} in {name!r} is invalid.")
                fields.append(Field(short, bit, depth, field_low(name, short)))
        tables.append(Table(name, table_offset, record_size, field_count,
                            written, compressed_length, tuple(fields),
                            records_offset, crc_offset))
    return Database(start, min(end, start + declared), declared, tuple(tables))


def find_databases(data: bytes | bytearray) -> list[Database]:
    offsets: list[int] = []
    cursor = 0
    while True:
        cursor = data.find(SIGNATURE, cursor)
        if cursor < 0:
            break
        offsets.append(cursor)
        cursor += 1
    if len(offsets) < 2:
        raise EditorError("The DATA file has fewer than two embedded T3DB databases.")
    result: list[Database] = []
    for index, start in enumerate(offsets):
        end = offsets[index + 1] if index + 1 < len(offsets) else len(data)
        result.append(parse_database(data, start, end))
    return result


def find_table(database: Database, name: bytes) -> Table | None:
    return next((table for table in database.tables if table.name == name), None)


def find_field(table: Table, short: bytes) -> Field | None:
    return next((field for field in table.fields if field.short == short), None)


def row_offset(database: Database, table: Table, index: int) -> int:
    return database.start + table.records_offset + index * table.record_size


def active_row(data: bytes | bytearray, offset: int, table: Table) -> bool:
    return (data[offset + table.record_size - 1] & 0x80) == 0


def read_packed(data: bytes | bytearray, offset: int, field: Field) -> int:
    byte_count = (field.bit % 8 + field.depth + 7) // 8
    raw = int.from_bytes(data[offset + field.bit // 8:offset + field.bit // 8 + byte_count], "little")
    encoded = (raw >> (field.bit % 8)) & ((1 << field.depth) - 1)
    return encoded + field.low


def write_packed(data: bytearray, offset: int, field: Field, value: int) -> None:
    encoded = value - field.low
    if encoded < 0 or (field.depth < 32 and encoded >= (1 << field.depth)):
        raise EditorError(f"Value {value} is outside field {field.short!r} capacity.")
    for bit in range(field.depth):
        absolute = field.bit + bit
        byte_offset = offset + absolute // 8
        mask = 1 << (absolute % 8)
        if encoded & (1 << bit):
            data[byte_offset] |= mask
        else:
            data[byte_offset] &= ~mask
    if read_packed(data, offset, field) != value:
        raise EditorError(f"Packed write verification failed for {field.short!r}.")


def rows_with_field(data: bytes | bytearray, database: Database, table: Table,
                    key: Field | None = None, value: int | None = None):
    for index in range(table.written):
        offset = row_offset(database, table, index)
        if not active_row(data, offset, table):
            continue
        if key is not None and read_packed(data, offset, key) != value:
            continue
        yield index, offset


def one_player_id(data: bytes | bytearray, database: Database) -> int | None:
    table = find_table(database, TABLE_PLAYAS_PLAYER)
    if table is None:
        return None
    field = find_field(table, FIELD_PLAYER_ID)
    if field is None:
        raise EditorError("career_playasplayer has no playerid field.")
    values = [read_packed(data, offset, field)
              for _, offset in rows_with_field(data, database, table)]
    values = [value for value in values if value >= 0]
    if not values:
        return None
    unique = sorted(set(values))
    if len(unique) != 1:
        raise EditorError(f"career_playasplayer contains multiple player IDs: {unique}.")
    return unique[0]


def current_date_value(data: bytes | bytearray, database: Database) -> int | None:
    table = find_table(database, TABLE_CALENDAR)
    if table is None:
        return None
    field = find_field(table, FIELD_CURRENT_DATE)
    if field is None:
        raise EditorError("career_calendar has no currdate field.")
    values = [read_packed(data, offset, field)
              for _, offset in rows_with_field(data, database, table)]
    return next((value for value in values if 19_000_101 <= value <= 29_991_231), None)


def age_at(date_value: dt.date, game_date: int) -> int:
    current = dt.date(game_date // 10000, (game_date // 100) % 100, game_date % 100)
    age = current.year - date_value.year
    if (current.month, current.day) < (date_value.month, date_value.day):
        age -= 1
    return age


def fifa_crc(data: bytes | bytearray) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if crc & 0x80000000 else (crc << 1) & 0xFFFFFFFF
    return crc


def update_table_crc(data: bytearray, database: Database, table: Table,
                     changed: bool) -> str:
    if not changed:
        return "unchanged"
    offset = database.start + table.crc_offset
    stored = u32(data, offset)
    if stored == CDCD:
        return "preserved-CDCD"
    start = database.start + table.offset + 36
    end = database.start + table.crc_offset
    put_u32(data, offset, fifa_crc(data[start:end]))
    return "rehashed"


def patch_table_field(data: bytearray, database: Database, table_name: bytes,
                      key_short: bytes, key_value: int, target_short: bytes,
                      target_value: int) -> dict:
    table = find_table(database, table_name)
    if table is None:
        return {"found": False, "changed": False, "matched": 0}
    key = find_field(table, key_short)
    target = find_field(table, target_short)
    if key is None or target is None:
        raise EditorError(f"{table_name!r} lacks {key_short!r} or {target_short!r}.")
    matched = 0
    changed = 0
    previous: int | None = None
    for _, offset in rows_with_field(data, database, table, key, key_value):
        matched += 1
        current = read_packed(data, offset, target)
        previous = current
        if current != target_value:
            write_packed(data, offset, target, target_value)
            changed += 1
    if matched == 0:
        raise EditorError(f"Player {key_value} was not found in {table_name!r}.")
    return {
        "found": True,
        "matched": matched,
        "changed": changed,
        "previous": previous,
        "target": target_value,
        "crc": update_table_crc(data, database, table, changed > 0),
    }


def locate_player(data: bytes | bytearray, databases: list[Database]) -> tuple[int, int]:
    player_id: int | None = None
    game_date = 20260101
    for database in databases:
        candidate = one_player_id(data, database)
        if candidate is not None:
            if player_id is not None and candidate != player_id:
                raise EditorError(f"Conflicting Player Career IDs: {player_id} and {candidate}.")
            player_id = candidate
        candidate_date = current_date_value(data, database)
        if candidate_date is not None:
            game_date = candidate_date
    if player_id is None:
        raise EditorError("This DATA does not contain career_playasplayer; it is not a Player Career save.")
    return player_id, game_date


def read_targets(data: bytes | bytearray, databases: list[Database], player_id: int) -> dict:
    result: dict = {}
    for database in databases:
        players = find_table(database, TABLE_PLAYERS)
        if players is not None:
            key = find_field(players, FIELD_PLAYER_ID)
            birth = find_field(players, FIELD_BIRTHDATE)
            retiring = find_field(players, FIELD_IS_RETIRING)
            if key is None or birth is None or retiring is None:
                raise EditorError("players is missing one of playerid/birthdate/isretiring.")
            matches = list(rows_with_field(data, database, players, key, player_id))
            if len(matches) != 1:
                raise EditorError(f"Expected one players row for {player_id}, found {len(matches)}.")
            _, offset = matches[0]
            result["players"] = {
                "database": databases.index(database),
                "birthdate": read_packed(data, offset, birth),
                "isretiring": read_packed(data, offset, retiring),
            }
        growth = find_table(database, TABLE_GROWTH)
        if growth is not None:
            key = find_field(growth, FIELD_PLAYER_ID)
            age = find_field(growth, FIELD_STARTING_AGE)
            if key is None or age is None:
                raise EditorError("career_playergrowthhistory is missing playerid/startingage.")
            matches = list(rows_with_field(data, database, growth, key, player_id))
            if len(matches) > 1:
                raise EditorError(f"Expected at most one growth row for {player_id}, found {len(matches)}.")
            if matches:
                _, offset = matches[0]
                result["growth"] = {
                    "database": databases.index(database),
                    "startingage": read_packed(data, offset, age),
                }
    if "players" not in result:
        raise EditorError(f"Player {player_id} is missing from players.")
    return result


def validate_output(data: bytes, requested_date: dt.date, requested_age: int,
                    player_id: int, game_date: int) -> dict:
    databases = find_databases(data)
    targets = read_targets(data, databases, player_id)
    expected_birthdate = (requested_date - FIFA_EPOCH).days
    if targets["players"]["birthdate"] != expected_birthdate:
        raise EditorError("Post-write birthdate verification failed.")
    if targets["players"]["isretiring"] != 0:
        raise EditorError("Post-write isretiring verification failed.")
    if "growth" in targets and targets["growth"]["startingage"] != requested_age:
        raise EditorError("Post-write startingage verification failed.")
    if len(data) < CONTAINER_DATA_START or u32(data, CONTAINER_CRC_OFFSET) != (zlib.crc32(data[CONTAINER_DATA_START:]) & 0xFFFFFFFF):
        raise EditorError("Post-write DATA container CRC verification failed.")
    return targets


def apply_patch(data: bytes, requested_date: dt.date) -> tuple[bytes, dict]:
    databases = find_databases(data)
    player_id, game_date = locate_player(data, databases)
    requested_age = age_at(requested_date, game_date)
    if not 12 <= requested_age <= 50:
        raise EditorError(f"Requested date produces startingage={requested_age}; FIFA allows 12..50.")
    before = read_targets(data, databases, player_id)
    output = bytearray(data)
    output_databases = find_databases(output)
    patches: dict[str, dict] = {}
    for database in output_databases:
        if find_table(database, TABLE_PLAYERS) is not None:
            patches["birthdate"] = patch_table_field(
                output, database, TABLE_PLAYERS, FIELD_PLAYER_ID, player_id,
                FIELD_BIRTHDATE, (requested_date - FIFA_EPOCH).days)
            patches["isretiring"] = patch_table_field(
                output, database, TABLE_PLAYERS, FIELD_PLAYER_ID, player_id,
                FIELD_IS_RETIRING, 0)
        if find_table(database, TABLE_GROWTH) is not None:
            patches["startingage"] = patch_table_field(
                output, database, TABLE_GROWTH, FIELD_PLAYER_ID, player_id,
                FIELD_STARTING_AGE, requested_age)
    changed = any(item.get("changed", 0) for item in patches.values())
    outer_before = u32(output, CONTAINER_CRC_OFFSET)
    outer_after = zlib.crc32(output[CONTAINER_DATA_START:]) & 0xFFFFFFFF
    put_u32(output, CONTAINER_CRC_OFFSET, outer_after)
    after = validate_output(bytes(output), requested_date, requested_age, player_id, game_date)
    report = {
        "status": "changed" if changed else "already-correct",
        "playerId": player_id,
        "requestedDate": requested_date.isoformat(),
        "currentGameDate": game_date,
        "targetStartingAge": requested_age,
        "before": before,
        "after": after,
        "patches": patches,
        "outerCrcBefore": f"0x{outer_before:08x}",
        "outerCrcAfter": f"0x{outer_after:08x}",
        "inputSha256": hashlib.sha256(data).hexdigest(),
        "outputSha256": hashlib.sha256(output).hexdigest(),
        "integrity": "validated-t3db-fields-and-container-crc",
    }
    return bytes(output), report


def inspect_player_career_file(path: Path) -> dict:
    """Read one Player Career DATA file without changing it.

    The result deliberately identifies the player by the save directory and
    numeric Player Career id rather than guessing from every generic career
    DATA file.  Callers can therefore present an exact target before enabling
    a write action.
    """
    path = path.resolve()
    if not path.is_file():
        raise EditorError(f"DATA file not found: {path}")
    data = path.read_bytes()
    databases = find_databases(data)
    player_id, game_date = locate_player(data, databases)
    targets = read_targets(data, databases, player_id)
    birthdate = targets["players"]["birthdate"]
    try:
        birth_date = FIFA_EPOCH + dt.timedelta(days=birthdate)
    except OverflowError as exc:
        raise EditorError(f"Player {player_id} has an invalid birthdate value: {birthdate}.") from exc
    stat = path.stat()
    return {
        "path": str(path),
        "saveDirectory": path.parent.name,
        "size": stat.st_size,
        "modifiedNs": stat.st_mtime_ns,
        "playerId": player_id,
        "currentGameDate": game_date,
        "birthdateSerial": birthdate,
        "birthdate": birth_date.isoformat(),
        "isretiring": targets["players"]["isretiring"],
        "startingage": targets.get("growth", {}).get("startingage"),
    }


def commit_player_career_file(path: Path, requested_date: dt.date,
                              backup_dir: Path | None = None) -> dict:
    """Patch one verified Player Career DATA atomically and verify it again."""
    path = path.resolve()
    if not path.is_file():
        raise EditorError(f"DATA file not found: {path}")
    initial_stat = path.stat()
    original = path.read_bytes()
    original_hash = hashlib.sha256(original).hexdigest()
    output, report = apply_patch(original, requested_date)
    report["mode"] = "apply"
    report["inputPath"] = str(path)

    if output == original:
        report["writtenPath"] = None
        report["reason"] = "already-correct; no replacement needed"
        return report

    # Refuse a stale write: FIFA may have saved this exact DATA between our
    # analysis and the user pressing the apply button.
    current_bytes = path.read_bytes()
    current_stat = path.stat()
    if (current_stat.st_size != initial_stat.st_size or
            current_stat.st_mtime_ns != initial_stat.st_mtime_ns or
            hashlib.sha256(current_bytes).hexdigest() != original_hash):
        raise EditorError("DATA changed during analysis; refusing to overwrite it. Refresh and try again.")

    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S%f")
    resolved_backup_dir = backup_dir.resolve() if backup_dir else path.parent
    resolved_backup_dir.mkdir(parents=True, exist_ok=True)
    backup = resolved_backup_dir / f"{path.name}.birthdate-backup-{timestamp}"
    temporary = path.parent / f".{path.name}.birthdate-editor-{os.getpid()}.tmp"
    try:
        shutil.copy2(path, backup)
        if hashlib.sha256(backup.read_bytes()).hexdigest() != original_hash:
            raise EditorError("Backup verification failed; refusing to replace DATA.")
        with temporary.open("xb") as handle:
            handle.write(output)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != report["outputSha256"]:
            raise EditorError("Post-replace hash verification failed.")
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    report["backupPath"] = str(backup)
    report["writtenPath"] = str(path)
    return report


def parse_date(value: str) -> dt.date:
    try:
        result = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc
    if result < dt.date(1583, 1, 1) or result > dt.date(4000, 12, 31):
        raise argparse.ArgumentTypeError("date is outside the supported FIFA range")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path, help="path to a FIFA 16 career DATA file")
    parser.add_argument("--date", type=parse_date, default=DEFAULT_DATE,
                        help="birthdate in YYYY-MM-DD format (default: 2007-01-01)")
    parser.add_argument("--apply", action="store_true",
                        help="create a backup and atomically replace DATA; omitted means dry-run")
    parser.add_argument("--backup-dir", type=Path,
                        help="optional directory for the backup; default is next to DATA")
    args = parser.parse_args()

    path = args.data.resolve()
    if not path.is_file():
        parser.error(f"DATA file not found: {path}")
    if args.apply:
        report = commit_player_career_file(path, args.date, args.backup_dir)
    else:
        original = path.read_bytes()
        _output, report = apply_patch(original, args.date)
        report["mode"] = "dry-run"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EditorError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
