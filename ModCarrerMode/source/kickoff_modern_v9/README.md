# Saída de bola moderna — versão 8

Versão aprovada em partida pelo usuário em 10/10/2026, com o banco de 12 reservas v8 ativo.

- O receptor fica atrás da marca central, na diagonal e olhando para a bola.
- O primeiro passe segue para esse receptor.
- Antes do passe, o cobrador perto da marca central olha para o receptor no pr�prio campo. A rota��o para ao preparar o passe.
- Os outros titulares da equipe cobradora que estejam dentro do círculo são afastados radialmente para 10,25 metros da marca central. A regra usa posição, equipe e papel do atleta; não depende de nome, camisa, ID, clube ou estádio.
- O cobrador e o receptor são excluídos dessa regra adicional. Reservas e adversários também são excluídos.
- A posição permanece corrigida durante a cobrança, inclusive pulando as cenas.

O plugin espera pelas chamadas nativas antes de instalar, para carregar pelo host após reiniciar. Aplica quatro adaptações de CALL e uma troca guardada da entrada física da vtable somente em RAM; o executável em disco não muda. O método físico original continua sendo chamado para todos os jogadores. O mod não usa Frida.

Carregamento: `kickoff_modern_v9/kickoff_modern_v9.dll` em `ModCarrerMode/mods/enabled.txt`. Apenas uma versão de saída de bola deve estar habilitada. Log: `ModCarrerMode/logs/kickoff_modern_v9.log`. Para desativar, comente a entrada e reinicie o jogo. As versões anteriores estão preservadas como protótipos desabilitados.

Código, teste e compilação: `ModCarrerMode/source/kickoff_modern_v9/`, execute `build.cmd`. MSVC C11 /W4 /WX passou. O teste de distância cobre interior, limite e exterior do círculo, lados espelhados, cobrador/receptor, reservas/adversários, altura e vetores inválidos. No jogo o usuário confirmou a saída, o afastamento do terceiro titular, a abertura com banco corrigido e uma substituição.

DLL SHA256: `89E8E5746B15B7F67E1B7C89B82E511B52ED63AF7BFFBDF8DF1D4082574ECE52`.
Executável analisado SHA256: `889772d3192c74ce4c1f2b7b3467cc96f9f1123aaf347bce7b199333dbac7a9d`, timestamp PE `0x577DE45C`. Outros builds são recusados pelas verificações de imagem e chamadas.

Instalado no jogo `U:/fifa 16` e no desenvolvimento `U:/mods/FIFA Friends V12`. O banco v8 está nas duas instalações e conserva 12 reservas e a liberação do adicional substituído. Backups e capturas ficam em `J:/mods/fifa 16/estudos fifa 16/16_KICKOFF_RAM_20261010/`.

Segundo tempo, saída após gol e outras equipes ainda podem ser ampliados nos próximos testes. Nenhum commit ou push foi feito nesta entrega.
