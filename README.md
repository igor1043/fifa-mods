# FIFA Friends V12

FIFA Friends V12 reúne recursos de carreira e apresentação da partida para FIFA 16: torcida, banco de reservas, substituições, saída de bola moderna, mascotes e bolas de reposição visuais. A pirotecnia acrescenta fogos, fumaça e confete com as cores do mandante.

## Recursos

### Modo carreira

- **Meu Time:** estatísticas dos jogadores e informações do clube, uniformes, estádio, capacidade e prestígio.
- **Competição:** informações de Liga e Copa, classificação, fases e partidas disponíveis.
- **Próxima partida:** adversário, competição, data, horário, estádio e público estimado quando disponíveis.
- **Aposentadoria:** remove a marca de aposentadoria; a opção de redefinir idade ajusta para 18 anos por padrão, preservando mês e dia.
- **Verba:** acrescenta 1.000.000 ou 3.000.000 à verba de transferências.
- **Integração do save:** publica o acesso ao save ativo e os dados nativos usados pelos cards da carreira.

As ações de aposentadoria e verba são processadas depois que você sai do save. Aguarde o autosave; na aposentadoria, escolha sair sem salvar. Permaneça no menu enquanto a camada mostra o andamento e reabra a carreira após a confirmação. O FIFA pode continuar aberto no menu durante o processamento.

### Apresentação e gameplay

| Mod | Comportamento | Guia |
|---|---|---|
| Mascotes v27 | Um mascote do mandante, caminhada entre pontos próximos, 30 segundos em cada ponto e 15 segundos de apoio. Seis variantes de gol, três gestos de apoio e restauração de poses pelo tempo do replay. | [Modelos, instalação e limitações](ModCarrerMode/source/mascot_photographer/README.md) |
| Pirotecnia | Fogos, fumaça e confete nas cores do mandante. Abertura de 60 segundos e gols do mandante por 25 segundos, com controles separados. | [Instalação e configuração](ModCarrerMode/source/flamengo_pyro/README.md) |
| Saída de bola v13 | Primeiro passe para trás, receptor na diagonal, cobrador voltado à defesa e outros atletas fora do círculo central. | [Instalação](ModCarrerMode/source/kickoff_modern_v13/README.md) |
| Bolas de reposição v16 | Treze cópias estáticas da malha e textura da bola da partida, ao redor do campo, sem física. | [Posições e funcionamento](ModCarrerMode/source/multiball_visual/README.md) |
| Banco de reservas | Até 12 reservas reais; modelos adicionais ficam ocultos fora de campo e são liberados na substituição. | [Banco de 12 reservas](ModCarrerMode/source/bench_native12/README.md) |
| Sete substituições | Limite de sete trocas; revisão 2 evita repetir a varredura completa enquanto o par de estruturas ativo permanece válido. O tamanho do banco é independente desse limite. | Fontes em `ModCarrerMode/source/substitution_all7_rulescan_native/` |
| Aviso de encerramento dos servidores | Confirma automaticamente o aviso português identificado, apenas com a janela do FIFA em primeiro plano. | [Mod opcional](ModCarrerMode/source/skip_server_shutdown_notice/README.md) |

Também inclui estimativa de ocupação da torcida na carreira, ícones de competições/pré-temporada, correção de miniaturas de goleiros, nascimento de jogadores entre 2006 e 2012 e integrações com Server16Python/CR16.

## Código e recursos locais

Esta atualização publica código, headers de animação, scripts, configuração e documentação. Modelos 3D atualizados, texturas, capturas de animação, DLLs/EXEs compilados, relatórios e backups ficam fora deste commit. Os binários e modelos já presentes em commits anteriores não foram removidos do histórico e podem representar versões anteriores.

Para usar os fontes atuais, compile os módulos e mantenha os recursos de jogo no pacote local. Os headers `mascot_goal_*_clip.h` já contêm as animações necessárias à compilação; os JSONs de captura não são necessários para gerar a DLL. Os modelos originais de edição também não são necessários à execução.

## Requisitos

- FIFA 16 **x64**, com executável compatível com as assinaturas verificadas pelos módulos.
- Carregador de plugins do pacote (`dinput8.dll` e sua cadeia de dependências).
- Windows e PowerShell para instalação.
- Para compilar: Visual Studio Build Tools com MSVC C/C++ x64 e Windows SDK. Os `build.cmd` usam `vcvars64.bat`; ajuste seu caminho caso a instalação do Build Tools esteja em outro local.
- Python 3 para as ferramentas opcionais de preparação/conversão; o Python não é necessário ao runtime das DLLs de mascote, saída, bolas ou pirotecnia.

## Pastas no jogo

Os caminhos abaixo são relativos à pasta que contém `FIFA16.exe`:

```text
FIFA16.exe
dinput8.dll
ModCarrerMode/
  mods/
    enabled.txt
    mascot_single/mascot_goal_line_v27.dll
    kickoff_modern_v13/kickoff_modern_v13.dll
    multiball_visual/multiball_visual_v16.dll
    stadium_pyrotechnics/stadium_pyrotechnics.dll
    stadium_pyrotechnics/pyro.ini
    bench_native12/bench_native12.dll
    substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll
    skip_server_shutdown_notice/skip_server_shutdown_notice.dll
  config/match_presentation.ini
  logs/
data/
  fifarna/lua/assets/sle.lua
  sceneassets/
    mascot/<ID_DO_CLUBE>/
    particles/stadium_pyrotechnics_0.lnx
    particles/stadium_pyrotechnics_0.rx3
```

