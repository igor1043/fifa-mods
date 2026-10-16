# Bolas de reposição com suportes 3D por competição

O `multiball_visual.dll` mantém as mesmas 13 bolas do mod existente, usando a
malha e a textura da bola da partida. Acrescenta um suporte RX3 sob cada bola,
sem física. A bola de gameplay permanece intacta.

| Competição | Suporte |
|---|---|
| Brasileirão Série A — 1738 | `brasileirao` |
| Série B — 1741; Série C — 1747; Série D — 1757 | `cbf` |
| Paulista — 2325, incluindo quartas 2330, semifinal 2335 e final 2338 | `paulistao` |
| Outras competições e amistosos sem associação | `generic1` ou `generic2` |

`standball.ini`, na pasta da DLL, contém os IDs exatos das competições e dos
seus descendentes no `compobj.txt` instalado. A fase tem prioridade sobre a
competição principal quando consta no mapa. IDs de liga como 7 e 83 não são
tratados como IDs de competição. Não existem associações por intervalo ou nome.

Em amistosos da mesma liga, utiliza o contexto produzido pelo Server16 para as
entradas, validando o processo, a data do arquivo e os dois clubes. Uma copa real
sempre mantém sua própria seleção. Sem contexto válido, utiliza o genérico.
Essa escolha independe do botão de objetos de abertura e da pirotecnia.

Revisão 2: amistosos podem não ter o ponteiro de competição da carreira. A
ausência desse ponteiro agora permite consultar o contexto válido do Server16
e, sem ele, aplicar o genérico a uma partida nativa confirmada. Uma falha de
leitura posterior conserva a seleção da mesma partida. O log informa a origem
da seleção (`native`, `friendly_same_league` ou `generic_fallback`).

`[standball] enabled=1` habilita os suportes. `generic_variant=0` alterna os dois
genéricos entre partidas, mantendo uma única variação nas 13 posições durante
pausas e replays. `1` ou `2` fixa o genérico correspondente. Desabilitar os
suportes conserva as bolas no gramado.

## Modelos e posicionamento

Os cinco FBX fornecidos em STANDBALL foram convertidos para malhas estáticas
RX3, com UV, textura difusa, normal e mipmaps. Os PNGs não são usados no jogo.
Os modelos ficam em `data/sceneassets/standball/<variação>/model.rx3` e
`textures.rx3`, no jogo e no desenvolvimento. A largura é de aproximadamente
19,5 cm (75% dos 26 cm originais), preservando as proporções dos modelos,
com cerca de 2.400 triângulos
por suporte. A prévia de conversão foi renderizada lendo os RX3 produzidos.

Os dez RX3 ficam fora do Git e permanecem instalados na pasta do jogo.
Um clone desta branch inclui o código e a configuração dos suportes; seus
modelos e texturas precisam estar instalados localmente. A verificação do
pacote aceita essa ausência. Sem os assets, a DLL mantém as bolas no gramado.

Os suportes compartilham os centros X/Z das bolas existentes. As marcas ficam
voltadas para o campo. A altura visual das bolas acompanha o encaixe medido na
geometria de cada suporte, recalculado para a escala de 75%. As bolas mantêm
seu tamanho original; somente os suportes foram reduzidos nos três eixos.
Sem recursos prontos ou com assets ausentes/alterados,
as bolas ficam na altura original de 11,1252 cm. As posições atuais permanecem:
quatro bolas atrás dos gols em X ±5520 cm e nove nas laterais em Z ±3620 cm.

## Carregamento e validação

O callback nativo de cena cria uma aparência privada do tipo 17, variação 1,
mantendo a aparência 0 dos câmeras. A DLL aguarda os hooks de entrada, VAR e
máquina de fumaça habilitados e preserva a cadeia. O Lua só redireciona essa
aparência privada. A troca de competição esconde os suportes anteriores antes
de recarregar o modelo; os cinco LODs devem estar prontos antes da exibição.
Os arquivos RX3 são conferidos por tamanho e SHA-256 antes da solicitação.

O desenho das bolas continua usando snapshots privados de 0x820 bytes,
preservando os 1–3 slots originais e acrescentando apenas as 13 cópias já
existentes. Não carrega RX3 nem executa Lua no callback de desenho da bola.
O Stop restaura os callbacks das bolas e esconde os suportes; o callback de cena
permanece encadeado até fechar o processo, como nos outros objetos estáticos.

`build.cmd` compila com MSVC x64 `/W4 /WX` e executa os testes de bolas e de
alinhamento. `verify.cmd "<raiz dos assets>"` executa o callback de produção em
uma cena nativa simulada: carregamento assíncrono, 13 bindings, troca de modelo,
retirada anterior à recarga, ciclo de recursos e Stop. Não abre nem modifica FIFA.
O mesmo comando executa a seleção real de cena com a cadeia de competição
ausente, o contexto de amistoso, o genérico, o replay, a chegada tardia do contexto,
a prioridade de uma copa real e a rejeição de outro processo/clube.
`test_standball.py --lua-python-path <pasta com lupa.lua51>` verifica seleção e
as seis ordens dos wrappers Lua de suporte, VAR e máquina de fumaça.

Para reproduzir a conversão: extrair os ZIPs, executar `export_stands.py` pelo
Blender, depois `convert_stands.py` e `render_stands.py`. Seus argumentos estão
disponíveis com `--help`. A conversão usa `--scale 0.75` por padrão sobre o
export original de 26 cm; o raio utilizado no encaixe da bola permanece igual.
`install_stands.py` instala o módulo e os assets nas
duas raízes, preserva configurações existentes e registra backup/manifesto.

Compilação, testes e prévia dos RX3 verificados. O carregamento da revisão 2
foi confirmado no FIFA pelos registros de seleção, recursos e 13 suportes
posicionados. A escala de 75% foi conferida na geometria convertida e na prévia;
sua aparência dentro do FIFA precisa de confirmação após reiniciar.
Logs: `ModCarrerMode/logs/multiball_visual.log` e `standball.log`.
