#!/bin/bash

# Plugin Sistemi ile MLX Server Başlatma Scripti
# ===============================================

# Varsayılan model
MODEL=${1:-""}
PORT=${2:-8080}

echo "=========================================="
echo "MLX Server - Plugin Sistemi ile Başlatılıyor"
echo "=========================================="
echo "Model: $MODEL"
echo "Port: $PORT"
echo "API Port: 8081"
echo "=========================================="

# Python environment kontrolü
if [ -d ".venv" ]; then
    echo "Virtual environment bulundu, aktif ediliyor..."
    source .venv/bin/activate
fi

# Gerekli bağımlılıkları kontrol et
echo "Bağımlılıklar kontrol ediliyor..."
python3 -c "import plugin_system" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Plugin sistemi bulunamadı, yükleniyor..."
    pip install -r requirements.txt
fi

# Server'ı başlat
echo ""
echo "Server başlatılıyor..."
python3 mlx_server_patch.py \
    --model "$MODEL" \
    --port $PORT \
    --enable-plugin-system

# Temizleme
deactivate 2>/dev/null
