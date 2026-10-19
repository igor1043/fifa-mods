# Publicação de 19/10/2026

## Recursos incluídos

| Recurso | Conteúdo |
| --- | --- |
| Ícones de competições | Biblioteca por ID do INI, 158 imagens para calendário/cards, cabeçalhos DXT5 corrigidos, BIG/APT e nomes nativos de DDS. |
| Objetos de entrada | Prioridade da fase e herança da competição principal da base Robson 12.12; tradução da identidade do save para a base instalada. |
| Bolas e suportes | Seleção por competição, configuração original de suportes do autor e identidade de carreiras antigas. |
| Painel de carreira | Troca de clube, proposta nativa ao treinador, solicitação de verba e aposentadoria. |
| Carreira ativa | Identificação automática do save carregado; prévias de slots e Configurações Pessoais não substituem a carreira. |
| Avisos e desempenho | Feedback de operações, progresso persistente e atualização de dados da carreira. |
| Público | Peso por competição na ocupação automática, incluindo Libertadores e competições brasileiras. |
| Estádio | Referência à imagem nativa do estádio quando não existe miniatura externa. |
| Treinador/mascote | Ferramentas de conversão, validação e reparo de antebraços, pesos, mangas e tabelas de textura do técnico nativo do Atlético-MG. |
| Distribuição | Fontes, módulos compilados, Server16Python atualizado, recursos 2D e ferramentas de manutenção. |

Os fontes/configurações de física de roupas, banco com 12 reservas, torcida com
uniformes, saída de bola moderna, máquinas de fumaça, pirotecnia, substituições,
compatibilidade de torneios e cabine do VAR também estão preservados na branch.
A maioria desses arquivos não apresentou mudança funcional adicional nesta
publicação: diferenças locais de quebra de linha não representam nova revisão.

## Base e limites

A correção parte do ModCarrerMode v12.12 de Robson, com settings.ini, CompData e
DB v12.11 - HONDURAS fornecidos pelo usuário. Os modelos externos permanecem
no pacote local, conforme as exclusões do repositório.

Os ícones foram confirmados pelo usuário depois de reabrir o FIFA. A exibição
das entradas e dos suportes 3D e a estabilidade do técnico nativo ainda precisam
de confirmação em partida. Publicar as alterações não muda esse estado de validação.

## Pastas principais

- `ModCarrerMode/source/`: implementação, configurações de origem e verificações existentes.
- `ModCarrerMode/mods/` e `ModCarrerMode/bin/`: módulos de execução.
- `data/ui/`: imagens, texturas, BIGs e layout da carreira.
- `Server16Python.exe`: aplicativo compilado do Server16.
- Repositório Python Port, branch `fifa-friends`: fontes do Server, overlay,
  importador de ícones, operações de carreira e runtime nativo de propostas.

Logs, saves, caminhos privados da carreira, backups de DLLs, temporários e
dependências locais de engenharia reversa ficam fora da publicação.
