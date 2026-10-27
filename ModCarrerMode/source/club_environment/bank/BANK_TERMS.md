# Catálogo de empréstimos do jogo

As taxas e os prazos de análise são parâmetros de simulação. Não representam
uma oferta real de crédito nem condições negociadas com clubes de futebol.

## Referência pública consultada em 24/10/2026

Banco Central, pessoa jurídica, capital de giro prefixado com prazo superior
a 365 dias, observações de **02 a 08/07/2026**:

https://www.bcb.gov.br/estatisticas/reporttxjuros/?codigoModalidade=211101&codigoSegmento=2

| Instituição | Média observada ao mês | Base no jogo |
|---|---:|---:|
| Caixa | 1,84% | 1,84% |
| Santander | 1,93% | 1,93% |
| Banco do Brasil | 2,05% | 2,05% |
| Itaú | 2,05% | 2,05% |
| Bradesco | 2,26% | 2,26% |

São médias de uma modalidade e de um período específicos, não taxas vigentes
garantidas em outubro ou para operações de qualquer valor. Banrisul (1,50%),
Sicredi (1,75%), Bmg (2,45%), Master (2,65%) e Crefisa (2,90%) têm bases
**simuladas**, sem atribuição de média real a essas instituições. Os adicionais
por valor e prazo também são regras do jogo. A interface mantém “Taxa simulada”.

## Resposta em dias da carreira

Bradesco/Crefisa: 1; Banrisul/Bmg/Sicredi/Itaú/Santander: 2;
Banco do Brasil/Caixa: 3; Master: 4. São dias corridos da carreira, incluindo
finais de semana. Esses tempos não são promessas de atendimento dos bancos.

O prazo é fixado na solicitação. O SQL armazena data enviada, data de resposta,
data de processamento e situação. Avançar o calendário não move essas datas.
Propostas e contratos já registrados mantêm a cotação e o prazo gravados.

A calibração migra apenas as taxas antigas que ainda coincidiam com os padrões
do protótipo, uma vez. Edições posteriores no bank_catalog permanecem válidas.
Nenhum DATA/INDEX é alterado por essa migração.

## Processamento

O leitor de pedidos é um serviço Python separado da geração dos arquivos APT,
ativo durante a sessão inteira. Sua thread usa somente um handle de leitura
(0x410). A aplicação financeira continua serializada na ponte e exige clube,
contexto, data, orçamento e tela estável confirmados. APIs nativas de e-mail
continuam exclusivamente na thread proprietária da interface do FIFA.

Recebimento e decisão têm IDs distintos. A fila nativa é publicada antes da
geração visual. O e-mail guarda a data original do evento; o recibo registra
separadamente quando foi inserido. A mesma operação não credita duas vezes.

### Captura direta do clique

A tela envia `Server16SubmitBank` pelo ION_CareerMode com o pedido explícito.
O adaptador consome somente esse evento e delega todos os outros ao dispatcher
original. A captura apenas lê contexto/data e grava uma mensagem pequena em
`native_request.tsv`; não chama APIs do FIFA nem modifica seu orçamento.
A ponte lê esse arquivo a cada ciclo, validando PID, clube, contexto, época e
nonce da sessão. Quando o protocolo está ativo, não é feita varredura do heap.
A data do clique vem do calendário nativo, mesmo se o APT exibido estava antigo.
`capture_delay_ms` no log mede o intervalo entre essa captura e o recebimento
pela ponte. A inserção dos e-mails mantém sua thread proprietária original.
