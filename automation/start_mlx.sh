#!/bin/bash

# MLX Server Başlatıcı Scripti
# Apple MLX kütüphanesini başlatır

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/.venv"
PORT="${1:-8080}"
MODEL="${2:-mlx-community/Qwen3-Coder-Next-5bit}"

echo "🍎 MLX Server Başlatılıyor..."
echo "📍 Port: $PORT"
echo "🤖 Model: $MODEL (6bit)"

# Virtual environment kontrolü
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment bulunamadı: $VENV_PATH"
    echo "   Önce 'python3 -m venv .venv' ile oluşturun"
    exit 1
fi

# Virtual environment aktifleştir
source "$VENV_PATH/bin/activate"

# MLX LM server başlat
mlx_lm.server \
    --model "$MODEL" \
    --port "$PORT" \
    --host 0.0.0.0

deactivate
