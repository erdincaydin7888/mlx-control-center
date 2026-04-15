#!/bin/bash

# MLX Otomatik Sunucu Baslatma Scripti
# ====================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/.venv"
PORT="${1:-8045}"
MODEL="${2:-mlx-community/Qwen3-Coder-Next-5bit}"
IDLE_TIMEOUT="${3:-900}"
PRELOAD="${4:-false}"

echo "=========================================="
echo "MLX Otomatik Sunucu - Tam Otomasyonlu"
echo "=========================================="
echo "Port: $PORT"
echo "Model: $MODEL"
echo "Idle Timeout: ${IDLE_TIMEOUT}s (${IDLE_TIMEOUT}/60 dakika)"
echo "Onceden Yukle: $PRELOAD"
echo "=========================================="

# Virtual environment kontrolu
if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment bulunamadi: $VENV_PATH"
    echo "Lutfen once asagidaki komutu calistirin:"
    echo "  cd $SCRIPT_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install mlx-lm uvicorn"
    exit 1
fi

# Virtual environment aktiflestir
source "$VENV_PATH/bin/activate"

# Gerekli bağımlılıkları kontrol et
echo "Bagimliliklar kontrol ediliyor..."
python3 -c "import mlx.core; import mlx_lm; import uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Gerekli paketler yukleniyor..."
    pip install mlx-lm uvicorn
fi

# Environment variable'ları ayarla
export MLX_MODEL_PATH="$MODEL"
export PYTHONUNBUFFERED=1

# Sunucuyu baslat
echo ""
echo "Sunucu baslatiliyor..."
echo "Ping kontrolu ile model otomatik yuklenecek"
echo "Idle timeout sonrasi model RAM'den otomatik silinecek"
echo ""

python3 "$SCRIPT_DIR/mlx_auto_server.py" \
    --port "$PORT" \
    --model "$MODEL" \
    --idle-timeout "$IDLE_TIMEOUT" \
    $( [ "$PRELOAD" = "true" ] && echo "--preload" )

# Temizleme
deactivate 2>/dev/null
