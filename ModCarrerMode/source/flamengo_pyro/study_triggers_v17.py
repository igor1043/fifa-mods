from pathlib import Path
import csv,json,hashlib
game=Path(r'U:\fifa 16')
dest=Path(r'J:\mods\fifa 16\estudos fifa 16\19_FLAMENGO_PYRO_20261010\v17_teste')
dest.mkdir(exist_ok=True)
comp=game/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata/compobj.txt'
rows={}
for row in csv.reader(comp.read_text(encoding='utf-8-sig').splitlines()):
    if len(row)!=5:continue
    idx,kind,ident,label,parent=row
    rows[int(idx)]={'id':int(idx),'type':int(kind),'identifier':ident,'label':label,'parent':int(parent)}
finals=[r for r in rows.values() if r['type']==4 and r['label']=='FCE_Final']
for f in finals:
    f['competition_identifier']=rows.get(f['parent'],{}).get('identifier')
    f['children']=[r['id'] for r in rows.values() if r['parent']==f['id'] and r['type']==5]
inventory={'active_in_dll':False,'source':str(comp),'source_sha256':hashlib.sha256(comp.read_bytes()).hexdigest(),
    'note':'Static stage catalogue only. Requires live stage ID and competition context before activation. Does not treat semifinals/quarterfinals as finals.',
    'final_stage_count':len(finals),'final_stages':finals,
    'mirassol':{'club_id':113163,'catalog_base_stadium_id':175,'package':'BRA - Jose Maria de Campos',
        'package_file':str(game/'StadiumGBD/BRA - Jose Maria de Campos.rar'),
        'display_name':'José Maria de Campos Maia - Mirassol - SP','shared_injection_slots':[176,261],
        'activation_requirement':'Confirmed Server16 applied package for this match generation, not just base or shared stadium ID.'}}
