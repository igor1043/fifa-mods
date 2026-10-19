# FIFA Friends V12

Mais vida na carreira, nos uniformes e na apresentação das partidas do FIFA 16.

O FIFA Friends V12 reúne melhorias para acompanhar seu clube, personalizar a experiência e dar mais identidade a cada competição. O [Server16](https://github.com/igor1043/CG-File-Server-16---Python-Port/tree/fifa-friends) é o painel que acompanha o projeto e permite escolher os recursos antes e durante a partida.

**Edição:** FIFA Friends V12 · **Atualizado em:** 19/10/2026

## Atualização — 19/10/2026

- **Carreira:** painel do Server16 para transferência de clube, proposta nativa de treinador, solicitação de verba e aposentadoria, com identificação automática da carreira aberta.
- **Ícones:** calendário e cards usam a mesma imagem por competição. Foram corrigidos os DDS e os BIGs necessários ao calendário; o teste no jogo confirmou os ícones após reiniciar.
- **Entradas e bolas:** prioridade da fase com herança da competição principal da base Robson 12.12 e tradução dos IDs de carreiras antigas. A exibição 3D ainda aguarda confirmação em partida.
- **Público e estádio:** pesos por competição na ocupação automática e suporte à foto nativa do estádio no card.
- **Técnico nativo:** ferramentas de conversão e reparo de braços, pesos e texturas para Eduardo Domingues/Atlético-MG. Os modelos ficam no pacote local; a estabilidade em partida continua pendente de teste.

Veja a [lista de arquivos e recursos publicados](ModCarrerMode/docs/ATUALIZACAO_2026-10-19.md).

## Aberturas — 18/10/2026

- **Base Robson 12.12:** o pacote da fase tem prioridade; uma fase sem pacote próprio herda o modelo da competição principal. A identidade de carreiras antigas é traduzida para a base instalada.

## Ícones por ID da competição — 18/10/2026

Calendário, card Próxima Partida da Central e cards de Competições compartilham
[uma pasta de ícones](data/ui/imgAssets/careerCompetitionIcons/README.md).
Use `<ID_DO_INI>.png`; o pacote já inclui as versões proporcionais para cada área.
Carreiras antigas são resolvidas pela identidade da competição, preservando o
mesmo logo em todos os meses. A DLL gera o BIG/APT e as texturas nativas de cada ícone ao iniciar.

### Atualização sobre a base do Robson

Com FIFA e Server fechados, copie os arquivos atualizados preservando os caminhos:

- `dinput8.dll` e os módulos `career_ui_assets`, `entrance_props` e `multiball_visual` em `ModCarrerMode/mods/`.
- A biblioteca `data/ui/imgAssets/careerCompetitionIcons/`, incluindo `calendar/`, `cards/` e `competitions.tsv`.
- Os BIGs e DDS de `data/ui/artAssets/cmCalendarCompetitions/`, `data/ui/imgAssets/cmCalendarCompetitions/` e os novos arquivos `l100*.dds` de `data/ui/imgAssets/league/light/` e `dark/` que acompanham a atualização.

Os BIGs do calendário são necessários; não os apague. A DLL os recria no próximo
início se faltarem. Para trocar a arte, edite `<ID_DO_INI>.png`, como `1761.png`
para a Série A e `1460.png` para a Libertadores nesta base. Confira os IDs aceitos
em `COMPETICOES.txt`. O Server prepara as texturas antes da próxima abertura do FIFA.

A atualização preserva os modelos de `entrance_props` e `standball` já instalados.
Após reiniciar, confira calendário, Central e cards de Competições; depois confira
a entrada e os suportes numa partida. Os ícones já tiveram confirmação visual
nesta instalação; entradas e suportes ainda aguardam essa confirmação.

## Câmeras do jogador — 18/10/2026

O Server16 incluído no pacote traz **Primeira pessoa** e **Terceira pessoa · carreira**.
No FIFA, escolha a câmera **Profissional**. Durante a partida, abra **Select + Start / F12 → Câmera**.
Ativação, modo e campo de visão ficam salvos. A primeira pessoa permite ajustar de 75° até 150°;
a terceira pessoa mantém a faixa de 60° a 90°. A abertura padrão é 85° nos dois modos, com suavização
Forte e enquadramento de campo e bola fixos. O acompanhamento inclui a espera para
reiniciar a jogada com a bola parada. Na terceira pessoa, Distância oferece Perto,
Intermediária e Afastada, com escolha salva e transição suave. O módulo da câmera está embutido no executável
do Server; o instalador do pacote distribui esse mesmo executável com os demais recursos.
O acompanhamento em terceira pessoa suaviza a translação e as viradas, com entrada
gradual dos movimentos e transição entre jogadores próximos.
A recuperação da câmera salva aguarda a inicialização nativa do FIFA antes de
consultar os ossos do jogador, evitando o crash durante a abertura do jogo.

## Destaques desta atualização — 17/10/2026

- **Base v12.11 com Honduras:** calendário e configuração sincronizados com o pacote oficial. Ícones e suportes reconhecem as identidades instaladas; as pastas de abertura foram alinhadas aos IDs atuais.

- **Camisas e calções com movimento:** física de roupas 0.8.2, com dobras, ajuste na barra do calção e controle pelo Server. Sua escolha fica salva. O recurso é experimental e começa desligado.
- **Goleiro com o uniforme correto:** corrigida a miniatura que aparecia branca no campo da aba Elenco e nas rotinas de escalação.
- **Ícones das competições corrigidos:** vínculos ajustados ao calendário instalado, evitando associações antigas entre competições e fases.
- **Novos ícones sem planilhas:** coloque uma imagem com o nome ou ID da competição; o Server atualizado prepara e cadastra o ícone automaticamente.
- **Bolas de reposição e suportes:** seleção por competição, identificação da liga em amistosos e suportes com tamanho reduzido.
- **Server com preferência de física salva e encerramento revisado:** mantém sua escolha e conclui a limpeza dos próprios recursos ao sair.
- **Tiro de meta em desenvolvimento:** posicionamento e passe curto ajustados em um módulo experimental.

## Melhorias disponíveis

### Acompanhe sua carreira

- **Próxima Partida:** adversário, competição, data, horário, estádio e estimativa de público, conforme os dados do jogo.
- **Meu Time:** jogadores, informações do clube, estatísticas, cartões e lesões.
- **Competição:** classificação, ligas, copas, fases e partidas.
- **Calendário com identidade:** ícones próprios para competições e pré-temporada, com importação automática de novas imagens pelo Server.
- **Gestão da carreira:** ferramentas de aposentadoria, idade e verba, seguindo as instruções exibidas no jogo.
- **Criação de jogador:** intervalo de nascimento adaptado para 2006–2012.
- **Compatibilidade de competições:** leitura das identidades e fases usadas pelos recursos da carreira.

### Mais identidade em campo

- **Física de roupas:** movimento de camisas e calções, com opção de ativar ou desativar antes e durante a partida.
- **Mascotes dos clubes:** caminhada, apoio e comemoração do mascote do mandante.
- **Abertura por competição:** arcos e placas do campeonato; em amistosos entre clubes da mesma liga, usa o conjunto dessa liga.
- **Escudos dinâmicos:** escudos dos clubes aplicados aos objetos da apresentação.
- **Bolas extras:** 13 bolas de reposição com o visual da bola da partida e suportes por competição.
- **Cabine do VAR:** objeto visual na beira do gramado nas Séries A e B do Brasileirão.
- **Pirotecnia:** fogos, fumaça e confete na abertura e nos gols do mandante, com cores do clube.
- **Máquinas de fumaça:** 20 equipamentos acompanham os efeitos do estádio.
- **Torcida:** uniformes dos clubes, estimativa de ocupação e ajuste de público pelo Server.

### Mais opções na partida

- **Banco com 12 reservas.**
- **Até sete substituições.**
- **Saída de bola moderna:** primeiro passe para trás e organização dos jogadores em volta do círculo central.
- **Tiro de meta moderno — experimental:** reposicionamento e passe rasteiro curto para zagueiros próximos; ainda precisa de avaliação em partida.

## Como começar

1. Use a instalação compatível do **FIFA 16 para Windows, 64 bits** e os pacotes de imagens, modelos e áudio desejados.
2. Com os programas fechados, instale o pacote compilado: `ModCarrerMode/install-game.cmd -GameDirectory "C:\Seu FIFA 16" -UpdateCompetitionData`.
3. Abra o **Server16 atualizado** e depois o FIFA.
4. No pré-jogo, entre em **Configurações da partida**, escolha as opções e confirme em **Aplicar**. Durante a partida, use o painel de **F12**.

Para ativar o movimento das roupas, escolha **Física de roupas > Aplicar** no Server. A opção controla camisa e calção juntos e fica salva para as próximas aberturas. Depois de atualizar o executável ou os módulos, reinicie o Server e o FIFA.

## Colocar outro ícone ficou simples

1. Com o FIFA fechado, coloque um **PNG ou JPG** em `data/ui/imgAssets/careerCompetitionIcons/`, dentro da pasta do jogo.
2. Use o nome ou ID da competição. Nesta edição, por exemplo: **`1761.png`** para a Série A. O arquivo **`COMPETICOES.txt`**, criado pelo Server nessa pasta, lista os nomes aceitos.
3. Abra o Server atualizado, aguarde alguns segundos e inicie o FIFA.

O Server cuida do tamanho, do formato e do cadastro. **Não é preciso editar o index.tsv nem converter a imagem manualmente.** Para trocar um logo, substitua a imagem original. Prefira PNG com fundo transparente e mantenha apenas uma imagem por competição.

Para instalar apenas os mods mantendo sua base atual, omita `-UpdateCompetitionData`. Essa opção instala a base oficial completa e guarda backup do DLC, settings.ini, banco e traduções substituídos. Consulte o [guia da base de competições](ModCarrerMode/docs/COMPDATA.md).

## Pacotes e disponibilidade

Os recursos visuais dependem dos respectivos modelos, texturas e imagens instalados. Mascotes, objetos de abertura, cabine do VAR, suportes das bolas e ícones são distribuídos em pacotes locais separados do código. Narração, músicas e vídeos também usam bibliotecas próprias. Sem um pacote visual válido, o objeto correspondente não aparece.

A cabine do VAR é visual: não altera decisões de arbitragem. As bolas de reposição e seus suportes são elementos de cenário. A física de roupas e o tiro de meta moderno são experimentais; aparência e desempenho podem variar conforme a instalação.

## Para quem desenvolve ou monta o pacote

- [Guia técnico, instalação e estrutura dos arquivos](ModCarrerMode/docs/GUIA_TECNICO.md).
- [Catálogo completo das implementações](ModCarrerMode/docs/implementations.json).
- [Detalhes da física de roupas](ModCarrerMode/source/cloth_motion/README.md).
- [Server16: configuração, áudio e personalização](https://github.com/igor1043/CG-File-Server-16---Python-Port/tree/fifa-friends).

A edição **New Experience** tem sua [própria branch](https://github.com/igor1043/fifa-mods/tree/fifa-friends-new-experience).
