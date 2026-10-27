# Consolidação da V12 — 10/10/2026

## Implementações publicadas
- Mascote: pacote dinâmico por ID, segurança de pacote ausente, contexto compartilhado de animação/posição, comemoração de 26 s, troca de gol no intervalo, pontos de fundo do campo. Nome definitivo mascot_goal_line.dll. Modelos fora do Git.
- Bolas extras visuais: 13 cópias da bola atual, com suporte baixo, sem entidades de gameplay.
- Saída de bola moderna: receptor na diagonal, passe para trás, outros titulares fora do círculo; versão ativa v10, fontes de estudo anteriores preservados.
- Banco de 12: ocultação dos extras na abertura e liberação por atividade nativa quando substituídos.
- Carreira: catálogo de ícones de competição/pré-temporada e resolução dinâmica de DDS/BIG; disponibilidade de kits consultada nos assets.
- Loader/worker: compilados dos fontes atuais; guardas de handle/caminho de save recuperadas do stash.
- Dados atuais de competições: calendários, fases, tarefas, configurações e tabelas auxiliares.
- Stash: fontes VP8 recuperados e desativados, diagnóstico Swiss preservado em patch. O DLL antigo/configuração revertida não foram reativados. Stash original conservado.

## Arquivos locais excluídos
Modelos e texturas em data/sceneassets/mascot/<ID>, caches Python, builds, DLLs inativos, arquivos RAR e extrações duplicadas de FootballCompEng. Backups estão preservados localmente.

## Limitações
A filtragem de animação sentada do mascote falhou na conferência dentro do jogo e continua pendente. Testes sintéticos de postura não substituem validação visual. Bolas extras ainda requerem conferência próxima após reiniciar. Os modelos e a ferramenta externa de rig não são distribuídos por esta branch.
