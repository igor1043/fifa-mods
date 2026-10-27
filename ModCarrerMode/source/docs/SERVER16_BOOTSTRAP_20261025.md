# Extração do Server16 e recuperação dos titulares

O carregador anterior falhou ao reabrir seu próprio EXE para ler uma entrada do pacote. O arquivo mostrado no erro existia e o pacote completo foi descomprimido sem erro no teste de integridade. Não foi estabelecido qual processo ou condição externa impediu a abertura naquela tentativa.

A revisão repete a abertura por no máximo cinco segundos. Também dispensa arquivos de pip, ferramentas de construção e caches da ponte Python x86. Módulos e DLLs necessários permanecem no pacote; todo o conteúdo retido foi comparado byte a byte com o EXE anterior. A ponte x86 foi testada com FifaLibrary16 e a base real do FIFA, sem alterar o banco.

Os fontes canônicos ficam no projeto Server16, branch `fifa-friends`. Esta cópia em `source/` inclui `scripts/build_archive_bootloader.py`, `scripts/repack_bootloader.py`, `scripts/frozen_payload.py`, o cabeçalho em `tools/` e a licença do PyInstaller. O compilador usa a fonte oficial da versão 6.20.0, validada pelo SHA-256 registrado no script. O novo carregador é exigido pelo spec nas próximas compilações.

O navegador de clubes abre o auxiliar somente ao pedir os titulares. O código -1 do carregador recebe até duas novas tentativas; cada reinício reenvia exatamente o clube e a sequência em andamento. O teste cobre também falha permanente, sem repetição infinita. A criação mantém o ambiente congelado independente e a herança restrita de handles.

Verificações desta revisão: três aberturas do EXE, incluindo duas simultâneas; ponte x86; auxiliar congelado completando 11 jogadores do save ativo; dois clubes com 11 jogadores distintos; exportação a frio em caminho com espaços e acentos; fila e chamadas nativas dos placares em processo de teste; cena e câmera em D3D11 WARP. O hash do save lido permaneceu igual. Essas verificações não substituem confirmação visual do novo placar durante uma partida.
