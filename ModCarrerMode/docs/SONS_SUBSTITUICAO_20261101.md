# Pacote de notificações de substituição

15 MP3s recebidos em “Sons de Notificações”, identificados pelo ID dos clubes
no catálogo do patch e instalados em `FSW/Substitutions/<ID>.mp3` nas pastas do
jogo e do desenvolvimento. A pasta recebida não foi alterada. O áudio anterior
do Flamengo foi preservado no backup.

Volume padrão reduzido de 35% para 20%. O Server16 ganhou uma aba “Som de
substituição” em Áudio → Editar chants. Controle de 0–100%, ativação e gravação
automática. A alteração do volume também afeta uma reprodução em andamento.
O recurso mantém sua configuração independente dos cânticos.

Validação: IDs consultados no catálogo SQLite do patch em modo somente leitura;
os 15 MP3s abriram no decodificador do Windows e tiveram duração válida, sem
reprodução durante essa conferência. 25 testes automatizados passaram; teste
do formulário oculto confirmou slider, persistência, ativação e salvamento ao
fechar. O autoteste do novo executável congelado passou, incluindo o módulo
da nova aba. Os arquivos instalados foram comparados com o desenvolvimento.

Backup: `code-release/substitution-sounds-20261101/before`.
Mapeamento e hashes: `code-release/substitution-sounds-20261101/installed-audio-map.json`.
Sem alterações de save ou banco. Sem commit nem push.

Regra final: somente substituições do mandante geram o som. O visitante é
ignorado mesmo que possua MP3, incluindo Flamengo como visitante. Os dois
cenários estão cobertos pelos testes.
