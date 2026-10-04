# Player Career: ano de nascimento 2006–2012

A DLL `birthyear_range_2006_2012.dll` faz parte das duas edições. O payload `payload/vpro_proinfo.big` libera a escolha na interface. O watcher `dist/Fifa16BirthdateWatcher2006.exe` deve ser iniciado antes de criar o jogador para preservar a data no save.

O instalador das edições instala também o payload em `data/ui/game/screens/virtualpro/vpro_proinfo.big`. Ele preserva o original em backup externo antes de substituir esse arquivo. Instalar somente a DLL não garante a interface nem a persistência.

O watcher observa somente DATA novo/alterado após sua inicialização. Mantém a data válida entre 2006 e 2012; fora dessa faixa usa 01/01/2006. Faz backup e valida os CRCs. Confirme a data após fechar e reabrir a carreira; o log fica em `ModCarrerMode/logs/birthdate_watcher_2006.log`.
