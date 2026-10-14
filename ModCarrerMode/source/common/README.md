Rotina de carregamento da cena, revisão de 14/10/2026

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
