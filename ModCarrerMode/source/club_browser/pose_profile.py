"""Content identity of the authored pose, independent from saves and SQL."""
from pathlib import Path
import hashlib,json
def signature(game):
    path=Path(game)/'ModCarrerMode/data/club_browser/poses/starting_eleven.pose'
    if not path.is_file():
        if path.with_suffix('.json').is_file() or path.with_suffix('.scene.json').is_file():
            raise ValueError('Falta a pose dos titulares. Extraia o complemento de assets de 26/10/2026 ou mais recente na raiz do FIFA.')
        return b'legacy-pose'
    if not 16<=path.stat().st_size<=4*1024*1024:raise ValueError('Arquivo da pose dos titulares inválido.')
    data=path.read_bytes()
    if data[:8]!=b'FFPOSE02':raise ValueError('Versão da pose dos titulares inválida.')
    digest=hashlib.sha256(data).digest()
    manifest=path.with_suffix('.json')
    if manifest.is_file():
        expected=json.loads(manifest.read_text(encoding='utf-8-sig'))['recipe_sha256']
        if digest.hex()!=expected:
            raise ValueError('A pose dos titulares está desatualizada. Extraia o complemento de assets correspondente à versão instalada.')
    return digest