(dest/'gatilhos_estudados.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
report='''# Fogos, fumaça, papel picado e gatilhos — v17

## Entrega instalada

A v17 mantém o disparo automático para Flamengo 1043, como mandante ou visitante. A abertura está configurada para 60 segundos de teste; o gol, 25 segundos. Não há F7/F8. A abertura usa seis pontos nas laterais e quatro atrás dos gols. O gol usa oito pontos atrás dos gols (quatro por lado), preservando a distância longitudinal já aprovada e distribuindo-os transversalmente.

O reinício era perdido porque a identificação da sessão dependia de ponteiros que o FIFA reaproveita. A nova observação lê relógio nativo, placar coerente e página da interface no máximo quatro vezes por segundo. Uma volta sustentada ao começo, com 0 a 0, rearma a abertura e zera o detector de gols e seus maiores placares, as durações e os disparos pendentes. Uma interrupção das leituras durante recarga também pode fornecer evidência de reinício. A confirmação leva 500 ms. Páginas contendo `replay` bloqueiam essa confirmação. Mudanças transitórias não bastam.

Os testes cobrem reinício com os mesmos ponteiros, 0 a 0, recarga antes do relógio avançar, repetição do reinício, novo gol após reset, replay identificado, leitura transitória e relógio de intervalo. Isso verifica a lógica, não comprova ainda todas as transições reais do FIFA. Se o reinício não produzir nenhuma mudança observável — nem relógio/placar, nem recarga, nem contexto — falta um sinal nativo adicional para distingui-lo de uma pausa.

As instâncias continuam pertencendo ao motor; ao parar a apresentação, a DLL encerra emissão sem apagar instâncias ou descarregar assets. Ela não força a flag nativa de inicialização, que causou a regressão da v15. A substituição e os outros módulos não foram alterados.

## Fumaça mais espessa

Há controles no `.lnx`, mas não uma propriedade única de “densidade volumétrica”. O jogo desenha partículas com textura e transparência.

| Propriedade | Efeito | Valor atual da fumaça de base |
|---|---|---|
| `vColorMult`, componente alfa | Opacidade multiplicada pela textura | Vermelho 0,95; preto 0,98 |
| `vColorRamp` / `vColorRampTimes` | Fade ao longo da vida | Pico 0,95; trecho seguinte 0,75 |
| `iEmitRate` | Quantidade emitida por segundo | 150 por camada |
| `iNumParticlesMax` | Capacidade simultânea da camada | 850 |
| `ParticleActionKillAge/iAgeMs` | Tempo de sobreposição das nuvens | 6.500 ms |
| `fSizeMean` / `fSizeSpread` | Tamanho e variação das nuvens | 380 / 100, unidades internas |
| `vVelocityMean` / `vVelocitySpread` | Subida, deriva e dispersão | Média {55, 280, 15} |
| `sTexture` e `sTechnique` | Máscara de transparência e composição | `fx_rawcloud.dds`, `AlphaBlend` |

O alfa final depende da máscara da textura, do multiplicador e da curva. Assim, alfa 0,98 não torna toda a nuvem 98% opaca. Aumentar tamanho/altura espalha a mesma emissão por mais espaço e pode parecer menos denso. Para engrossar de verdade, o caminho é aumentar a sobreposição, sustentar o platô de opacidade e, se necessário, ajustar a textura. Na v17 os valores de fumaça são os da v16; no gol há 33% mais pontos, aumentando a emissão total de fumaça também. Não existe ajuste em tempo real dessas propriedades pelo INI nesta entrega.

## Mais papel picado

Cada ponto emite vermelho e preto. A taxa por cor passou de 1.400 para 2.000 por segundo e cada rajada de 350 para 450 ms. O intervalo total continua 4,5 segundos. Cada grupo de cor suporta 1.200 partículas simultâneas, antes 900. No gol, oito pontos substituem seis: cerca de 2,45 vezes a emissão programada por rodada de rajadas, antes da limitação de capacidade e dos descartes do motor. Não é uma contagem garantida de partículas visíveis.

O asset é compartilhado por abertura e gol, portanto as rajadas de papel também aumentam na abertura. A capacidade configurada de todos os grupos soma 52.510 partículas para os dez pontos da abertura, e 42.008 para oito pontos do gol. Isso é capacidade, não utilização constante nem medição de FPS.

## Partidas importantes

| Gatilho | Evidência encontrada | Situação |
|---|---|---|
| Final | `compobj.txt` distingue etapas com rótulo exato `FCE_Final`; o Server16 tem cadeia de competição e etapa (`TOURNAME`/`TOURROUNDID`) | Viável, precisa validar IDs em uma final real; catálogo gerado em `gatilhos_estudados.json` |
| Clássico | O módulo crowd já lê a tabela `rivals` do banco do FIFA, com pares de clubes e categorias | Viável reutilizar essa informação ou cadastrar pares no módulo; não ativado na v17 |
| Última rodada da liga | `schedule.txt` contém programação por etapa e rodada | Precisa comparar rodada atual e calendário da temporada; não assumir 38 nem confundir ID da etapa com número da rodada |
| Estádio normal | Lua `db.stadium[idx].stadiumID` recebe `wvStadium/stadID` | Viável por ID estável, com validação da sessão |
| Mirassol customizado | Regra `[stadium]` do Server16 e arquivo `.rar` identificam o pacote real | Viável por pacote aplicado; os IDs de injeção são compartilhados |

O helper gráfico `getTournamentFinal` não prova uma final: pode retornar verdadeiro por flag gráfica, distribuição da torcida ou estádio. Não deve ser o único gatilho. As etapas finais foram extraídas por igualdade exata, excluindo semifinal e quartas.

Na observação do jogo aberto, relógio e placar foram legíveis, mas os IDs de competição/etapa estavam indisponíveis. Portanto a identificação de finais ainda é estudo, não uma capacidade comprovada em jogo nesta DLL. As regras de elegibilidade podem ser calculadas uma vez por sessão e armazenadas; não há necessidade de pesquisar calendário ou banco a cada frame.

## Mirassol e Server16

- Clube: **113163**.
- Catálogo: estádio-base **175**, capacidade **13827** (capacidade não é ID).
- Regra `FSW/settings.ini`: `113163=BRA - Jose Maria de Campos,5,188,0`.
- Arquivo: `StadiumGBD/BRA - Jose Maria de Campos.rar`.
- Nome: **José Maria de Campos Maia - Mirassol - SP**.

O ID-base 175 aparece para outros clubes também. `stadium_runtime.py` prepara o modelo e assets do pacote em um dos slots **176/261**, confirma a escrita do ID em memória e só então registra `StadName`/`curstad` e `Applied stadium ... using injID=...`. Esses slots são reutilizados por outros estádios. A seleção de competições e escolhas manuais também pode sobrepor o estádio padrão do mandante.

O gatilho seguro deve receber o pacote confirmado e a geração da partida após `finish_stadium_apply`, ou identificar o asset efetivamente aplicado e validar seu contexto. Só testar 175, 176 ou 261 dá falsos positivos. Ler o nome do placar sozinho também é insuficiente: o Server16 escreve nos dois slots, e na observação atual ambos continham “AO VIVO”, não um estádio. Uma integração pequena de contexto confirmado com Server16 é o caminho mais seguro; não foi feita alteração no Server16 nesta entrega.

## Cores por time

O Lua do estádio expõe `homePrimaryColour`, `homeSecondaryColour`, `awayPrimaryColour` e `awaySecondaryColour`. Isso oferece uma fonte de cores da sessão, mas ainda é necessário validar o formato e se a cor corresponde ao uniforme do dia ou à identidade do clube. A v17 usa vermelho/preto do Flamengo. O gatilho Mirassol não está ativo e não herda uma paleta automaticamente. O branco das partículas e suas rampas também interfere na cor final.

## Performance e validação

O caminho ocioso mantém o detector de gols em 100 ms e leituras de reinício em 250 ms; identificação pesada de clubes ocorre a cada dois segundos, fora da apresentação. Não há espera por jobs para essas leituras. Banco, calendário e arquivos de estádio não são pesquisados por frame.

O log da v16 observado registrou aproximadamente 21–31 ms de CPU do módulo a cada 10 segundos ocioso. Isso não mede GPU/FPS; a v17 ainda precisa de observação real após carregar. Mais partículas podem elevar o custo de desenho durante os efeitos.

Build x64 MSVC com `/W4 /WX`; testes de duração, gol e ciclo de sessão passaram; referências de XML, assinatura do executável e 11 guardas nativas foram verificadas. O instalador salva backup e preserva a ordem e todas as entradas dos outros módulos.

Para carregar a DLL nova, feche e abra o FIFA uma vez. Teste Flamengo 1043: veja a abertura, faça gol, use Reiniciar Partida, veja a abertura novamente e faça outro gol. O log novo registra `MATCH_RESTART_CONFIRMED reset_intro_and_goal_baseline` quando o reset é confirmado. Basta reiniciar a partida para repetir depois que a v17 já estiver carregada.

## Fontes locais

- `U:/fifa 16/data/fifarna/lua/assets/stadium.lua`, cores e ID do estádio.
- `U:/fifa 16/data/fifarna/lua/assets/rm_common.lua`, distinção entre final gráfica e etapa real.
- `U:/fifa 16/dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata/compobj.txt` e `schedule.txt`.
- `J:/mods/fifa 16/01_Projetos/python_port/server16_py/app.py`, `offsets.py`, `memory_access.py`, `stadium_runtime.py` e `entrance_runtime.py`.
- `U:/mods/FIFA Friends V12/ModCarrerMode/source/career_native/src/features/crowd/crowd_runtime.c`, tabela de rivalidades.
- `U:/fifa 16/FSW/settings.ini` e `ModCarrerMode/data/catalogs/club_stadium_fallback.tsv`.
'''
(dest/'ESTUDO_GATILHOS_E_REINICIO.md').write_text(report,encoding='utf-8')
print(f'Study saved; exact final stages: {len(finals)}; optional triggers remain inactive')
