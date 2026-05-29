#!/bin/bash
# Script de prueba del flujo completo. Requiere una imagen de prueba.
# Uso: ./scripts/test_api.sh <ruta_a_imagen.jpg>

set -e
BASE="http://localhost"
IMAGE=${1:-"test.jpg"}

echo "=== S1: Listar modelos ==="
curl -s "$BASE/models" | python3 -m json.tool

echo ""
echo "=== S2: Enviar fotograma ==="
RESPONSE=$(curl -s -X POST "$BASE/detections" \
  -F "image=@$IMAGE" \
  -F "model_id=yolo11n.pt" \
  -F 'metadata={"lat":-34.6037,"lon":-58.3816,"sensor":"cam_01"}')
echo "$RESPONSE" | python3 -m json.tool

FRAME_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['frameId'])" 2>/dev/null)

if [ -z "$FRAME_ID" ]; then
  echo "ERROR: no se obtuvo frameId"
  exit 1
fi

echo ""
echo "=== S3: Obtener imagen original (frameId=$FRAME_ID) ==="
curl -s -o /tmp/frame_original.jpg "$BASE/frames/$FRAME_ID"
echo "Guardada en /tmp/frame_original.jpg"

echo ""
echo "=== S3: Obtener thumbnail ==="
curl -s -o /tmp/frame_thumb.jpg "$BASE/frames/$FRAME_ID?thumbnail=true"
echo "Guardada en /tmp/frame_thumb.jpg"

echo ""
echo "=== S4: Buscar por ubicación ==="
curl -s "$BASE/frames/search?lat_min=-35&lat_max=-34&lon_min=-59&lon_max=-58" | python3 -m json.tool

echo ""
echo "=== S4: Validación de rangos inválidos ==="
curl -s "$BASE/frames/search?lat_min=-34&lat_max=-35&lon_min=-58&lon_max=-59" | python3 -m json.tool

echo ""
echo "Listo."