## Instalação

Feche o FIFA e o Server16Python antes de instalar. Use a [branch FIFA Friends V12](https://github.com/igor1043/fifa-mods/tree/fifa-friends-v12).

### Pacote local completo

Com os binários compilados e recursos atualizados presentes na pasta de desenvolvimento, execute na raiz do pacote:

```powershell
.\ModCarrerMode\install-game.cmd -GameDirectory "C:\Caminho\para\FIFA 16"
```

O instalador geral copia os arquivos existentes no pacote, preserva configurações conforme suas opções e cria backups. Ele não compila as DLLs nem obtém modelos externos. Para atualizar só os mascotes, prefira o instalador específico descrito no guia.

### Compilação dos módulos atuais

Execute os comandos na raiz do repositório, em PowerShell, conferindo o resultado de cada um:

```powershell
.\ModCarrerMode\source\mascot_photographer\build.cmd
.\ModCarrerMode\source\kickoff_modern_v13\build.cmd
.\ModCarrerMode\source\flamengo_pyro\build.cmd
.\ModCarrerMode\source\multiball_visual\build.cmd
.\ModCarrerMode\source\substitution_all7_rulescan_native\build_v2.cmd
```

O build do mascote já copia sua DLL para `ModCarrerMode/mods/mascot_single/` no desenvolvimento. Para os demais, copie as saídas abaixo para os destinos do jogo, criando a pasta de cada módulo:

| Saída da compilação | Destino relativo à pasta do jogo |
|---|---|
| `source/kickoff_modern_v13/build/kickoff_modern_v13.dll` | `ModCarrerMode/mods/kickoff_modern_v13/kickoff_modern_v13.dll` |
| `source/flamengo_pyro/build/stadium_pyrotechnics.dll` | `ModCarrerMode/mods/stadium_pyrotechnics/stadium_pyrotechnics.dll` |
| `source/multiball_visual/build/multiball_visual_v16.dll` | `ModCarrerMode/mods/multiball_visual/multiball_visual_v16.dll` |
| `source/substitution_all7_rulescan_native/substitution_all7_rulescan_native_v2.dll` | `ModCarrerMode/mods/substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll` |

Os caminhos da coluna de origem começam em `ModCarrerMode/`. A pirotecnia exige também o par de recursos `.lnx/.rx3` e as configurações do seu guia. Para banco, carreira e outros módulos existentes, use os scripts próprios de seus diretórios; o build da carreira é `ModCarrerMode/source/career_native/build.cmd`.

### Habilitação

`ModCarrerMode/mods/enabled.txt` aceita um caminho de DLL por linha, relativo à pasta `mods`. `#` comenta uma linha. Adicione apenas módulos instalados e preserve as outras entradas do seu pacote. Exemplos:

```text
mascot_single\mascot_goal_line_v27.dll
kickoff_modern_v13\kickoff_modern_v13.dll
multiball_visual\multiball_visual_v16.dll
stadium_pyrotechnics\stadium_pyrotechnics.dll
bench_native12\bench_native12.dll
substitution_all7_rulescan_native\substitution_all7_rulescan_native.dll
```

Use uma versão por módulo. Para desativar, comente a entrada correspondente e reinicie o FIFA. Trocar arquivos ou entradas não atualiza uma DLL já carregada na sessão aberta.

## Como usar

- **Mascote:** entre em partida com um clube que tenha pacote local de modelo. O mod usa o mandante; as ações são automáticas. Confira os IDs e o Lua exigido no guia.
- **Pirotecnia:** habilite `pyrotechnics`, `entrance` e/ou `goal` em `ModCarrerMode/config/match_presentation.ini`. Não depende de teclas F7/F8.
- **Saída de bola:** dê o primeiro passe normalmente. A v13 prepara receptor, direção e orientação durante a saída.
- **Bolas extras:** aparecem automaticamente com a bola da partida; usam somente a bola, sem suporte adicional.
- **Carreira:** use os cards e siga a orientação exibida para operações no save.
- **Nascimento 2006–2012:** abra `ModCarrerMode/mods/career_birthdate_2006/dist/Fifa16BirthdateWatcher2006.exe` antes de criar o jogador.

## Verificação

Os builds de saída e pirotecnia executam seus testes antes de gerar a DLL. Para conferir políticas do mascote e os testes compartilhados da carreira:

```powershell
.\ModCarrerMode\source\mascot_photographer\verify.cmd
.\ModCarrerMode\source\career_native\test.cmd
```

Consulte `ModCarrerMode/logs/` se algum módulo não aparecer. No mascote, pacote ausente/incompleto ou ausência das categorias de atores suportadas mantém a cena original. No replay, apenas o histórico registrado nesta sessão pode ser restaurado. A compensação de esqueleto da v27 foi verificada offline; a aparência final em campo depende também do modelo local e deve ser conferida no jogo.

## New Experience

A New Experience é uma edição separada, com o card **Meu Escritório** e telas próprias de central/calendário, notícias, busca de clubes e ligas, competições, perfis, visualização 3D, ranking, operações, transferências, patrocinadores e sala de troféus. Está na [branch FIFA Friends New Experience](https://github.com/igor1043/fifa-mods/tree/fifa-friends-new-experience) e não faz parte deste pacote V12.
