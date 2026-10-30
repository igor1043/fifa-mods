# Finanças, próxima partida e resultados — revisão local de 30/10/2026

As consultas de receitas abrem pelo total de Direitos de TV, Bilheteria bruta ou
Patrocínio, tanto na visão geral quanto em Receitas. TV lista cada lançamento,
com filtros Casa, Fora e Todos, adversário, competição, situação e valor recebido.
Bilheteria conserva somente os jogos em casa e mostra receita bruta, custos e
líquida. Paginação funciona pelos botões e pelo analógico direito. Essas consultas
não criam lançamentos nem reaplicam dinheiro.

Patrocínio continua sendo um único lançamento. A composição provisória usa 60%
para master, 25% para secundários e 15% para material esportivo, conservando
exatamente o total inteiro recebido. Não há novos patrocinadores ou contratos
individuais nesta revisão. A tela de dívidas usa o logotipo do banco contratado;
bancos fictícios antigos sem imagem recebem um ícone neutro.

Os valores de Finanças e da bilheteria estimada recebem o prefixo da opção em
`career_managerpref.currency`. O nome dessa opção é lido do idioma instalado:
por exemplo, o patch pode renomear Dollar para Real e Pounds para Euros. A
formatação não aplica câmbio nem muda o inteiro armazenado. O cache dos três
nomes é invalidado pela revisão do arquivo de idioma. Em falha de leitura, o
número permanece visível, sem atribuir uma moeda por suposição.

A foto da próxima partida segue a chave de estádio usada pela Central: foto
convertida já instalada, miniatura FSW em DDS/JPEG/PNG/BMP e os sufixos numéricos
legados; estádios nativos podem usar o DDS do seu pacote de arte. Uma chave
explícita sem foto não recebe imagem de outro estádio por aproximação de nome.
O DDS da tela usa 1052×404, alinhado aos blocos DXT5; a largura visual é ajustada
ao card. A ausência de foto fica indicada. Capacidade e público seguem os
mesmos catálogos e configuração da Central.

A leitura de resultados é comum a todas as ligas. Campanhas publicadas em FCE
e em leagueteamlinks são alternativas: escolhe-se a evidência mais completa por
clube/competição, sem somar duas vezes. O perfil nativo aceita jogos/V/E/D
válidos mesmo quando o FIFA não conserva os gols individuais. Campos de gols
desconhecidos aparecem como “—”. O resumo do treinador só recebe os dados da
passagem identificada; campanhas sem partidas individualizadas não são
atribuídas a um substituto por suposição.

Validação: protocolo C++ com os 1.647 clubes das 101 ligas do catálogo desta
instalação; 1.235 clubes com jogos registrados. Dinamo Zagreb e Hajduk Split
foram conferidos com oito jogos europeus cada. Testes de navegação APT,
paginação, moedas, consultas sem mutação, checkpoints financeiros e resultados
parciais passaram. O save usado na verificação manteve o mesmo SHA-256.

Instalação local, sem commit/push e sem alterações nas regras de demissão ou
contratação do mercado de técnicos. O backup da instalação guarda os arquivos
anteriores, os novos caminhos e hashes para rollback.
