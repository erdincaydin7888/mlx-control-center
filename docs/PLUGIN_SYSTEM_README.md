# Plugin Sistemi - Mikroservis Mimarisi

Bu dokümantasyon, MLX Proxy ve Server yapısına eklenen plugin sistemini açıklar.

## Mimari Katmanlar

```
┌─────────────────────────────────────────────────────────────┐
│                     Plugin Sistemi                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PluginManager│  │  ModelLoader │  │ EventPublisher│     │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  FileWatcher │  │  PluginAPI   │  │  Registry    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │  WorkerPool  │  │ Connector    │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Özellikler

- **Hot-Reload**: Dosya değişikliklerinde otomatik yeniden yükleme
- **Event-Driven**: Event-based mimari ile gevşek bağlılık
- **REST API**: HTTP API üzerinden plugin yönetimi
- **Worker Pool**: Asenkron görev yönetimi
- **Metrics**: Sistem metriklerini toplama

## Kurulum

```bash
# Gerekli bağımlılıklar
pip install watchdog psutil requests

# Plugin sistemini kullan
python3 mlx_proxy.py 5000
```

## Kullanım

### 1. Basit Kullanım

```python
from plugin_system import PluginManager

# Plugin manager'ı başlat
pm = PluginManager(proxy_port=5000, api_port=8080)

# Plugin yükle
pm.load_plugin("/path/to/plugin")

# API sunucusunu başlat
pm.start_api_server()

# Dosya izleyiciyi başlat
pm.start_watcher()
```

### 2. REST API Kullanımı

```bash
# Tüm plugin'leri listele
curl http://localhost:8080/v1/plugins

# Yeni plugin yükle
curl -X POST http://localhost:8080/v1/plugins \
  -H "Content-Type: application/json" \
  -d '{"plugin_path": "/path/to/plugin"}'

# Plugin bilgilerini al
curl http://localhost:8080/v1/plugins/{plugin_id}

# Model yükle
curl -X POST http://localhost:8080/v1/models \
  -H "Content-Type: application/json" \
  -d '{"model_path": "/path/to/model", "model_name": "my-model"}'

# Sağlık kontrolü
curl http://localhost:8080/v1/health
```

### 3. Hot-Reload

Plugin sistemi otomatik olarak dosya değişikliklerini izler:

```python
from plugin_system import HotReloadManager

# Hot-reload manager'ı başlat
hrm = HotReloadManager(plugin_manager)
hrm.start()
```

## Örnek Plugin'ler

### Custom Model Loader

Özel model yükleme mantığı sağlar.

```python
from plugin_system.examples import CustomModelLoader

plugin = CustomModelLoader()
plugin.register_custom_loader("custom_type", my_loader_func)
```

### Request Interceptor

Gelen request'leri filtreler ve değiştirir.

```python
from plugin_system.examples import RequestInterceptor

plugin = RequestInterceptor()

# Filter ekle
def max_tokens_filter(request):
    return request.get("max_tokens", 0) <= 8192

plugin.register_filter("max_tokens_limit", max_tokens_filter)
```

### Metrics Collector

Sistem metriklerini toplar.

```python
from plugin_system.examples import MetricsCollector

plugin = MetricsCollector()
plugin.start()

# Metrik kaydet
plugin.record_metric("request_latency", 0.5)
plugin.set_gauge("memory_usage_mb", 1024)
```

## API Endpoint'leri

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/plugins` | GET | Tüm plugin'leri listele |
| `/v1/plugins/{id}` | GET | Plugin bilgilerini al |
| `/v1/plugins/{id}/reload` | POST | Plugin'i yeniden yükle |
| `/v1/plugins/{id}/unload` | POST | Plugin'i boşalt |
| `/v1/models` | GET | Tüm modelleri listele |
| `/v1/models/{id}` | GET | Model bilgilerini al |
| `/v1/models/{id}/reload` | POST | Model'i yeniden yükle |
| `/v1/models/{id}/unload` | POST | Model'i boşalt |
| `/v1/health` | GET | Sağlık kontrolü |
| `/v1/events` | GET | Event log |

## Konfigürasyon

```python
from plugin_system import PluginConfig

config = PluginConfig(
    plugin_path="/path/to/plugin",
    enabled=True,
    auto_reload=True,
    watch_interval=5,
    model_config={"max_tokens": 8192},
    environment={"CUDA_VISIBLE_DEVICES": "0"}
)
```

## Event Sistemi

```python
from plugin_system import EventPublisher, EventType

publisher = EventPublisher()

# Event yayını
publisher.publish(
    EventType.PLUGIN_LOADED,
    "source",
    {"plugin_id": "123", "status": "active"}
)

# Event dinleme
publisher.dispatcher.register(
    EventType.PLUGIN_LOADED,
    lambda e: print(f"Plugin yüklendi: {e.payload}")
)
```

## Worker Pool

```python
from plugin_system import WorkerPool

# Worker havuzu başlat
with WorkerPool(num_workers=4) as pool:
    # Görev ekle
    pool.submit("task_name", my_function, arg1, arg2)
    
    # Asenkron görev
    pool.submit_async("async_task", my_async_function)
```

## Proxy Entegrasyonu

```bash
# Plugin sistemi ile proxy başlat
python3 mlx_proxy.py 5000

# Plugin sistemi olmadan proxy başlat
python3 mlx_proxy.py 5000 --no-plugin
```

## Server Entegrasyonu

```bash
# Plugin sistemi ile server başlat
python3 mlx_server_patch.py --model /path/to/model --enable-plugin-system

# API portu: 8081
# Hot-reload: otomatik
```

## Hata Ayıklama

```bash
# Debug logları
export PYTHONPATH=/path/to/mlx:$PYTHONPATH
python3 -m plugin_system.manager

# API logları
curl -v http://localhost:8080/v1/health
```

## Performans Önerileri

1. **Hot-Reload**: Geliştirme sırasında kullanın, production'da kapalı tutun
2. **Worker Pool**: CPU-bound işlemler için uygun
3. **Metrics**: Prodüktivite izlemek için kullanın
4. **Event System**: gevşek bağlılık için kullanın

## Lisans

Bu sistem, MLX Proxy ve Server ile birlikte kullanılmak üzere tasarlanmıştır.
