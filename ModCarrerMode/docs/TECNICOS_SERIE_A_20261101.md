# Técnicos 3D da Série A — 01/11/2026

A importação usa os 20 técnicos e os vínculos do `coaches.csv` fornecido em
`MANANGER BR`, com data de referência 26/10/2026. Esses vínculos são configuração
da base entregue, sem consulta ou atualização automática pelo futebol real.
Minifaces, nomes, contratos e saves não são substituídos por esta importação.

| Clube na base | ID | Técnico |
|---|---:|---|
| Athletico-PR | 1039 | Odair Hellmann |
| Atlético-MG | 1035 | Eduardo Domínguez |
| Bahia | 1598 | Rogério Ceni |
| Botafogo | 517 | Tite |
| Chapecoense | 112476 | Rafael Lacerda |
| Corinthians | 1041 | Clarence Seedorf |
| Coritiba | 111044 | Fernando Seabra |
| Cruzeiro | 568 | Artur Jorge |
| Flamengo | 1043 | Leonardo Jardim |
| Fluminense | 567 | Marcão |
| Grêmio | 1629 | Renato Gaúcho |
| Internacional | 1048 | Eduardo Baptista |
| Mirassol | 113163 | Rafael Guanaes |
| Palmeiras | 383 | Abel Ferreira |
| RB Bragantino | 123921 | Vágner Mancini |
| Remo | 130026 | Thiago Carpini |
| Santos | 1053 | Cuca |
| São Paulo | 598 | Dorival Júnior |
| Vasco da Gama | 569 | Pedro Emanuel |
| Vitória | 1719 | Jair Ventura |

## Conversão e revisão

São 15 entradas FBX e cinco RX3. Eduardo Domínguez, Seedorf e Renato Gaúcho
chegaram sem armature; o Odair tinha 15.008 vértices sem pesos; o Abel precisou
de correção de escala de 100 vezes. Os demais FBX tinham um rig de 43 ossos.
O importador adapta os nomes semânticos ao rig nativo de 31 ossos do treinador,
preserva suas matrizes de bind e a paleta ativa de 19 ossos. Juntas adicionais
da coluna, do pescoço e dos dedos são consolidadas nas cadeias suportadas.

`source/mascot_photographer/Build-NativeManagerFromFbx.py` recebe os mesmos
argumentos do conversor OBJ: `--source`, `--profile`, `--reference`, `--tools`,
`--output` e `--club-id`. O arquivo
`source/mascot_photographer/profiles/native_managers_serie_a_20261101.json`
registra os perfis medidos e checksums das fontes. Não se deve aplicar o perfil
de um personagem a outro sem conferir escala, pose, eixos e encaixe da roupa.

Os rigs completos são adaptados pelos pesos autorais. Os ausentes ou parciais
usam transferência de um treinador nativo ajustado à pose de origem. Rogério
Ceni, Renato Gaúcho e Vágner Mancini recebem repintura por distância aos segmentos medidos de
ombro, braço, antebraço e mão (`capsuleArms`). Esse perfil não é aplicado de
forma indiscriminada às mangas largas: nesses casos são usados os pesos
autorais ou transferidos, revisados em poses, para não prender tecido ao tronco.
Todos passam por revisão de cotovelos, punhos e costuras. A revisão da barra
termina antes da axila para não prender a parte interna da manga ao quadril.
Nos RX3 de Fernando Seabra, Artur Jorge, Rafael Guanaes e Thiago Carpini,
antebraços e punhos também são comparados à superfície e aos pesos do Jardim
nativo, que tem o mesmo bind. As regiões revistas não usam pesos do braço oposto.

A revisão da roupa usa um campo contínuo entre quadril, coluna e tórax na
parte inferior da camisa. Isso evita pesos alternados que ondulavam a barra.
Vértices coincidentes das costuras recebem posição e pesos iguais antes do
ajuste para o bind nativo, para a roupa não se abrir ao levantar os braços.
A revisão inclui os modelos de manga longa e os cinco RX3 recebidos.

`Clean-NativeManagerGarment.py` também procura pele que estava escondida sob a
roupa na pose original. Cada face candidata precisa ter cor de pele e quatro
raios saindo para fora da superfície que encontrem a roupa com orientação
consistente. Só então essa geometria interna é retirada; pele exposta nos
braços, rosto e mãos é preservada. No Rogério Ceni isso removeu a camada de
corpo que atravessava a polo. As texturas e os minifaces não recebem pintura
para esconder esses defeitos de geometria.

Nos RX3 recebidos também foram revisadas pequenas peças ligadas à cabeça.
A barba do Rafael Guanaes tinha cartões de malha com peso de pescoço; esses
componentes passam a acompanhar rigidamente a cabeça, preservando seu formato
quando o personagem olha para cima.

As texturas são os mapas 3D fornecidos, nos papéis `cm`, `nm`, `coeff`, com
mipmaps reconstruídos e cabeçalhos duplicados sincronizados. O nome numérico
da pasta de origem identifica a pessoa; não é um ID de clube FIFA. A instalação
usa os IDs de clube da tabela acima, nas variantes `0_0` e `0_1`:

`data/sceneassets/slc/specificmanager_<clube>_0_<variante>{,_textures}.rx3`.

## Mercado de técnicos e isolamento

O mercado grava vínculos em `server16_manager_market.sqlite3`, separado dos
arquivos DATA/INDEX e da base global. A leitura de um vínculo exige o save,
PID, criação do processo, contexto, epoch, clube, data e token de leitura
corretos. Os testes de engine e de perfil verificam restauração, carreiras
distintas e rejeição de publicações de outra sessão.

O código atual **não redireciona o treinador SLC da partida quando o mercado
contrata alguém**. O `GetRMSle` continua resolvendo o técnico pelo clube. As
trocas simuladas não reescrevem esses arquivos nem passam para os amistosos.
O perfil do clube ainda exporta o modelo padrão daquele clube, mesmo quando
os dados do perfil exibem um técnico contratado. Essa limitação já existia e
esta importação de modelos não ativa um hook novo de partida.

`ModCarrerMode/data/manager_market/manager_models.json` relaciona as 20
identidades estáveis `COACH-*` aos pares de modelos aprovados. É um catálogo
de referências, com `runtimeOverrideEnabled=false`; não é um comando para
trocar nomes, minifaces ou atores na carreira.

Não é necessário duplicar a malha para cada clube em que o técnico trabalhar.
Uma futura integração deve resolver a identidade contratada para esse par
fixo de assets, antes do carregamento do ator, e somente com contexto de
carreira confirmado. Não deve copiar o modelo contratado por cima do padrão
do clube. Ausência de modelo completo ou contexto inválido deve usar fallback
definido; uma publicação antiga não deve ser usada em um amistoso.

## Validação e arquivos locais

As verificações incluem formato RX3, buffers, paleta, bind, pares de texturas,
pesos normalizados, cabeça rígida, independência dos braços, costuras e 81
poses de nove clipes por técnico. As prévias e GIFs são produzidos a partir
do RX3 exportado. Esses ensaios offline não confirmam estabilidade ou aparência
em todas as animações do FIFA; o teste em partida permanece necessário.

O estudo, os modelos, o backup anterior, as prévias e os relatórios completos
ficam em `U:/mods/estudos/100_TECNICOS_SERIE_A_20261101/`, fora do código.
O diretório `before/` preserva os arquivos substituídos de cada destino, com
checksums. O manifesto da instalação registra os arquivos novos para permitir
uma restauração exata, inclusive quando antes não existia uma variante.

Não foram feitos commit ou push nesta preparação.
