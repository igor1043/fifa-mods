# Gramado em alta qualidade e padrões da câmera

Revisão de distribuição: o recurso foi mantido no código, mas ficou oculto no
menu e desativado por padrão a pedido do usuário. `GRASS_QUALITY_AVAILABLE=False`
remove o switch, as chamadas do controlador e a menção na categoria Gráficos.
`high_quality=0` também foi aplicado à instalação local. A descrição abaixo
documenta a implementação guardada para uma eventual reativação.

O menu da camada do Server16 ganhou um switch em **Ajustes da partida →
Gráficos → Gramado em alta qualidade**, abaixo de Física de roupas. A escolha
é salva em `ModCarrerMode/config/grass_quality.ini` e vale para as partidas
seguintes. O padrão é desligado. A ativação é independente da câmera.

O shader nativo da grama usa faixas de detalhe e desaparecimento. Na sessão
observada, o objeto do gramado tinha altura de desaparecimento de 200–400 cm;
as faixas próximas de detalhe alternavam entre 1/100 e 100/250 cm conforme a
câmera, com faixas distantes de 900/1000/1100 cm. A seleção de arquivos em
`data/fifarna/lua/assets/grass.lua` usa os assets do estádio e do patch.
O switch não copia uma textura de replay nem muda o estado de replay.

Quando ligado, o ajuste amplia a faixa de desaparecimento por altura para
80–120 m e promove o detalhe próximo até 4/7 m dentro da distância distante já
configurada pelo estádio. Não aumenta densidade, altura ou quantidade total
de lâminas. O aspecto final depende do gramado instalado e do enquadramento;
o custo de GPU pode aumentar. A comparação visual entre replay e gameplay
com a opção ligada ainda precisa ser feita dentro do jogo.

`grass_quality_runtime.py` valida o executável 577DE45C, o objeto Grass da
partida, sua vtable, índice, dimensões e vínculos antes de alterar quatro
blocos de parâmetros. Não altera instruções, shaders, arquivos do estádio,
physics, DATA ou INDEX. A engine continua controlando o render. Ao desligar,
sair da partida ou fechar o Server16, restaura os bytes originais somente se
o objeto ainda é o mesmo e o valor não foi substituído por outra atualização.
Mudanças nativas de parâmetros são recapturadas; endereços de uma partida
anterior nunca são reutilizados para restauração. Há um controlador por sessão
Windows para evitar dois Servers concorrentes.

Novas configurações da câmera em primeira pessoa agora começam com **130°**
e suavização da cabeça **Extra alta** (nível 2). A terceira pessoa continua
com FOV inicial de 85°. Preferências explícitas já salvas são respeitadas.

Testes cobrem gravação da opção, arquivo inválido, limites de detalhe, troca
de processo/objeto, preservação de mudanças nativas, restauração exata,
navegação do menu e padrões/persistência da câmera. A leitura em RAM e o
ensaio temporário da faixa de desaparecimento estão documentados em
`code-release/camera_defaults_grass_20261030/`; a sessão foi encerrada antes
do ensaio visual completo do novo switch.
