# Coletiva — versão press08

Abra **Sala-Imprensa.cmd**. O executável desta revisão é **Ambientes3D-press08.exe**; o atalho geral do visualizador foi preservado para não interferir no outro trabalho em andamento.

**Coletiva-Final-Exemplo.cmd** abre o exemplo do Flamengo com técnico e quatro jogadores do banco instalado, bola e troféu do campeonato. Não representa uma final detectada em um save.

## Controles da coletiva

Na aba **Sala**, configure os cinco lugares: **Vazio**, **Técnico do clube** ou um jogador do elenco. Selecionar uma pessoa já usada em outro lugar a move, sem duplicá-la. As cadeiras continuam disponíveis quando o lugar está vazio. Role o painel lateral para ver todos os controles.

**Final** coloca o troféu exato da competição no suporte reservado. **Competição = 0** usa a liga do clube no banco instalado; um ID explícito permite testar outra competição. Recarregue os recursos após alterar o ID. Recursos indisponíveis não são substituídos por um troféu de outra competição.

**Plateia** permite ocultar as pessoas e seus equipamentos, mantendo os 48 assentos. As vistas **Sala**, **Mesa**, **Diagonal**, **Completa** e **Plateia** reposicionam a câmera; **Completa** remove teto/laterais para inspeção. A câmera livre continua disponível com mouse, teclado e controle.

Clique em um participante da mesa para editar sua posição ou esqueleto. **Salvar cena / Ctrl+S** guarda os lugares, câmera, modo final, visibilidade e ajustes em XML, com backup ao sobrescrever. Salve em `presets/`, nunca na pasta do FIFA.

## O que esta revisão altera

- Sala ampliada, palco elevado, degraus, saída lateral de participantes e entrada traseira.
- Mesa escura com ripado, escudo do clube, bordas arredondadas, microfones de haste flexível, água, copos, gravadores, tablet e anotações. Sem título gigante na frente.
- Cinco cadeiras da mesa com estofados arredondados, apoio lombar e apoio de cabeça; 48 cadeiras de plateia com três variações discretas de tecido.
- Oito modelos nativos de público/imprensa, homens e mulheres, com e sem boné; quatro atividades: anotações, fotografia, microfone e vídeo. Pés no piso e superfície do assento vinculada ao contato da pose. As câmeras auxiliares originais não ficam abandonadas sob as cadeiras.
- Painel claro com uma textura quadrada repetida. Logos nativos extraídos dos banners instalados, sem os fundos de anúncio e sem deformar a proporção. Inclui o escudo do clube.
- Luzes internas posicionadas nas luminárias da sala, uma fonte principal com mapa de sombra e preenchimento das outras luminárias. Não é iluminação solar nem ray tracing.

Os patrocinadores são um conjunto demonstrativo comum, não uma afirmação de contratos de cada clube. O público usa poses estáticas próprias da coletiva, não animações ANT originais. O ambiente é procedural; pessoas, kits, bola, troféu e logos reutilizam os recursos instalados do FIFA.

## Verificação e segurança

**Testar-Imprensa.cmd** verifica Flamengo e Cruzeiro, os cinco lugares, 48 assentos, variedade da plateia, contato com assento/piso, edição isolada do técnico no palco, XML, modo final e cinco capturas por clube.

Backup anterior ao ajuste de plateia/cadeiras/painel: `backups/20261004-coletiva-plateia`.

Esta revisão foi feita somente no visualizador externo. Não instala nem escreve no jogo ou no Dev. O vestiário não recebeu novos ajustes por esta revisão.
