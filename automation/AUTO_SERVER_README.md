# MLX Otomatik Sunucu - Tam Otomasyonlu Model Yönetimi

## 🚀 Özellikler

- **Otomatik Model Yükleme**: "ping" komutu geldiğinde RAM'e model otomatik yüklenir
- **Otomatik Model Silme**: Belirli bir süre boşta kalırsa model RAM'den silinir
- **IDE Entegrasyonu**: Cursor ve OpenCode'dan doğrudan bağlanabilir
- **Hot-Reload**: Model değiştirme desteği
- **HTTP API**: Basit REST API ile entegrasyon

## 📋 Gereksinimler

- Python 3.10+
- mlx-lm
- uvicorn
- requests (test için)

## 🛠️ Kurulum

```bash
cd /Users/erdinc/Desktop/Mlx

# Virtual environment oluştur
python3 -m venv .venv
source .venv/bin/activate

# Gerekli paketleri yükle
pip install mlx-lm uvicorn requests

# Sunucuyu başlat
./start_auto_mlx.sh 8045 mlx-community/Qwen3-Coder-Next-5bit 900
```

## 📡 API Endpoint'leri

### GET /health
Sunucu sağlığını kontrol et

```bash
curl http://127.0.0.1:8045/health
```

### GET /status
Model durumu ve bilgileri

```bash
curl http://127.0.0.1:8045/status
```

### POST /generate
Ping veya generate isteği

```bash
# Ping - modeli yükle
curl -X POST http://127.0.0.1:8045/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "ping"}'

# Generate - metin üret
curl -X POST http://127.0.0.1:8045/generate \
  -H "Content-Type: application/json" \
  -d '{
    "type": "generate",
    "prompt": "Merhaba nasilsin?",
    "max_tokens": 512
  }'

# Unload - modeli sil
curl -X POST http://127.0.0.1:8045/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "unload"}'
```

## 🔧 IDE Entegrasyonu

### Cursor

Cursor'da `~/.cursor/ai-provider.json` dosyasını oluşturun:

```json
{
  "type": "http",
  "name": "MLX Auto Server",
  "apiBase": "http://127.0.0.1:8045",
  "apiKey": "mlx-auto-server-key",
  "models": [{"id": "mlx-auto", "name": "MLX Otomatik Sunucu"}],
  "headers": {"Content-Type": "application/json"},
  "endpoints": {"chat": "/generate", "status": "/status"},
  "requestFormat": {
    "type": "post",
    "body": {
      "type": "json",
      "content": {
        "type": "ping",
        "prompt": "{{prompt}}",
        "max_tokens": "{{maxTokens}}"
      }
    }
  },
  "responseFormat": {
    "contentPath": "$.response",
    "toolCallsPath": "$.tool_calls"
  },
  "features": {
    "streaming": false,
    "toolCalling": true,
    "imageGeneration": false
  }
}
```

### OpenCode

OpenCode'da `~/.opencode/config.json` dosyasını oluşturun:

```json
{
  "providers": [{
    "id": "mlx-auto",
    "name": "MLX Otomatik Sunucu",
    "type": "openai",
    "apiBase": "http://127.0.0.1:8045/v1",
    "apiKey": "mlx-auto-server-key",
    "models": [{"id": "mlx-auto", "name": "MLX Otomatik Sunucu"}],
    "headers": {"Content-Type": "application/json"}
  }],
  "defaultProvider": "mlx-auto"
}
```

## ⚙️ Konfigürasyon

### Idle Timeout

Varsayılan idle timeout: 900 saniye (15 dakika)

Model 15 dakika boyunca kullanılmazsa otomatik olarak RAM'den silinir.

Timeout'u değiştirmek için:

```bash
./start_auto_mlx.sh 8045 "model-yolu" 1800  # 30 dakika
```

### Önceden Yükleme

Sunucu başlarken modeli önceden yüklemek için:

```bash
./start_auto_mlx.sh 8045 "model-yolu" 900 true
```

## 🧪 Test

```bash
# Test scriptini çalıştır
python3 test_auto_server.py

# Veya manuel test
curl http://127.0.0.1:8045/health
curl http://127.0.0.1:8045/status
```

## 📝 Örnek Kullanım

### Python ile

```python
import requests
import json

BASE_URL = "http://127.0.0.1:8045"

# Modeli yükle
response = requests.post(
    f"{BASE_URL}/generate",
    json={"type": "ping"}
)
print(response.json())

# Metin üret
response = requests.post(
    f"{BASE_URL}/generate",
    json={
        "type": "generate",
        "prompt": "Python'da list comprehension nedir?",
        "max_tokens": 512
    }
)
print(response.json())

# Modeli sil
response = requests.post(
    f"{BASE_URL}/generate",
    json={"type": "unload"}
)
print(response.json())
```

### Bash ile

```bash
# Modeli yükle
curl -X POST http://127.0.0.1:8045/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "ping"}'

# Metin üret
curl -X POST http://127.0.0.1:8045/generate \
  -H "Content-Type: application/json" \
  -d '{
    "type": "generate",
    "prompt": "Merhaba dunya!",
    "max_tokens": 256
  }'
```

## 🐛 Sorun Giderme

### Port zaten kullanılıyor

```bash
# Portu değiştir
./start_auto_mlx.sh 8046 "model-yolu"
```

### Model yüklenemiyor

```bash
# Model yolunu kontrol et
echo $MLX_MODEL_PATH

# Veya manuel yükle
python3 -c "from mlx_lm import load; load('model-yolu')"
```

### Sunucu yanıt vermiyor

```bash
# Logları kontrol et
tail -f /tmp/mlx_auto_server.log

# Sunucuyu yeniden başlat
pkill -f mlx_auto_server.py
./start_auto_mlx.sh 8045 "model-yolu"
```

## 📚 Daha Fazla Bilgi

- [MLX LM Dokümantasyonu](https://github.com/ml-explore/mlx-lm)
- [OpenClaude](https://github.com/openclaude)
- [Cursor](https://cursor.com)
- [OpenCode](https://opencode.ai)

## 📄 Lisans

MIT License
