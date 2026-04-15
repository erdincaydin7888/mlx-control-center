# MLX Tam Otomasyonlu Sunucu - Özet

## ✅ Tamamlanan İşlemler

### 1. Otomatik MLX Sunucusu (mlx_auto_server.py)
- **Ping kontrolü**: Sunucuya "ping" geldiğinde model otomatik yüklenir
- **Idle timeout**: 15 dakika (varsayılan) boşta kalırsa model RAM'den silinir
- **HTTP API**: /health, /status, /generate endpoint'leri
- **Thread-safe**: Aynı anda tek istek işleyebilir (Metal/MLX kısıtlaması)

### 2. IDE Entegrasyonları

#### Cursor
- Dosya: `~/.cursor/ai-provider.json`
- Port: 8045
- Model: mlx-community/Qwen3-Coder-Next-5bit

#### OpenCode
- Dosya: `~/.opencode/config.json`
- Port: 8045
- Model: mlx-auto

#### OpenClaude
- Ayarlar: `~/.claude/settings.json` güncellendi
- Provider: `~/.claude/providers/mlx-auto.json`

### 3. Start Script'i (start_auto_mlx.sh)
```bash
./start_auto_mlx.sh [port] [model] [idle_timeout] [preload]
```

Örnek kullanım:
```bash
# Varsayılan ayarlarla başlat
./start_auto_mlx.sh

# Özelleştirilmiş başlatma
./start_auto_mlx.sh 8045 "mlx-community/Qwen3-Coder-Next-5bit" 900
```

### 4. Test Script'i (test_auto_server.py)
```bash
python3 test_auto_server.py
```

### 5. Dökümantasyon
- `AUTO_SERVER_README.md`: Detaylı kullanım kılavuzu
- `OTOMASYON_OZETI.md`: Bu özet

## 🚀 Kullanım

### Sunucuyu Başlatma
```bash
cd /Users/erdinc/Desktop/Mlx
./start_auto_mlx.sh 8045 "mlx-community/Qwen3-Coder-Next-5bit" 900
```

### Ping Gönderme (Modeli Yükle)
```bash
curl -X POST http://127.0.0.1:8045/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "ping"}'
```

### Metin Üretme
```bash
curl -X POST http://127.0.0.1:8045/generate \
  -H "Content-Type: application/json" \
  -d '{
    "type": "generate",
    "prompt": "Merhaba nasilsin?",
    "max_tokens": 512
  }'
```

### Modeli Silme
```bash
curl -X POST http://127.0.0.1:8045/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "unload"}'
```

## 📊 Sistem Akışı

```
IDE (Cursor/OpenCode)
        ↓
    HTTP POST /generate
        ↓
  Sunucu "ping" alır
        ↓
  Model RAM'e yüklenir
        ↓
  İstek işlenir
        ↓
  Yanıt döner
        ↓
  Idle timeout başlar (15 dk)
        ↓
  Sonraki ping'de model zaten yüklenmiş
        ↓
  Idle timeout sona ererse → Model RAM'den silinir
```

## ⚙️ Konfigürasyon Seçenekleri

| Seçenek | Varsayılan | Açıklama |
|---------|------------|----------|
| port | 8045 | Sunucu portu |
| model | Qwen3-Coder-Next-5bit | MLX model yolu |
| idle_timeout | 900 | Idle timeout (saniye) |
| preload | false | Sunucu başlarken modeli yükle |

## 🧪 Test Edilmesi Gerekenler

1. **Sunucu Başlatma**
   ```bash
   ./start_auto_mlx.sh 8045
   ```

2. **Health Check**
   ```bash
   curl http://127.0.0.1:8045/health
   ```

3. **Ping Testi**
   ```bash
   curl -X POST http://127.0.0.1:8045/generate \
     -H "Content-Type: application/json" \
     -d '{"type": "ping"}'
   ```

4. **Generate Testi**
   ```bash
   curl -X POST http://127.0.0.1:8045/generate \
     -H "Content-Type: application/json" \
     -d '{
       "type": "generate",
       "prompt": "Test",
       "max_tokens": 100
     }'
   ```

5. **IDE Entegrasyonu**
   - Cursor/OpenCode'da provider olarak ekleyin
   - Bir komut gönderin
   - Modelin otomatik yüklendiğini kontrol edin

## 📝 Notlar

- Model RAM'e yüklendiğinde ~2-5 GB RAM kullanır (model boyutuna göre)
- Idle timeout sonunda model RAM'den silinir
- Sonraki ping'de model tekrar yüklenir
- Birden fazla istek aynı anda gelirse sırayla işlenir (Metal kısıtlaması)

## 🐛 Bilinen Sorunlar

- İlk yükleme biraz zaman alabilir (model cache oluşturulur)
- Idle timeout kısa tutulursa model sürekli yüklenir/silinir (performans etkilenir)

## 📚 Daha Fazla Bilgi

- `AUTO_SERVER_README.md`: Detaylı kullanım kılavuzu
- `mlx_auto_server.py`: Kaynak kod
- `test_auto_server.py`: Test scripti
