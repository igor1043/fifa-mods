"""Shared native-mod UI tokens. Original kits, pitches and status colors stay native."""
from pathlib import Path
import json
import os
import re

DEFAULTS = dict(accent='#B9A274', accent_text='#17242C', accent_ink='#76623D',
                accent_hover='#C8B58F', accent_soft='#EEE7DA', focus_outline='#E5D4B0',
                surface='#FFFFFF', paper='#F4F6F7')

def load(path=None):
    values = dict(DEFAULTS)
    if path is None:
        path = Path(os.environ.get('SERVER16_GAME_ROOT', Path(__file__).resolve().parents[3])) / 'ModCarrerMode/data/custom_ui_theme.json'
    try:
        raw = Path(path).read_text(encoding='utf-8-sig')
        if len(raw) > 8192:
            return values
        configured = json.loads(raw)
        if configured.get('version') != 1:
            return values
        for key in values:
            value = configured.get(key)
            if isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                values[key] = value.upper()
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return values

TOKENS = load()
ACCENT = TOKENS['accent']
ACCENT_TEXT = TOKENS['accent_text']
ACCENT_INK = TOKENS['accent_ink']
ACCENT_HOVER = TOKENS['accent_hover']
ACCENT_SOFT = TOKENS['accent_soft']
FOCUS_OUTLINE = TOKENS['focus_outline']

def rgb(value):
    return int(value.lstrip('#'), 16)

def argb(value, alpha=255):
    return (alpha << 24) | rgb(value)

def rgba(value, alpha=255):
    number = rgb(value)
    return ((number >> 16) & 255, (number >> 8) & 255, number & 255, alpha)
