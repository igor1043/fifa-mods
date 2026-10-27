# Bancada de cenas — 26/10/2026

Extraia **FIFA-Friends-Bancada-Cenas-IA-20261026.zip** em uma pasta própria,
fora da pasta do FIFA. Abra **Abrir bancada.cmd**. O pacote contém Python 3.13
x64, dependências, biblioteca dos onze jogadores e os dois modelos ONNX.
Não precisa instalar Python, Blender ou CUDA para usar o editor e a IA.
O navegador abre apenas o servidor local (127.0.0.1).

Para **Exportar RX3**, execute **Configurar FIFA.cmd** e escolha sua pasta do
FIFA 16. Ela é usada somente para ler os modelos base do formato nativo. O ZIP
exportado fica na bancada; não é instalado automaticamente no jogo.
Salvar/abrir cenas JSON e importar imagens não exigem configurar o FIFA.

A IA local detecta uma ou várias pessoas, estima 133 pontos e transfere as
poses para os esqueletos editáveis. O primeiro uso carrega os modelos; os
seguintes reutilizam o processo por até 90 segundos sem atividade. A velocidade
depende do computador. A GPU é escolhida no início; CPU serve como alternativa.
Uma foto estima profundidade e partes ocultas: revise a pose com IK/FK.

Ctrl+Z desfaz; Ctrl+X refaz. Punhos e pés têm IK de dois ossos. As cenas são
poses estáticas; a exportação não cria uma animação ou cutscene nativa completa.
Consulte README-editor.md para os controles e local_ai/README.md para a IA.

Os fontes estão na branch fifa-friends-v12, em
ModCarrerMode/source/scene_studio. Modelos, pesos ONNX e runtime portátil ficam
neste ZIP. Dados importados, saves e rascunhos pessoais não foram incluídos.
