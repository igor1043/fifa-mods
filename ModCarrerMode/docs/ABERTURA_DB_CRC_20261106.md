# Correção confirmada da DB na abertura — 06/11/2026

As tentativas PIDs 46708, 26840, 6504 e a reprodução controlada 39136 falharam
em `fifa16.exe+0x4B6CB75`, durante a leitura de `data/db/fifa_ng_db.db`, antes da
criação do menu. A pilha nativa foi reconstruída com os registros da exceção e
os dados de unwind. Nenhuma carreira foi carregada nos testes.

## Causa desta reprodução

Na integração da DB dos Emirados/Atlante, a rotina externa `ComputeAllCrc`
gravou checksums no fim lógico de quatro tabelas cujo conteúdo não estava
alinhado. O checksum físico fica antes da próxima tabela, conforme o diretório,
depois dos bytes de preenchimento. A gravação fora desse ponto também deixou
quatro CRCs de cabeçalho inconsistentes. Os testes anteriores só releram as
linhas válidas; isso não verificava esses cabeçalhos como a engine faz.

A correção altera exatamente **32 bytes** da DB integrada, restaurando os
bytes auxiliares dessas quatro regiões. Todos os registros válidos das 137
tabelas permanecem idênticos. A liga dos Emirados, Atlante e as correções das
escalações continuam presentes. A metadata e os arquivos LOC ficam intactos.

- DB anterior com falha: `ea785ec7ee90cc05f2fc58f89b0d2693e1786fae0bfd2fca6d9840baa5e39a24`
- DB corrigida: `c0223b427e6a1a7cbf8543044d34b4475ac7d62606293ca3b453931fc201db50`

`fifa_db_crc.py` valida o arquivo, o diretório e os cabeçalhos/payloads de todas
as tabelas. Usa os deslocamentos físicos do diretório, inclui o preenchimento
e trabalha sobre cópias; não chama a rotina externa que modificava a entrada.

## Comparação controlada

Com os mesmos módulos e arquivos de interface:

- A DB original enviada por Robson chegou a LanguageSelect/PressStart.
- A DB integrada reproduziu o mesmo crash antes de criar uma página.
- A cópia com as correções de elenco, mas CRC antigo, também falhou.
- A DB corrigida chegou a PressStart.

A alteração preventiva de ordem de inicialização feita na revisão anterior
foi retirada: não foi a solução dessa reprodução. Os ajustes independentes do
mascote e do fundo ao sair da carreira permanecem.

O dump antigo de Robson em `+0x3A41F43` é uma ocorrência diferente. Esta análise
não estabelece que todo crash intermitente anterior do botão Launch tenha a
mesma causa. A correção aqui fica restrita à inconsistência reproduzida.

Relatório, testes, cópias e rollback:
`J:\mods\fifa 16\estudos fifa 16\relatorios\abertura-crash-recidiva-20261106`.

Instalação no jogo e desenvolvimento validada pelo usuário para publicação.
Três aberturas controladas chegaram a PressStart com os módulos ativos.
As 276 regiões de checksum passaram na validação; os 137 conjuntos de
registros válidos permaneceram idênticos. Saves e bancos pessoais não são
editados. O executável do Server16 não precisa ser recompilado para esta
correção da DB e a retirada da alteração preventiva da DLL principal.
