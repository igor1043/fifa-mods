# Pirotecnia do estádio

O diretório conserva o nome histórico `flamengo_pyro`, mas o módulo atual é `stadium_pyrotechnics.dll` e funciona para qualquer mandante compatível. As duas cores institucionais são recuperadas do banco FIFA local e incorporadas ao catálogo `team_palettes.h`.

## Comportamento

- Abertura de 60 segundos, acionada pela apresentação real da partida com duas equipes nativas confirmadas.
- Gol do mandante: 25 segundos de efeitos. Gol do visitante não inicia um novo show.
- Fogos, confete e duas camadas de fumaça; encerramento gradual das fontes, com cauda de partículas incluída na duração.
- Prévia de estádio, seleção de uniformes e outros menus não acionam abertura. Reiniciar Partida rearma abertura e detector de gols.
- A pausa interrompe a emissão em curso e preserva o evento consumido e o placar. Voltar à partida, abrir seleção de lados/detalhes ou reconstruir tabelas Lua não rearma a fumaça. Abertura e gols do mandante são os únicos disparos automáticos.
- Sem comandos F7/F8: os gatilhos são automáticos.

## Compilação

Na raiz do repositório:

```powershell
.\ModCarrerMode\source\flamengo_pyro\build.cmd
```

O script executa sete testes antes de compilar `stadium_pyrotechnics.cpp`, com MSVC C++17 x64 e `/W4 /WX`. Saída: `ModCarrerMode/source/flamengo_pyro/build/stadium_pyrotechnics.dll`.

`export_palettes.py` atualiza o catálogo a partir do banco local; a compilação normal já usa o header incluído. `prepare.py` preserva a preparação local de fontes e recursos e depende de entradas de estudo/build fora do Git; não é necessário executá-lo para compilar a DLL atual. Os arquivos `flamengo_pyro_v17.cpp`, `build_v17.cmd`, `native_signatures_v6.h` e `verify_v17.py` permanecem como entradas desse preparador, não como DLLs adicionais a habilitar.

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

Comente as entradas antigas `flamengo_pyro\flamengo_pyro*.dll`, preservando os outros mods. Reabra o FIFA após a instalação.

`install.py` automatiza essa operação no ambiente de desenvolvimento original, com jogo em `U:\fifa 16` e backup em `J:\mods\fifa 16\estudos fifa 16`. Antes de usá-lo em outro computador, ajuste esses caminhos e confirme que os recursos de `build/assets/` estão disponíveis. A instalação manual acima não depende desses caminhos locais.

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
