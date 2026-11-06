# Mascote e fundo do menu — 06/11/2026

Instalada no jogo e no desenvolvimento; validada pelo usuário e preparada para publicação em 06/11/2026.

## Mascote do clube

Em Ver clubes → Ver mascote, use **Comemorar** com o mouse, Enter ou o botão
principal do controle. O mesmo comando para a comemoração. Girar, centralizar,
zoom e voltar continuam disponíveis com as legendas nativas do FIFA.

A animação usa o clipe nativo de comemoração 108, adaptado ao esqueleto de cada
mascote. O modelo e suas texturas não são alterados. O stream privado começa
pausado, repete enquanto solicitado e retorna à pose original quando parado.
Clube sem mascote continua vazio; esqueleto não compatível mantém a pose estática.
O botão não interfere na área de arrastar para girar. A geração tem limite de
64 MiB/64 quadros e é reutilizada dentro do cache visual da sessão.

## Fundo depois de sair da carreira

O fundo conserva uma publicação de thread própria, obtida na fábrica nativa da
interface. Assim, deixar a carreira não interrompe a preparação do estádio do
menu. Um pulso do FluxHub mantém a atualização mesmo sem novos Updates do FCE.
O handler anterior de onEnterFrame é preservado e restaurado ao sair.

A imagem de cobertura só é retirada depois da confirmação de carregamento,
desenho da rota atual e estabilização do loader. A atualização do componente
visual continua na thread da interface, com validações de página, registro,
objeto e prazo; não chama o alocador de strings a partir de Render.

## Crash de abertura

A correção comprovada da DB está em [ABERTURA_DB_CRC_20261106.md](ABERTURA_DB_CRC_20261106.md).
A ordem de inicialização original foi preservada. A revisão preventiva que
adiava módulos foi retirada depois dos testes de comparação; ela não resolveu
a reprodução. As mudanças do mascote e do fundo não dependem dessa espera.

O dump antigo de Robson em +0x3A41F43 tem outro ponto de falha. Não há prova
de que todos os crashes anteriores do Launch tivessem a mesma causa da DB.

## Validação

- 30 testes Python: lookup, seleção/retorno, mouse/teclado/controle, streams,
  animação real de Flamengo/Grêmio/Fluminense e preparação de estádios.
- 13 testes do FluxHub: rodapé contextual, callbacks anteriores preservados,
  pulso do menu, entrada/saída e inicializador sem recursão.
- Testes nativos: 240 quadros no D3D WARP com buffers originais imutáveis,
  pausa/início/parada, publicação da cena, identidade do modelo, fila da interface
  após encerrar CareerContext, rejeição de outra thread e preflight dos patches.
- 77 arquivos de estado persistente e DB conferidos sem alteração.
- Cópias de runtime do jogo e desenvolvimento verificadas por SHA-256.

Além das verificações nativas, a DB corrigida chegou a PressStart em três
aberturas controladas, sem carregar uma carreira. O usuário confirmou o
funcionamento antes de autorizar esta publicação.

## Rollback

Backup e recibo ficam em:
`J:\mods\fifa 16\estudos fifa 16\relatorios\mascote-comemoracao-20261106`.
Com FIFA e Server16 fechados, `python rollback.py` nessa pasta restaura somente
os arquivos desta revisão. Saves, bancos da carreira e preferências não são
sobrescritos. O executável do Server16 não precisou ser recompilado: estes
módulos são carregados das DLLs e fontes externas da instalação.
