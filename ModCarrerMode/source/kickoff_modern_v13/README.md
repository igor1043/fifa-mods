# Saída de bola moderna

O primeiro passe da saída vai para trás. O receptor fica na diagonal, no próprio campo, e os demais atletas próximos são afastados do círculo central. O cobrador olha para a defesa antes do toque. A preparação contempla a apresentação completa, as cenas puladas e o reinício da partida.

## Compilar e instalar

Na raiz do repositório:

```powershell
.\ModCarrerMode\source\kickoff_modern_v13\build.cmd
```

O pacote já inclui a DLL compilada. O script executa `test_kickoff_spacing.c`, compila com MSVC C11 x64, `/W4 /WX`, e atualiza `ModCarrerMode/mods/kickoff_modern/kickoff_modern.dll`. O diretório dos fontes conserva o nome histórico. Destino no jogo:

```text
ModCarrerMode/mods/kickoff_modern/kickoff_modern.dll
```

Com o FIFA fechado, mantenha uma única versão da saída em `ModCarrerMode/mods/enabled.txt`:

```text
kickoff_modern\kickoff_modern.dll
```

Comente as versões anteriores e preserve banco, substituições e outros plugins. Reabra o FIFA e dê o primeiro passe normalmente. Não requer modelos, texturas ou mudanças no executável em disco.

## Implementação

A implementação cobre os dois publicadores nativos do comando de espera/entrada do cobrador. Apenas na saída ativa substitui o comando pela orientação ao próprio campo de defesa, preservando a prioridade original. Verifica assignment, atleta titular, receptor da mesma equipe, destino recuado e estrutura do comando antes de aplicar. Ao preparar o primeiro passe, encerra essas substituições.

Mantém fator 0,75 na carga do primeiro passe e a geometria de espaçamento. `Fifa16ModAdoptKickoff` permite adotar a saída pausada existente sem mudar as posições. As guardas recusam executáveis incompatíveis.

Log: `ModCarrerMode/logs/kickoff_modern_v13.log`. Para desativar, comente a entrada e reinicie o jogo.
