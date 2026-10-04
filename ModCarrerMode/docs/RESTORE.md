# Voltar à versão anterior

Backup completo feito antes de reorganizar:

`J:\mods\backup\ModCarrerMode_antes_reorganizacao_20261003_080145`

## Restaurar somente o Dev

1. Feche qualquer compilação em andamento.
2. Mova a pasta Dev atual `ModCarrerMode` para uma nova pasta de segurança fora do repositório. Não a apague: isso preserva alterações feitas depois da reorganização.
3. Copie `dev/ModCarrerMode` do backup para o lugar original no repositório Dev.
4. Restaure `dev/dinput8.dll` do backup na raiz do repositório.
5. Se quiser voltar também à documentação anterior, restaure `dev/README.md` na raiz do repositório.

Os dados `dev/data/` também foram copiados para o backup. A reorganização não modifica os bancos de idioma; não é necessário restaurá-los para apenas voltar à estrutura anterior.

## Jogo

Nenhuma instalação no jogo foi realizada durante esta reorganização. A cópia `jogo/ModCarrerMode` e `jogo/dinput8.dll` registra o estado anterior para segurança, caso seja útil futuramente.

Não misture diretórios antigos e novos ao restaurar o Dev: guarde a pasta atual primeiro e restaure a pasta completa. O leitor novo prioriza as configurações de `config/` quando elas existem.
