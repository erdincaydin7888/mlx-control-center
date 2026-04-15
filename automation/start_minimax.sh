#!/bin/bash

# MiniMax-M2.7 MLX Server Başlatıcı
# Model yolu: /Users/erdinc/.lmstudio/models/baa-ai/MiniMax-M2.7-RAM-90GB-MLX

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="\$SCRIPT_DIR/.venv"
PORT="\${1:-8000}"
MODEL_PATH="/Users/erdinc/.lmstudio/models/baa-ai/MiniMax-M2.7-RAM-90GB-MLX"

echo "🍎 MiniMax-M2.7 MLX Server Başlatılıyor..."
echo "📍 Port: \$PORT"
echo "🤖 Model: \$MODEL_PATH"
echo "⚠️  Not: Model 90GB boyutundadır, yüklenmesi birkaç dakika sürebilir."

if [ ! -d "\$VENV_PATH" ]; then
    echo "❌ Virtual environment bulunamadı: \$VENV_PATH"
    exit 1
fi

source "\$VENV_PATH/bin/activate"

# MLX LM server başlat
# trust-remote-code ekleniyor çünkü minimax özel bir mimari kullanıyor
python3 -m mlx_lm.server \
    --model "\$MODEL_PATH" \
    --port "\$PORT" \
    --host 0.0.0.0 \
    --trust-remote-code

deactivate
