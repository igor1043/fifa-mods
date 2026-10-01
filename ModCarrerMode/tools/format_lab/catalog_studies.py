"""Read the full textual study corpus, deduplicate and generate topical navigation.

Classification is heuristic navigation, never an assertion that an old claim was
validated. Originals are not moved, rewritten or deleted. Generated files are new.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import unquote

AREAS = {
    '01_arquitetura_e_runtime': ('Arquitetura, DLLs, providers e integração', r'nativ|runtime|provider|bridge|host|dinput|injec|recuperacao.fonte|contratos|server16'),
    '02_telas_e_navegacao': ('Telas, APT, AVM1, NAV e layouts', r'apt|tela|screen|widget|nav|cards?|toggle|interface|menu|layout'),
    '03_save_e_bancos': ('Save, T3DB, jogador criado e persistência', r'save|t3db|nasciment|birth|retirement|aposent|idade|salvamento|data.index|huffman|playercareer'),
    '04_competicoes_e_ranking': ('Competições, calendário, pré-temporada e ranking', r'compdata|compet|fixture|calend|torneio|pre.temporada|ranking|classific|artilheir|assistencia'),
    '05_banco_e_partida': ('Banco, substituições, regras e partida', r'banco|bench|substitu|subs.length|squadtab|partida|gameplay'),
    '06_estadios_e_torcida': ('Estádios, torcida, câmeras e thumbnails', r'estadio|stadium|crowd|crwd|torcida|camera|panoram|thumbnail|dds'),
    '07_animacao_modelos_apresentacao': ('Animações, modelos, kits e apresentação', r'animac|modelos|3d|muse|seq|esia|skillmove|apresentac|kits|faces|retratos'),
    '08_localizacao_e_textos': ('Localização, textos e integridade', r'localiz|locales|traduc|loc.integrity|language|string|huffman'),
    '09_codecs_e_empacotamento': ('Codecs, bytecode, contêineres e empacotamento', r'decod|decript|descript|codific|compact|empacot|rebuild|round.trip|refpack|10fb|container|format|big.bh|lua'),
    '10_guias_e_historico': ('Guias, histórico e evidências auxiliares', r'indice|guia|readme|mapa|instala|atualiz|log|diagnostico|revisao|correcao'),
}
STAGES = {
    'decriptacao': r'decript|descript|criptograf|denuvo|encrypt',
    'decodificacao': r'decod|descompress|parser|refpack|huffman|cabecalho|formato',
    'codigo_e_decompilacao': r'decompil|disassembl|desmont|bytecode|avm1|luasm|ghidra|capstone',
    'codificacao_e_reconstrucao': r'encoder|writer|codificador|recompil|remont|reconstr|round.trip|serializ',
    'empacotamento': r'empacot|packager?|big4|bigf|\.bh|arquivo.big|trailer|alinhamento',
    'validacao': r'validac|validar|teste|sha.256|checksum|crc|prova|corrup',
}


def norm(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


def read_text(data):
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16'), 'utf-16'
    try:
        return data.decode('utf-8-sig'), 'utf-8'
    except UnicodeDecodeError:
        # A reversible byte mapping records unrecognised encodings without data loss.
        try:
            return data.decode('cp1252'), 'cp1252-candidate'
        except UnicodeDecodeError:
            return data.decode('latin1'), 'latin1-byte-mapping'


def link(path, page):
    relative = os.path.relpath(path, page.parent).replace('\\', '/')
    return '<' + relative.replace('>', '%3E').replace('<', '%3C') + '>'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('studies', type=Path)
    p.add_argument('catalog', type=Path)
    p.add_argument('data_output', type=Path)
    p.add_argument('--refresh-generated', action='store_true', help='refresh only generated indexes; preserve curated pages and original studies')
    a = p.parse_args()
    root = a.studies.resolve()
    if a.data_output.exists():
        raise ValueError('select a new data-output directory to preserve audit snapshots')
    if a.catalog.exists():
        marker=a.catalog/'README.md'
        if not a.refresh_generated or not marker.is_file() or not marker.read_text(encoding='utf-8').startswith('# Catálogo temático dos estudos'):
            raise ValueError('existing catalog requires --refresh-generated and known generated marker')
    documents, failures, hash_groups = [], [], defaultdict(list)
    # Existing curated corpus only; generated catalogs do not feed themselves.
    paths = sorted(p for section in ('00_GUIA', '01_MOD_CARREIRA_ATUAL', '02_ENGENHARIA_REVERSA')
                   for p in (root / section).rglob('*') if p.is_file() and p.suffix.lower() in ('.md', '.txt'))
    for path in paths:
        try:
            raw = path.read_bytes()
            text, encoding = read_text(raw)
            lines = text.splitlines()
            headings = [x.lstrip('#').strip() for x in lines if x.startswith('#')]
            title = headings[0] if headings else path.stem
            subject = norm(str(path.relative_to(root)) + ' ' + ' '.join(headings))
            areas = [key for key, (_, pattern) in AREAS.items() if re.search(pattern, subject)]
            if not areas:
                areas = ['10_guias_e_historico']
            content = norm(text)
            stages = [key for key, pattern in STAGES.items() if re.search(pattern, content)]
            record = {'path': str(path.relative_to(root)), 'title': title, 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest(), 'encoding': encoding,
                      'lines': len(lines), 'headings': headings, 'areas': areas, 'stages': stages,
                      'kind': 'documentacao' if path.suffix.lower() == '.md' else 'evidencia_textual',
                      'dates_in_name': re.findall(r'20\d{6}', path.name),
                      'historical_excerpts': [f'L{i+1}: {line.strip()}' for i, line in enumerate(lines)
                                             if re.search(r'nao.*(prov|confirm|decod)|pendente|round.trip|corrig|retifica|comprov', norm(line))][:12]}
            documents.append(record)
            hash_groups[record['sha256']].append(record)
        except (OSError, UnicodeError) as e:
            failures.append({'path': str(path), 'error': str(e)})
    canonical = []
    for group in hash_groups.values():
        group.sort(key=lambda d: ('reports' not in d['path'].split(os.sep), len(d['path']), d['path']))
        first = group[0]
        first['duplicates'] = [d['path'] for d in group[1:]]
        canonical.append(first)
        for d in group:
            d['canonical'] = first['path']
    a.catalog.mkdir(parents=True,exist_ok=a.refresh_generated)
    a.data_output.mkdir(parents=True)
    with (a.data_output / 'documents.jsonl').open('w', encoding='utf-8') as output:
        for record in documents:
            output.write(json.dumps(record, ensure_ascii=False) + '\n')
    summary = {'time_utc': datetime.now(timezone.utc).isoformat(), 'files_read': len(documents),
               'bytes_read': sum(d['bytes'] for d in documents), 'unique_contents': len(canonical),
               'duplicate_copies': len(documents)-len(canonical), 'failures': failures,
               'kinds': dict(Counter(d['kind'] for d in documents)),
               'encodings': dict(Counter(d['encoding'] for d in documents)),
               'method': 'full automated content reading/hash; heuristic thematic indexing; no original file moved'}
    (a.data_output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    intro = ('Gerado pela leitura integral automatizada do corpus textual. As áreas são um índice de navegação; '
             'uma ocorrência de palavra não valida a conclusão. Relatórios antigos podem ter aditamentos e retificações. '
             'Consulte ESTADO_ATUAL.md para a revisão técnica desta rodada.\n\n')
    index = ['# Catálogo temático dos estudos — 30/09/2026\n\n', intro,
             f'{len(documents):,} arquivos lidos, {len(canonical):,} conteúdos distintos, '
             f'{summary["duplicate_copies"]:,} cópias idênticas; {summary["bytes_read"]:,} bytes.\n\n',
             'Os originais permanecem em suas pastas. Evidências de assembly e logs aparecem separadas da documentação narrativa.\n\n',
             '- [Estado atual e retificações](ESTADO_ATUAL.md)\n',
             '- [Arquitetura e mapa técnico](ARQUITETURA.md)\n',
             '- [Inventário real do jogo e validação](VALIDACAO_FORMATOS.md)\n',
             '- [Catálogo completo](CATALOGO_COMPLETO.md)\n',
             '- [Duplicatas preservadas](DUPLICATAS.md)\n',
             '- [Links antigos sem destino](LINKS_ANTIGOS.md)\n\n']
    for key, (title, _) in AREAS.items():
        page = a.catalog / (key + '.md')
        records = [d for d in canonical if key in d['areas']]
        narrative = [d for d in records if d['kind']=='documentacao']
        evidence = [d for d in records if d['kind']!='documentacao']
        body = ['# ' + title + '\n\n', intro,
                f'{len(narrative)} documentos narrativos e {len(evidence)} evidências únicas. Um documento pode participar de várias áreas.\n\n']
        for section, items in [('Documentação', narrative), ('Evidência técnica', evidence)]:
            body.append('## ' + section + '\n\n')
            for d in sorted(items, key=lambda x: x['path']):
                label=d['title'].replace('[','(').replace(']',')').replace('\n',' ')
                body.append(f'- [{label}]({link(root/d["path"],page)}) — {d["bytes"]:,} bytes' + (f'; {len(d["duplicates"])} cópias idênticas' if d['duplicates'] else '') + '.\n')
        page.write_text(''.join(body), encoding='utf-8')
        index.append(f'- [{title}]({key}.md) — {len(records)} conteúdos.\n')
    index.append('\n## Etapas técnicas\n\n')
    for key in STAGES:
        page=a.catalog/('etapa_'+key+'.md')
        records=[d for d in canonical if key in d['stages'] and d['kind']=='documentacao']
        body=['# '+key.replace('_',' ').capitalize()+'\n\n',intro]
        for d in records:
            body.append(f'- [{d["title"].replace("[","(").replace("]",")")}]({link(root/d["path"],page)}).\n')
        page.write_text(''.join(body),encoding='utf-8')
        index.append(f'- [{key.replace("_"," ")}]({page.name}) — {len(records)} documentos.\n')
    (a.catalog/'README.md').write_text(''.join(index),encoding='utf-8')
    page=a.catalog/'CATALOGO_COMPLETO.md'
    body=['# Todos os arquivos textuais lidos\n\n',intro]
    for d in documents:
        body.append(f'- [{d["path"].replace(chr(92),"/")}]({link(root/d["path"],page)}) — {d["bytes"]} bytes; SHA-256 `{d["sha256"]}`; {d["encoding"]}.\n')
    page.write_text(''.join(body),encoding='utf-8')
    page=a.catalog/'DUPLICATAS.md'
    body=['# Conteúdos idênticos preservados\n\nA igualdade foi medida por SHA-256 do arquivo inteiro. Nenhuma cópia foi excluída.\n\n']
    for d in canonical:
        if d['duplicates']:
            body.append(f'## {d["title"]}\n\nPrincipal no índice: [{d["path"]}]({link(root/d["path"],page)}).\n\n')
            body.extend(f'- [{alias}]({link(root/alias,page)})\n' for alias in d['duplicates'])
            body.append('\n')
    page.write_text(''.join(body),encoding='utf-8')
    page=a.catalog/'LINKS_ANTIGOS.md'
    body=['# Referências antigas sem destino local\n\nLinks encontrados em Markdown; podem apontar a ferramentas ou snapshots removidos antes desta auditoria. Não comprovam que uma ferramenta ainda esteja disponível.\n\n']
    broken=[]
    for d in canonical:
        if d['kind']!='documentacao':
            continue
        source=root/d['path']
        text=read_text(source.read_bytes())[0]
        for target in re.findall(r'\]\(([^)]+)\)',text):
            target=unquote(target.strip('<>').split('#')[0])
            if not target or re.match(r'^[a-zA-Z]+://',target):
                continue
            if not (source.parent/target).exists():
                broken.append((d['path'],target))
                body.append(f'- [{source.name}]({link(source,page)}): `{target}`\n')
    page.write_text(''.join(body),encoding='utf-8')
    (a.data_output/'broken_links.json').write_text(json.dumps(broken,ensure_ascii=False,indent=2),encoding='utf-8')
    summary['broken_links']=len(broken)
    (a.data_output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
