# FIFA 16 — laboratório offline de formatos

Ferramentas criadas em 30/09/2026. Não abrem processo, não acessam RAM, não
instalam mods e não alteram o jogo. Saídas devem ser novas e fora de
`U:\fifa 16` (ou da raiz passada explicitamente). Python 3.10+; biblioteca
padrão, exceto Pillow para a validação opcional de imagens.

## Entradas principais

| Programa | Função |
|---|---|
| `catalog_studies.py` | Lê o corpus textual inteiro, calcula hashes, separa duplicatas e cria índices temáticos |
| `inventory.py` | Enumera arquivos, lê assinaturas e visita diretórios BIG brutos até profundidade 4 |
| `review_inventory.py` | Refina desconhecidos pelo cabeçalho registrado e agrupa lacunas |
| `fifa_formats.py` | Inspeção/extração/rebuild BIG4/BIGF; decoder/encoder RefPack 10FB; subtipo chunkzip |
| `validate_assets.py` | Valida MUSE real, todos os RefPack inventariados e nove amostras de imagem |
| `validate_chunkzip.py` | Valida 13 amostras do subtipo e recupera o pacote skillmoveai |
| `test_formats.py` | Oito testes de estrutura, codecs, limites e proteção de saída |
| `verify_delivery.py` | Confere os hashes do corpus original e destinos dos links novos |

O inspector irmão `../muse/muse10fb_inspect.py` foi corrigido para usar o decoder
real. Seu JSON não fornece mais os antigos campos incorretos `value_a_be` e
`value_b_be`; informa `decoded_size_declared`, `decoded_size`, hashes e validação.

## Comandos

Execute no PowerShell, usando nomes de saída ainda inexistentes:

```powershell
Set-Location 'J:\mods\fifa 16\fifa-mods-dev\fifa-mods-dev\ModCarrerMode\tools\format_lab'
python -m unittest -v test_formats.py
python verify_delivery.py 'J:\mods\fifa 16\estudos fifa 16' 'runs\20260930_corpus'

python inventory.py 'U:\fifa 16' 'runs\nova_varredura'
python review_inventory.py 'runs\nova_varredura' 'runs\nova_revisao'
python validate_assets.py 'U:\fifa 16' 'runs\nova_varredura' 'runs\nova_validacao'
python validate_chunkzip.py 'U:\fifa 16' 'runs\nova_varredura' 'runs\nova_validacao' 'runs\novo_chunkzip'

python fifa_formats.py inspect 'U:\fifa 16\data\bcdata\muse\musedata-match.big'
python fifa_formats.py unpack 'U:\fifa 16\data\bcdata\muse\musedata-match.big' 'runs\exemplo_muse'
python fifa_formats.py decode 'runs\exemplo_muse\000000.payload' 'runs\exemplo_entrada0.xml'
python fifa_formats.py encode 'runs\exemplo_entrada0.xml' 'runs\exemplo_entrada0.10fb'
python fifa_formats.py pack 'runs\exemplo_muse' 'runs\exemplo_rebuild.big'
```

`pack` usa os payloads que estão na pasta extraída: **não substitui sozinho**
um payload pelo XML recodificado. Essa substituição consciente é feita somente
em cópia no teste `validate_assets.py`, que compara todas as entradas depois.

Para o subtipo chunkzip, os comandos são `decode-chunkzip entrada saída` e
`encode-chunkzip entrada saída`. Outros subtipos são recusados explicitamente.

Para atualizar somente os índices gerados dos estudos, preservando os originais
e as páginas de síntese escritas à mão:

```powershell
python catalog_studies.py 'J:\mods\fifa 16\estudos fifa 16' 'J:\mods\fifa 16\estudos fifa 16\03_CATALOGO' 'runs\novo_corpus' --refresh-generated
```

O catálogo deve ter o marcador conhecido no README. A pasta de dados do novo
corpus deve ser inédita. O script só indexa as árvores 00/01/02, evitando que
o catálogo entre recursivamente no próprio índice. A classificação é heurística;
consulte a síntese técnica para saber o que está comprovado.

## Contratos e limites

- **BIG:** nomes extraídos como metadados e arquivos numerados, evitando colisões
  de nomes repetidos e travessia de caminhos. Rebuild preserva ordem, nomes e
  bytes dos payloads. Não preserva necessariamente offsets/padding; não regenera
  `.bh` nem outros índices externos. Trailer do diretório é preservado opacamente.
- **RefPack:** variante observada `10 FB`, seguida de tamanho big-endian de três
  bytes. Suporta literais, backreferences e cópia sobreposta. Limite da variante:
  menos de 16 MiB de conteúdo. Fluxos com bytes finais extra são rejeitados.
- **Encoder RefPack:** compressão LZ gulosa, não promessa de saída idêntica ao
  compressor EA. A comparação correta é do conteúdo recuperado.
- **chunkzip:** somente versão 2, um bloco, descritor fixo observado; decoder
  valida DEFLATE com zlib e tamanho declarado. Writer até `0x2D000` bytes. Não
  admite automaticamente variantes retail com múltiplos blocos/descritores.
- **Inventário:** lê cabeçalhos e diretórios, não os 250 GB integralmente.
  Containers comprimidos e arquivos ZIP/RAR/7Z ficam marcados sem expansão.
- **CLI de extração/codecs:** entrada limitada a 64 MiB; o inventário por stream
  aceita pacotes maiores. `pack` usa memória proporcional ao pacote a reconstruir.
- **Validação:** XML por ElementTree, DEFLATE por zlib, imagens por Pillow.
  Scripts/bibliotecas presentes no jogo não são executados.
- **Segurança:** sem sobrescrita de saídas existentes, sem execução do jogo,
  sem alterações na instalação. Nenhuma saída experimental está pronta para
  instalar automaticamente; falta prova do consumidor real.

## Provas desta entrega

Na pasta ignorada por Git `runs/20260930_*`: inventário completo; 391 RefPack
decodificados; 387 entradas MUSE (386 XML + um Lua); cinco recompressões MUSE;
rebuild e edição XML isolada; 13 round-trips chunkzip; 193 ESIA recuperados;
nove imagens lidas; smoke tests da CLI. Oito testes unitários passaram.

As conclusões e as lacunas estão nos [estudos reorganizados](<../../../../../estudos fifa 16/03_CATALOGO/README.md>).

Referências primárias:
[RefPack.cpp](https://github.com/SSXModding/bigfile/blob/master/src/bigfile/RefPack.cpp),
[BIG/OpenSAGE](https://github.com/OpenSAGE/Docs/blob/master/file-formats/big/index.rst).
O subtipo chunkzip foi medido nos bytes locais e validado contra DEFLATE.
