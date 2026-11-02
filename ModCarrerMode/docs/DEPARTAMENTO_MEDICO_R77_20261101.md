# Departamento médico R77

Reforma local do anexo oeste: aproximadamente 7,75 x 12,77 m, sem janelas,
com mais 480 cm de profundidade. A entrada permanece no mesmo lugar e a sala
do treinador R76, o vestiário e a hidratação não foram reposicionados.

## Setores e decoração

- Atendimento: mesa com tampo de madeira, computador, teclado, mouse, documentos,
  prancheta e três cadeiras. Monitor horizontal da situação médica do elenco.
- Preparação: bancada com armários superiores/inferiores, pia de inox com
  rebaixo e torneira curva, dispensador, frascos, caixas e toalhas organizadas.
- Tratamento: três macas paralelas, encostos elevados, toalhas com detalhe do
  clube, carrinhos com rodas, dispositivos, telas, controles, cabos e sondas.
  Bancos giratórios, suportes de toalhas, recipientes e três quadros anatômicos
  ilustrativos completam o setor. Estes desenhos não são material diagnóstico.
- Reabilitação: piso emborrachado, estação de cabos com pilha de pesos, banco,
  halteres, colchonete, bolas e plataforma de equilíbrio, segundo monitor.
- Identificação dinâmica: placas médicas, escudo do clube ao fundo e cores
  primária/secundária. Luminárias retangulares convencionais na malha do teto.

## Dados e acompanhamento

Lista de lesões, prazos e descrições vêm da carreira e da captura InjuryList
validada para a mesma sessão/clube/data. A disponibilidade representa ausência
de afastamento médico, não suspensões ou outras regras de escalação.
O atributo Resistência é identificado como atributo, sem apresentá-lo como
condição física atual. Carga, fadiga e risco permanecem sem valor quando não
existem na leitura; não são criadas medições de GPS ou diagnósticos fictícios.

A evolução observada usa a redução do prazo de retorno desde o primeiro
registro. Não é uma medição médica. O histórico começa nesta versão e fica em
`ModCarrerMode/runtime/club_environment/room/runtime/medical_observed_r77_<scope>.json`.
É separado por arquivo da carreira, clube e início da carreira. Recuar a data
reinicia a linha de acompanhamento para não trazer informação do futuro.
Nenhum arquivo do save é alterado. As escritas de acompanhamento são atômicas.

O departamento inclui todos os atletas vinculados, mesmo além dos 35 modelos
da visualização 3D. O tamanho das listas se ajusta para caber em até seis páginas.
A rotação sequencial corrige a omissão de páginas pares/ímpares quando há um
único painel; a convenção dos painéis antigos permanece compatível.

## Integração e validação

As malhas R77 recortam apenas a região médica. Pisos/tetos e materiais das cores
do clube são compartilhados com a sala para reduzir grupos de renderização.
Os sete enquadramentos médicos foram atualizados; as seis vistas do treinador
continuam disponíveis. Móveis/equipamentos têm colisores e a parede antiga do
fundo foi removida, com limite longitudinal nativo ajustado para 2785 cm.

Revisão: `code-release/medical-room-r77-20261101`. Inclui `before-r77.zip`,
instalador e rollback por arquivo, 28 testes Python, testes nativos das duas
salas/câmera/paginação, checagem de buffers e montagens completas de Criciúma e
Flamengo. As prévias são renders offline; validação visual no FIFA pendente.
O rollback dos arquivos não apaga o histórico observado do runtime.
Sem commit nem push.
