# Captura de poses por imagem — IA local

O editor usa YOLOX-M HumanArt para localizar pessoas e **RTMW3D-X** para estimar
133 pontos COCO-WholeBody por pessoa (corpo, pés, face e mãos). São modelos de
inferência ONNX, executados em um processo próprio. As dependências ficam em
`local_ai/vendor`, separadas do Python global e do FIFA. O modelo de poses usa
DirectML na GPU disponível e pode usar CPU; o detector usa CPU com quatro threads.
Nesta máquina, o adaptador selecionado é a RTX 3060. Não precisa instalar CUDA.

Os pesos publicados foram obtidos das URLs indicadas pelo projeto rtmlib. O
arquivo `models/manifest.json` registra URLs, tamanhos e hashes SHA-256. O código
do rtmlib conserva sua licença Apache-2.0 no wheel e nos metadados de `vendor`.
ONNX Runtime conserva sua licença MIT e os avisos distribuídos no pacote.

- Biblioteca e exemplo 3D: https://github.com/Tau-J/rtmlib
- Arquitetura e modelos: https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose3d
- Modelo ONNX usado pelo exemplo oficial da biblioteca: https://huggingface.co/Soykaf/RTMW3D-x
- Execução DirectML: https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html

`setup_models.py` baixa os dois modelos uma vez; cerca de 464 MB de downloads.
Nenhum download ou acesso à internet acontece na análise de uma imagem. Não há
envio de imagem, esqueleto ou save para uma API externa. O servidor aceita apenas
arquivos enviados ao endereço local, nunca uma URL de imagem fornecida pelo cliente.

As imagens normalizadas e capturas ficam em `imports/<id>/`, fora do jogo.
Os modelos ocupam GPU/RAM somente durante a análise e por até 90 segundos de
inatividade, para permitir várias tentativas rápidas. A primeira análise precisa
carregar os modelos; as seguintes reutilizam o processo. Há uma análise por vez,
limite de 48 pessoas, 15 MB por imagem, 24 megapixels e 240 segundos por trabalho.
Imagens são corrigidas pela orientação EXIF, convertidas para RGB e reduzidas a
no máximo 3072 pixels no maior lado. Recortes manuais usam essa imagem normalizada.

## Limites da reconstrução

Os pontos 2D são estimados na foto. A profundidade vem do RTMW3D; X/Y são colocados
em uma escala corporal aproximada, com origem no centro do quadril. Essa captura
não fornece medidas ou posições absolutas da câmera. O mapeamento preserva o
tamanho dos membros dos jogadores do FIFA, em vez de deformá-los para encaixar
os pixels. Contato com colegas, colisões, dedos ocultos e roupas não são
reconstruídos. Confiança do modelo não é garantia de uma articulação correta.

O mapa permite corrigir pontos na imagem e controlar a força da profundidade.
Depois da transferência, o esqueleto nativo completo continua editável com FK,
IK e os controles existentes. Uma foto gera uma pose estática, não uma animação.

## Reproduzir os testes

```text
python -B local_ai/test_reference.py
node --experimental-default-type=module test_pose_capture.mjs
node --experimental-default-type=module --experimental-loader ./node_loader.mjs test_pose_retarget.mjs
python -B local_ai/test_cases.py
python -B -m unittest test_pose_service -v
```

Os testes usam a imagem de referência do próprio estudo, recorte individual,
recorte manual e imagem vazia. Resultados ficam em `build/tests/`; os renderizados
do Blender são apenas inspeção offline. Nenhum desses testes modifica o FIFA.
