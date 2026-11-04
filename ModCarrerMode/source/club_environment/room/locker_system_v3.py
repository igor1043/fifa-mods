"""Reusable, data-driven dressing-room cubicle system.

One cabinet module and one placement rule are shared by every club. A club
profile supplies only its palette, finish and optional fascia copy. This file
does not read or write career-save data.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


DEFAULT_LAYOUT = {
    "center": {
        "z": -592.0,
        "rows": [
            {"count": 6, "start_x": -630.0, "spacing": 90.0},
            {"count": 6, "start_x": 180.0, "spacing": 90.0},
        ],
    },
    "sides": {
        "left_x": -832.0,
        "right_x": 832.0,
        "start_z": -390.0,
        "spacing_z": 90.0,
        "odd_extra_side": "right",
    },
}

DEFAULT_MODULE = {
    "id": "locker_bay_v3",
    "width_cm": 90.0,
    "height_cm": 287.0,
    "depth_cm": 84.0,
    "parts": ["back_panel", "side_dividers", "hanger_rail", "shelf", "bench", "cushion"],
}


def read_config(path=None):
    """Load optional JSON data while keeping defaults safe for older installs."""
    if path is None or not Path(path).is_file():
        return {"layout": DEFAULT_LAYOUT, "module": DEFAULT_MODULE, "room_structure": {}, "visual": {}}
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        payload = {}
    return {
        "layout": payload.get("layout") or DEFAULT_LAYOUT,
        "module": payload.get("module") or DEFAULT_MODULE,
        "room_structure": payload.get("room_structure") or {},
        "visual": payload.get("visual") or {},
    }


def slot_frames(count, layout=None):
    """Calculate a frame per player from rows and side-wall spacing.

    The center rows fill first. Any remaining bays alternate along the side
    walls; for an odd remainder, the configured side receives the extra bay.
    The returned tuples can be reused by the hanging shirt, shoes and labels.
    """
    count = max(0, int(count))
    spec = layout or DEFAULT_LAYOUT
    center = spec.get("center", DEFAULT_LAYOUT["center"])
    sides = spec.get("sides", DEFAULT_LAYOUT["sides"])
    frames = []
    for row in center.get("rows", []):
        row_count = max(0, int(row.get("count", 0)))
        start_x = float(row.get("start_x", 0.0))
        spacing = float(row.get("spacing", 90.0))
        z = float(center.get("z", -592.0))
        for index in range(row_count):
            frames.append(((start_x + index * spacing, 0.0, z), 0.0))
    center_capacity = len(frames)
    frames = frames[:count]

    remaining = max(0, count - center_capacity)
    odd_side = sides.get("odd_extra_side", "right")
    first_side = odd_side if odd_side in ("left", "right") else "right"
    opposite = "left" if first_side == "right" else "right"
    for index in range(remaining):
        side = first_side if index % 2 == 0 else opposite
        row = index // 2
        x = float(sides.get(f"{side}_x", DEFAULT_LAYOUT["sides"][f"{side}_x"]))
        z = float(sides.get("start_z", -410.0)) + row * float(sides.get("spacing_z", 102.0))
        yaw = math.pi / 2 if side == "left" else -math.pi / 2
        frames.append(((x, 0.0, z), yaw))
    return frames


def _hex(value, default):
    if isinstance(value, str) and len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value.upper()
        except ValueError:
            pass
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        channels = [round(float(channel) * (255 if float(channel) <= 1 else 1)) for channel in value[:3]]
        return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, channel)) for channel in channels))
    return default


def visual_profile(club_id, club_name, primary, secondary, visual=None, finish=None):
    """Resolve custom club identity or derive a coherent generic fallback."""
    spec = visual or {}
    primary = _hex(primary, "#263E58")
    secondary = _hex(secondary, "#E1E4E8")
    fallback = dict(spec.get("fallback", {}))
    profile = {
        "club_id": int(club_id),
        "club_name": str(club_name or "Clube"),
        "preset": "generated",
        "primary": primary,
        "secondary": secondary,
        "finish": fallback.get("finish", "light"),
        "niche": fallback.get("niche", "#F3F4F2"),
        "cushion": fallback.get("cushion", secondary),
        "panel": fallback.get("panel", "#FFFFFF"),
        "banner": {
            "mode": "generated",
            "lines": [str(club_name or "Clube").upper()],
            "base": primary,
            "accent": secondary,
            "ink": "#FFFFFF",
        },
        "ceiling_crest": True,
        "floor": fallback.get("floor", "neutral_tile"),
    }
    profile.update(spec.get("clubs", {}).get(str(int(club_id)), {}))

    selected_finish = finish or profile.get("finish", "light")
    finish_data = spec.get("finishes", {}).get(selected_finish, {})
    if finish_data:
        profile.update(finish_data)
    profile["finish"] = selected_finish
    profile["primary"] = _hex(profile.get("primary"), primary)
    profile["secondary"] = _hex(profile.get("secondary"), secondary)
    profile["niche"] = _hex(profile.get("niche"), "#F3F4F2")
    profile["cushion"] = _hex(profile.get("cushion"), profile["secondary"])
    profile["panel"] = _hex(profile.get("panel"), "#FFFFFF")
    profile.setdefault("banner", {})
    profile["banner"].setdefault("mode", "generated")
    profile["banner"].setdefault("lines", [str(club_name or "Clube").upper()])
    profile["banner"]["base"] = _hex(profile["banner"].get("base"), profile["primary"])
    profile["banner"]["accent"] = _hex(profile["banner"].get("accent"), profile["secondary"])
    return profile


def system_manifest(count, context, config):
    """Small serializable manifest for the native-room component builder."""
    layout = config.get("layout", DEFAULT_LAYOUT)
    center_capacity = sum(max(0, int(row.get("count", 0))) for row in layout.get("center", {}).get("rows", []))
    roster_count = max(0, int(count))
    side_count = max(0, roster_count - center_capacity)
    colors = context.get("colors", [[0.15, 0.24, 0.34], [0.88, 0.90, 0.92]])
    primary = colors[0] if len(colors) > 0 else "#263E58"
    secondary = colors[1] if len(colors) > 1 else "#E1E4E8"
    club = int(context.get("club", 0))
    style = visual_profile(club, context.get("club_name", "Clube"), primary, secondary, config.get("visual"))
    return {
        "schema": 3,
        "module": config.get("module", DEFAULT_MODULE),
        "room_structure": config.get("room_structure", {}),
        "club_style": style,
        "slot_count": roster_count,
        "distribution": {
            "center": min(roster_count, center_capacity),
            "sides": side_count,
            "odd_side": layout.get("sides", {}).get("odd_extra_side", "right"),
        },
        "finish_options": sorted(config.get("visual", {}).get("finishes", {"light": {}, "dark": {}}).keys()),
    }
