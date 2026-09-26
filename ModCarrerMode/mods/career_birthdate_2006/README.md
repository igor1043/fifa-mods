# Data de nascimento no modo Carreira Jogador

O pacote de execução contém duas partes instaladas por cópia para a raiz do
FIFA 16: `data/ui/game/screens/virtualpro/vpro_proinfo.big` libera o campo e
mostra os anos 2006–2012; `birthyear_range_2006_2012.dll` é carregada pela
linha correspondente em `../enabled.txt` e altera a faixa nativa neste build.

Essas duas partes **não garantem sozinhas** que a data persistirá no save. O
observador em `../../tools/career_birthdate_2006/watch_birthdate_2006.py`
trata saves novos/alterados. Ele importa `birthdate_editor.py`, usa Python 3,
faz backup antes de gravar e precisa ser iniciado separadamente antes da
criação da carreira. O executável empacotado mencionado em estudos anteriores
não está presente na instalação analisada; por isso o repositório inclui os
dois scripts, não promete inicialização automática ao abrir o FIFA.

Para acompanhar a gravação, execute o script com Python 3 e confira o evento
`patched` em `ModCarrerMode/tools/career_birthdate_2006/logs/` e a data após
reabrir a carreira. A DLL é específica do executável analisado; uma assinatura
desconhecida faz o plugin recusar a alteração.
