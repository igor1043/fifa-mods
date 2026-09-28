# Player Career — faixa 2006–2012

Esta variante combina três partes diferentes:

1. `payload\vpro_proinfo.big` altera a tela APT: a linha de ano é editável e a lista contém 2006–2012.
2. `birthyear_range_2006_2012.dll` altera, na imagem desembrulhada do FIFA 16, a faixa nativa do atributo 7 e o ano inicial. É específico para o build identificado; se a assinatura não coincidir, não escreve.
3. `dist\Fifa16BirthdateWatcher2006.exe` observa somente DATA novo ou alterado depois de iniciado. Quando encontra `career_playasplayer` + `players`, preserva a data escolhida se o ano estiver entre 2006 e 2012; se o jogo gravar um ano fora da faixa, usa `2006-01-01`. Em ambos os casos ajusta `startingage`, mantém `isretiring=0`, faz backup e valida os CRCs.

## Teste real

1. Feche o FIFA antes de instalar os arquivos de interface/plugin.
2. Execute `install_2006.ps1` nesta pasta. Ele recusa hashes desconhecidos e cria uma pasta em `rollback\`.
3. Inicie o `Fifa16BirthdateWatcher2006.exe` antes de criar o jogador.
4. Crie o Player Career, confirme a data na tela e clique em **Pronto**.
5. Aguarde o evento `patched` em `logs\birthdate_watcher_2006.log`.
6. Feche e reabra a carreira. A confirmação concreta é `requestedDate=YYYY-MM-DD` no log, dentro de 2006–2012, e a leitura da mesma data no jogo após recarregar.

O watcher ignora DATA que já existia quando foi iniciado, para não alterar carreiras antigas por acidente. O teste temporário `live_patch_birthyear_2026.py` é diferente: ele só muda três bytes na RAM e desaparece ao reiniciar o FIFA; não é a solução persistente.

## Limitações conhecidas

- A DLL e os RVAs são exclusivos do executável/build analisado.
- `01/01/2006` é apenas o fallback para um ano fora da faixa; uma data escolhida válida é preservada, inclusive mês/dia.
- A camada que garante a persistência é o patch validado do DATA. A APT/DLL liberam a entrada, mas não são consideradas prova de save sem o evento `patched` e o recarregamento.

## Reversão

Com o FIFA fechado, execute `rollback_2006.ps1 -RollbackDirectory <pasta criada em rollback>`.
