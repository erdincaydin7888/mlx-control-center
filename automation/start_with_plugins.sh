#!/bin/bash

# Plugin Sistemi ile MLX Proxy Başlatma Scripti
# ==============================================

# Varsayılan port
PORT=${1:-5000}

echo "=========================================="
echo "MLX Proxy - Plugin Sistemi ile Başlatılıyor"
echo "=========================================="
echo "Port: $PORT"
echo "API Port: 8080"
echo "Server Port: $((PORT + 10))"
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

# Proxy'yi başlat
echo ""
echo "Proxy başlatılıyor..."
python3 mlx_proxy.py $PORT

# Temizleme
deactivate 2>/dev/null
