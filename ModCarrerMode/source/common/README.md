Rotina de carregamento da cena, revisão de 14/10/2026

Reforço inicial de 15/10/2026: `scene_startup.h` reconhece a apresentação do
estádio pelo estado nativo, relógio em zero e página da partida. Os quatro
módulos fazem uma passagem extra após 500 ms e, somente enquanto pendentes,
até duas novas passagens, separadas por 1 e 2 segundos. A janela termina em
6 segundos ou quando sai da abertura. Pausa e replay não iniciam nem rearmam
o reforço; as regras de visibilidade e de competição continuam valendo.

As passagens revalidam Lua/protótipos atuais e repetem a preparação dos recursos
e vínculos privados antes de reaplicar as posições. Não escrevem em ponteiros
da cena anterior nem criam atores duplicados. A confirmação exige recursos e
vínculo nativo; no mascote, também posição junto ao fundo do campo. Isso não
substitui uma conferência visual da malha no FIFA. Os logs incluem
`startup_reinforcement enabled`, `attempt`, `confirmed` e `timeout`.
`test_scene_startup.cpp` cobre janela, carregamento pendente, sucesso, reinício,
pausa, replay, gameplay, amostragem nativa e preservação de atores comuns.

Entradas v21 e VAR v4 ativam o Lua no callback nativo da cena. Os workers
instalam os hooks; não executam os scripts de apresentação. O canhão v3
compartilha a mesma verificação de contexto e prontidão.

`scene_lua.h` acompanha a VM e a tabela global, verifica os indicadores reais
dos scripts a cada 500 ms e limita novas tentativas a uma por segundo.
Troca de contexto ou perda de indicador invalida o estado privado dos recursos
sem escrever em ponteiros da cena anterior. O booleano Lua é lido pelos seus
32 bits válidos, independentemente dos bytes restantes da união TValue.

As fábricas Lua de VAR e canhão verificam os atores da cena atual. Uma tabela
de cena nova pode criar seus próprios atores; uma tentativa repetida na mesma
tabela não duplica um ator pendente enquanto o RNA ainda não está disponível.
O protótipo privado é atualizado antes de solicitar seus recursos. A entrada
conclui a notificação nativa de carregamento quando todos os cinco LODs estão
prontos, usando a mesma função já empregada pelo VAR/canhão e validando sua
assinatura em memória antes de instalar o hook.

Mascote v30 confirma a conclusão do script e a identidade do protótipo antes
de mover o ator. Uma falha temporária pode tentar novamente com a mesma
geometria/partida. Seus wrappers são instalados uma vez por contexto Lua,
preservando wrappers adicionados posteriormente por outros módulos. O acesso
ao seu estado de cena tem proteção contra reentrada e liberação em `finally`.

Os quatro logs incluem PID e thread e registram a primeira sobreposição ou
reentrada observada. Esse registro sozinho não distingue recursão de chamadas
em threads diferentes. Não foi introduzido bloqueio entre DLLs durante a
execução do renderizador nativo: não há evidência suficiente sobre as esperas
internas do motor para impor essa ordem de bloqueio.

Validação: `common/verify.cmd`, os `build.cmd` de entrance_props/var_cabin/
smoke_machine, `mascot_photographer/verify.cmd` e compilação do mascote com
MSVC x64 `/W4 /WX`. `test_scene_scripts.py` exige `lupa.lua51`; seu argumento
opcional `--lua-python-path` aponta para uma instalação local dessa dependência.
Os testes executam os scripts de produção, incluindo as seis ordens dos três
módulos, RNA atrasado, troca de cena, limite de índices, reativação e falha do
script do mascote. A aparência no FIFA e o comportamento nos PCs afetados
ainda precisam de validação no jogo. A hipótese de concorrência não foi
confirmada por esses testes offline.
# Identidades de competições — 17/10/2026

`competition_identity.h` resolve os objetos do CompData instalado, os ícones por
nome/display e as raízes usadas pelos suportes de bola.
`test_competition_identity.cmd` verifica renumeração, IDs reutilizados e
identidades ambíguas com o mesmo código usado pelas DLLs. Desde 18/10/2026,
as aberturas usam diretamente a pasta com o ID atual, sem conversão ou herança.
