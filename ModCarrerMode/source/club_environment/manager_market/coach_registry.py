"""Human-editable manager registry shared by the market and SLC resolver."""
from configparser import ConfigParser, Error as ConfigError
from datetime import date
from pathlib import Path
import re

COACH_ID = re.compile(r"COACH-[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
MAX_ID = 200000


def _integer(section, key, default=0, low=0, high=MAX_ID):
    raw = section.get(key, str(default)).strip()
    if not raw.isdecimal():
        raise ValueError(key)
    value = int(raw)
    if not low <= value <= high:
        raise ValueError(key)
    return value


def _boolean(section, key, default):
    try:
        return section.getboolean(key, fallback=default)
    except ValueError as exc:
        raise ValueError(key) from exc


def _text(section, key, default="", limit=120):
    value = section.get(key, fallback=default).strip()
    if len(value) > limit or any(c in value for c in "\r\n\t\x00"):
        raise ValueError(key)
    return value


def _image(value):
    value = value.replace("\\", "/").strip()
    if not value:
        return "minifaces/NOTFOUND_DEFAULT.png"
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.parts[0:1] != ("minifaces",):
        raise ValueError("image")
    if path.suffix.casefold() != ".png":
        raise ValueError("image")
    return path.as_posix()


def load(path):
    """Return validated registry entries. Bad sections are skipped safely."""
    parser = ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str.lower
    try:
        with Path(path).open("r", encoding="utf-8-sig") as source:
            parser.read_file(source)
    except (OSError, UnicodeError, ConfigError):
        return {}
    try:
        meta = parser["registry"]
        if _integer(meta, "schema", low=1, high=1) != 1 or not _boolean(meta, "enabled", True):
            return {}
    except (KeyError, ValueError):
        return {}

    result = {}
    for section_name in parser.sections():
        if not section_name.startswith("coach:"):
            continue
        coach_id = section_name[6:].strip()
        if not COACH_ID.fullmatch(coach_id) or coach_id in result:
            continue
        section = parser[section_name]
        try:
            name = _text(section, "name", limit=100)
            if not name:
                continue
            nationality = _text(section, "nationality", limit=64)
            birth_date = _text(section, "birth_date", limit=10)
            if birth_date:
                date.fromisoformat(birth_date)
                if len(birth_date) != 10:
                    continue
            reputation = float(section.get("reputation", "5"))
            if not 0 <= reputation <= 10:
                continue
            salary = _integer(section, "salary", 50000, 0, 2_000_000_000)
            style = _text(section, "style", "Equilibrado", 40) or "Equilibrado"
            image = _image(_text(section, "image", "minifaces/NOTFOUND_DEFAULT.png", 160))
            source_slc = _integer(section, "source_slc_club_id", 0)
            model_enabled = _boolean(section, "model_enabled", source_slc > 0)
            result[coach_id] = dict(
                coach_id=coach_id,
                name=name,
                nationality=nationality,
                birth_date=birth_date or None,
                birthplace=_text(section, "birthplace", limit=100),
                default_club_name=_text(section, "default_club_name", limit=100),
                source_slc_club_name=_text(section, "source_slc_club_name", limit=100),
                reputation=reputation,
                salary=salary,
                style=style,
                image=image,
                eligible=int(_boolean(section, "market_enabled", True)),
                fictional=int(_boolean(section, "fictional", False)),
                default_club_id=_integer(section, "default_club_id", 0),
                source_slc_club_id=source_slc,
                model_enabled=model_enabled and source_slc > 0,
                enabled=True,
            )
        except (ValueError, OverflowError):
            continue
    return result


def market_rows(path):
    """Coach columns that can be copied into a career market branch."""
    fields = ("coach_id", "name", "nationality", "birth_date", "birthplace", "reputation",
              "salary", "style", "image", "eligible", "fictional")
    return {key: {field: row[field] for field in fields} for key, row in load(path).items()}
