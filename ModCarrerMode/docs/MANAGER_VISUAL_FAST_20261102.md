# Mercado de técnicos — preparação visual

A abertura posterior à entrega de 02/11 ainda reconstruía o catálogo inteiro
ao aparecer um título com uma identidade localizada diferente da competição
instalada. O log real registrou 84,708 s só nessa etapa.

- O catálogo inclui antecipadamente os IDs das competições e os aliases de
  troféus do CompData. Ganhar uma copa ou voltar a um save anterior mantém as
  imagens prontas, quando os arquivos instalados continuam iguais.
- A atualização reutiliza os blocos comprimidos das imagens e a geometria APT
  validada. Só o controlador e os dados atuais da carreira são recompilados.
  A ordem dos grupos nativos, os materiais e as texturas são preservados.
- As listas são codificadas como registros compactos. A leitura nativa converte
  somente os campos numéricos, em lotes limitados por quadro. O histórico
  detalhado continua sendo decodificado apenas ao abrir o perfil selecionado.
- O cálculo dos contratos continua em background. A publicação mantém a
  validação de processo, carreira, clube e data antes de entregar a tela.

Uma medição com os mesmos 1.730 clubes e aproximadamente 2 mil técnicos reduziu
a montagem com template de 12,572 s para 5,077 s na primeira utilização e
2,472 s na seguinte. São medições da montagem visual neste computador, não uma
garantia de tempo total de abertura em qualquer PC.

Na sessão real do FIFA, com o executável congelado do Server16, a etapa visual
levou 8,782 s e a publicação completa 18,521 s, incluindo leitura e cálculo.
Foram reaproveitados 574 blocos gráficos. Os 166 testes do mercado passaram
(um teste opcional de Lua ignorado). O arquivo nativo do save manteve o mesmo
SHA-256 durante a instalação na sessão aberta.

Atualize o código e instale também o pequeno complemento
`FIFA-Friends-Assets-Delta-Mercado-Tecnicos-20261102-R2.zip`, sobre os pacotes
anteriores. Ele troca apenas os três arquivos do catálogo visual preparado;
não repete modelos de técnicos, minifaces, vestiário ou saves.

Os testes cobrem os aliases de troféus, os registros nativos, o limite de pilha,
a integridade dos blocos gráficos, a troca de carreira e os perfis/controles.
