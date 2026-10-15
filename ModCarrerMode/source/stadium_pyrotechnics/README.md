# Stadium Pyrotechnics — pirotecnia para qualquer time

O módulo `stadium_pyrotechnics.dll` oferece pirotecnia para qualquer time. Na abertura, usa as duas cores institucionais do mandante; após um gol, os efeitos são acionados somente para o mandante.

## Comportamento

- Abertura de 60 segundos, acionada pela apresentação real da partida com duas equipes nativas confirmadas.
- Gol do mandante: 25 segundos de efeitos. Gol do visitante não inicia um novo show.
- Fogos, confete e duas camadas de fumaça; encerramento gradual das fontes, com cauda de partículas incluída na duração.
- Todas as 20 máquinas disparam na abertura; as 12 traseiras disparam imediatamente no gol do mandante.
- Os 11 grupos de partículas respeitam o trigger externo: cada gol e reinício da partida renova o relógio de emissão das instâncias reutilizadas, mesmo depois de terminar a abertura. Instale o `.lnx` atualizado junto da DLL.
- Cada máquina usa grupos privados (`iInstancing=0`). No modo compartilhado anterior, o caminho nativo de instâncias podia pular a emissão e a limpeza de um emissor atingia os buffers compartilhados. O modo privado preserva os limites por ponto e permite o reinício de cada máquina no gol.
- Os efeitos usam orientação fixa, sem rotação conforme o lado do campo. A posição de saída acompanha a boca da máquina.
- Prévia de estádio, seleção de uniformes e outros menus não acionam abertura. Reiniciar Partida rearma abertura e detector de gols.
- Pausa e replay preservam as instâncias e partículas do show em andamento. O tempo nesse menu não consome a duração restante; retornar continua o mesmo show, sem disparar outro gol.
- O recurso de partículas é pré-carregado na prévia da partida, sem criar ou disparar emissores. O Server16 acompanha a preparação e a confirmação nativa da cena em segundo plano; os avisos de carregamento da apresentação estão ocultos.
- A pausa interrompe a emissão em curso e preserva o evento consumido e o placar. Voltar à partida, abrir seleção de lados/detalhes ou reconstruir tabelas Lua não rearma a fumaça. Abertura e gols do mandante são os únicos disparos automáticos.
- Sem comandos F7/F8: os gatilhos são automáticos.

## Compilação

Na raiz do repositório:

```powershell
.\ModCarrerMode\source\stadium_pyrotechnics\build.cmd
```

O script executa sete testes antes de compilar `stadium_pyrotechnics.cpp`, com MSVC C++17 x64 e `/W4 /WX`. Saída: `ModCarrerMode/source/stadium_pyrotechnics/build/stadium_pyrotechnics.dll`.

`prepare.py` prepara os recursos atuais de `assets/` para o build, preservando o código do runtime. Os estudos e revisões anteriores ficam separados do módulo atual.

`python ModCarrerMode/source/stadium_pyrotechnics/test_assets.py` verifica os 11 grupos, o reinício por trigger externo e as referências entre partículas.

## Instalação manual

Feche o FIFA. A partir do pacote local de recursos, coloque os arquivos nos seguintes destinos, relativos à pasta de `FIFA16.exe`:

```text
ModCarrerMode/mods/stadium_pyrotechnics/stadium_pyrotechnics.dll
ModCarrerMode/mods/stadium_pyrotechnics/pyro.ini
ModCarrerMode/config/match_presentation.ini
data/sceneassets/particles/stadium_pyrotechnics_0.lnx
data/sceneassets/particles/stadium_pyrotechnics_0.rx3
```

O par `.lnx/.rx3`, a DLL e as configurações correspondentes estão incluídos no pacote publicado. O build C++ atualiza a DLL; preserve o par de recursos ao instalar.

Em `ModCarrerMode/mods/enabled.txt`, adicione uma única entrada:

```text
stadium_pyrotechnics\stadium_pyrotechnics.dll
```

Mantenha uma única entrada deste módulo e reabra o FIFA após a instalação.

O instalador `ModCarrerMode/tools/maintenance/Install-Game.ps1` também aplica o pacote e preserva as configurações locais. A instalação manual acima não depende de caminhos específicos da máquina de desenvolvimento.

## Configuração

Em `ModCarrerMode/mods/stadium_pyrotechnics/pyro.ini`:

```ini
[pyro]
enabled=1
```

O runtime atual é automático. `enabled=0` desliga o módulo na próxima inicialização.

Em `ModCarrerMode/config/match_presentation.ini`:

```ini
[match]
pyrotechnics=1
entrance=1
goal=1
```

`pyrotechnics` é a chave geral; `entrance` e `goal` controlam separadamente abertura e gol. Preserve as outras chaves e preferências existentes ao editar. Essas opções são consultadas durante a sessão; na ausência delas, a pirotecnia fica desativada por padrão. O mascote pode ser desativado pela sua entrada em `enabled.txt`.

## Diagnóstico e desativação

Log: `ModCarrerMode/logs/stadium_pyrotechnics.log`. Os registros `MATCH_DETECTED`, `SHOW_STARTED` e `HOME_GOAL_CONFIRMED` identificam os gatilhos. `SLOT_UNAVAILABLE`, `ASSET_TIMEOUT` ou `UNSUPPORTED_IMAGE` indicam por que o show não iniciou.

Para desativar, ajuste os controles acima ou comente a entrada da DLL em `enabled.txt` e reinicie o FIFA. Use apenas a DLL canônica atual, evitando carregar revisões históricas juntas.
