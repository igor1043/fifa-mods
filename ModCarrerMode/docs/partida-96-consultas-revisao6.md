# Entrada em partida com ligas grandes: revisão 6

Branch: `fifa-friends-v12-integracao-suico`. V12 e V12-backup permanecem intactas.

## Falha observada

Processo FIFA16 PID 7396, aberto em 06/10/2026 às 16:02. O `crash.dmp` foi
gerado às 16:10:18. O endereço da exceção atual é `exe+0x5810EC4`, uma escrita
em `rdx+r8` dentro da rotina de alocação. A rotina está interpretando um ponteiro
para texto do interpretador como tamanho/controle de um bloco de memória.
Isso demonstra um estado corrompido nesse caminho do alocador, sem localizar
por si só a instrução que originalmente o corrompeu.

O ponteiro em `exe+0x379C940` observado no processo continua preenchido:
`0x1434AD290`. Portanto, a explicação recebida sobre alocador NULL em
`exe+0x5F18BA0` não descreve a exceção deste despejo. O minidump não contém a
página desse global; sua observação vem da leitura do processo ainda aberto.

O `memoryfw.ini` decodifica corretamente e tem 116 entradas AddAllocator.
É idêntico ao arquivo entregue pelo Swiss. Comparado à V12 confirmada, a única
mudança é SaveLoadPP, de 14 para 24 MiB. Esta revisão não edita esse arquivo.

## Caminho identificado e intervenção

O desenrolamento AMD64 da pilha encontra:

1. `exe+0x5B82550`: construtor de consulta, com vetor de **96 IDs**;
2. `exe+0x4044A8B`, compilação/análise da consulta;
3. parser WHERE e avaliação de expressões, incluindo `exe+0x5E2F540` e
   `exe+0x4B709C0`;
4. alocação que termina em `exe+0x5810EC4` com o estado corrompido.

O pool ampliado de nós da L9 está instalado e apenas sete de seus 64 slots
aparecem ocupados; o objeto atual está no slot 0. Não há evidência de esgotamento
desse pool neste instante. O patcher também registra a capacidade de fixtures
em 16.000; a carreira registra 4.868 fixtures, abaixo dela.

Foi acrescentada uma mitigação nativa no código do host: `league_query_batches.c`.
Ela mantém o construtor original, mas, para vetores de 31 a 102 IDs, executa
consultas de até 30 IDs e reúne os resultados no mesmo vetor de saída.
Assim evita a expressão monolítica de 96 clubes encontrada no caminho da falha.

O original percorre seis tipos de atributos e acrescenta os resultados ao vetor
existente (`exe+0x5B82704..0x5B8276A`). A adaptação preserva essa ordem: primeiro
o atributo, depois seus lotes; mantém os argumentos adicionais e não remove um
clube da liga. IDs repetidos são tratados como conjunto, conforme o predicado
WHERE original. Consultas com até 30 IDs seguem pelo original em uma chamada.

O hook aceita somente o executável com timestamp `0x577DE45C` e o prólogo
verificado de 15 bytes. O trampoline retém esse prólogo, continua no original e
registra informações AMD64 de unwind. Uma assinatura desconhecida conserva o
código original. O código não intercepta a exceção nem retorna dados inventados
para contornar a falha.

Configuração acrescentada ao final do INI, preservando o conteúdo anterior:

```ini
[LeagueQueryBatches]
Aktiv=1
MaxTeamsPerQuery=30
```

Log: `U:\fifa 16\ModCarrerMode\logs\league_query_batches.log`. Em nova execução,
deve registrar `APPLIED exe+05B82550`; ao processar a lista grande, `BATCHED`
informa a quantidade original, quantidade distinta, atributos e chamadas nativas.

## Alcance e validação

O build recompila o host V12 com suas funções originais, a integração Swiss e a
adaptação nova. RCDATA 101 (L9 original) e RCDATA 102 (funções Swiss selecionadas)
continuam os mesmos. Não muda DB, compdata, DLLs de áudio, arquivos de física,
save, formato de 96 clubes ou calendário de 95 rodadas.

Compilação concluída; recursos e exports conferidos. Não houve teste automatizado
ou inicialização automática do FIFA. A eliminação do travamento e a equivalência
dos resultados de consultas grandes precisam ser confirmadas no jogo: entrar em
partida, conferir escalação/clubes disponíveis e acompanhar a carreira.
O ponto exato que corrompe o parser não foi conclusivamente identificado; a
intervenção reduz a consulta no caminho confirmado da falha. A validação da
temporada de 95 rodadas continua pendente como na revisão anterior.

É necessário reiniciar o FIFA. A memória já corrompida da execução anterior não
é recuperada com a troca de arquivos. Não é necessário apagar o save para aplicar
somente esta adaptação; nada foi apagado.

## Recuperação

Backup anterior a esta revisão:
`J:\mods\fifa 16\estudos fifa 16\backups\partida-allocator_20261006_161341`.

Preserva o dump, DLL/INI do jogo e os fontes/DLL/INI anteriores do Dev. O backup
da instalação possui o plano com hashes; `Restore-InstalledRevision.ps1` consegue
restaurar os arquivos do jogo a partir desse plano, preservando a revisão retirada.
O banco e a correção estrutural da Série D são preservados ao retornar a revisão 5.

Evidências reproduzíveis ficam em
`J:\mods\fifa 16\estudos fifa 16\06_PARTIDA_MEMORIA_20261006`: contexto da exceção,
pilha com unwind, disassembly, configuração decodificada e leitura dos objetos.
Os snapshots de memória são exclusivos desse PID e não são arquivos do pacote.

## Confirmação no jogo — 06/10/2026

Após a instalação da revisão 6, o usuário confirmou que conseguiu entrar na partida.
Esta confirmação cobre a entrada em partida relatada; equivalência de consultas,
persistência das estatísticas e temporada completa de 95 rodadas continuam pendentes.

