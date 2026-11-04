"""One club catalog for wall art and room signs, with legacy install support."""
from pathlib import Path
import room_appearance as appearance

LEGACY='ModCarrerMode/data/club_environment/room/clubs'
AREAS={'wall_mural':'mural.png','hydration_wall':'hydration.png',
       'sign_medical':'sign_medical.png','sign_coach':'sign_coach.png',
       'sign_water':'sign_water.png','sign_exit':'sign_exit.png'}


def source(game,club,key,*,respect_style=True):
    game=Path(game)
    if respect_style:
        try:v3=(game/'ModCarrerMode/data/club_environment/room/active-version.txt').read_text().strip()=='3'
        except OSError:v3=False
        if v3 and appearance.preferences(game,club)['style']=='default':return None
    path=appearance.asset(game,club,key)
    if path is not None:return path
    legacy=game/LEGACY/str(int(club))/AREAS[key]
    return legacy if legacy.is_file() else None


def paths(game,club):
    return [(key,path) for key in AREAS if (path:=source(game,club,key,respect_style=False)) is not None]
