# FIFA Mods

Mods e ajustes para o modo carreira do FIFA 16.

## Instalação

Copie o conteúdo desta pasta para a raiz da instalação do FIFA 16, mantendo a estrutura de diretórios. Faça um backup dos arquivos originais antes de substituir qualquer arquivo.

Existe apenas uma DLL de entrada: `dinput8.dll` na raiz do jogo. Não copie
outra `dinput8.dll` para `ModCarrerMode`; a cadeia `dinput8_career_chain.dll`
continua sendo carregada pela DLL da raiz para preservar os demais mods.

## Estado atual dos mods

Snapshot funcional conferido com a instalação em `U:\fifa 16` em
28/09/2026. A DLL nativa e o layout do modo carreira estão com o mesmo
SHA-256 no pacote e no jogo.

### Núcleo nativo do modo carreira

`dinput8.dll` é o ponto de entrada ativo. Ele reúne as implementações que
estão sendo tratadas neste pacote:

- cards do modo carreira e estatísticas do Meu Time;
- mensagens de ausência de dados somente quando o card está vazio;
- separação visual entre Liga e Copa na aba Competição;
- card Próxima partida com data/hora alinhadas, estádio, imagem, capacidade
  total e percentual de público estimado quando o cálculo está disponível;
- leitura do estádio e dos assets de kits/escudos;
- fluxo de aposentadoria por idade, com backup, alteração restrita ao DATA,
  recomputação/validação dos CRCs e restauração automática se a validação
  falhar.

### Plugins ativos

Estas quatro entradas estão habilitadas em
`ModCarrerMode/mods/enabled.txt`:

- `crowd/crowd_plugin.dll` — cálculo/runtime de público e fator de presença;
- `career_birthdate_2006/birthyear_range_2006_2012.dll` — faixa de ano
  2006–2012 no Player Career. A persistência da data depende também do
  watcher externo descrito no README do plugin;
- `bench12_global_limit_12_v2/global_limit_12_v2.dll` — limite global de
  banco relacionado ao pacote `bench12`;
- `substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll`
  — regra nativa para sete substituições. O carregamento e a escrita foram
  instrumentados, mas a confirmação final deve ser feita em uma partida
  iniciada do zero.

O `retirement_offline_worker.exe` também faz parte do pacote e está habilitado
pela configuração `ModCarrerMode/career_retirement_background.ini`.

### Plugin desativado

`easfc_hide_plugin.dll` permanece no pacote apenas para rollback/estudo e não
é carregado. Ele foi desativado após o crash de acesso inválido registrado no
processo do FIFA. A versão segura fica em `source/easfc_hide_plugin_safe` e
continua fora da lista ativa até um teste separado.

## Diagnóstico nativo do modo carreira

O arquivo `ModCarrerMode/career_native_mode.ini` controla a verbosidade dos
logs nativos. O módulo é o mesmo nas duas branches; o arquivo de configuração
define o ambiente do pacote:

- `mode=production`: mantém somente diagnósticos críticos e não grava os dumps
  volumosos de cards e snapshots.
- `mode=development`: mantém os logs completos para investigação.
- `mode=trace`: reservado para instrumentação adicional.

A DLL lê esse modo quando o FIFA inicia. Depois de alterar a configuração,
feche e reabra o jogo.

O código-fonte e o script de compilação desta DLL ficam em
`ModCarrerMode/source/career_native`. O artefato instalado continua sendo o
`dinput8.dll` na raiz deste repositório.

## Branches

`main`, `dev` e `backup` são mantidas com o mesmo snapshot de arquivos neste
momento, conforme a política de espelhamento do pacote. A branch `backup` é a
referência de recuperação; a diferença entre desenvolvimento e produção deve
ser controlada por configuração e validação, não por arquivos divergentes.

## Aposentadoria e traduções

O card arma uma solicitação única para o modo carreira. Depois que o save é
liberado ao sair da carreira, o worker aguarda `DATA`/`INDEX` estabilizarem,
cria backups, corrige o `DATA`, recalcula os CRCs e valida o resultado. Arquivos
`DATA` auxiliares pequenos são ignorados.

As correções de textos ficam em `tools/localization/career-mode-labels.json` e
nas bases `data/loc/*.db`. A configuração ativa está em
`ModCarrerMode/career_retirement_background.ini`; a versão de referência fica
em `career_retirement_background.ini.example`.

