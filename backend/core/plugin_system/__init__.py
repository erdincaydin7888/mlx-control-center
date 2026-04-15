"""
Plugin Sistemi - Mikroservis Mimarisi
======================================

Bu modül, MLX Proxy ve Server yapısına eklenecek plugin sistemini sağlar.
Yeni modellerin sıcak yükleme (hot-reload) yapılabileceği mikroservis mimarisi içerir.

Mimari Katmanlar:
- PluginManager: Merkezi plugin yönetimi
- ModelLoader: Model yükleme/boşaltma işlemleri
- EventPublisher: Event-driven plugin tetikleme
- FileWatcher: Dosya değişikliklerini izleme
- PluginAPI: REST API endpoint'leri
- PluginRegistry: Merkezi plugin kaydı
- WorkerPool: Asenkron görev yönetimi
- PluginConnector: Proxy-Servis entegrasyonu
- HotReloadManager: Otomatik yeniden yükleme

Kullanım Örneği:
    from plugin_system import PluginManager, PluginAPI
    
    # Plugin manager'ı başlat
    pm = PluginManager(proxy_port=5000, api_port=8080)
    
    # Plugin yükle
    pm.load_plugin("/path/to/plugin")
    
    # API sunucusunu başlat
    pm.start_api_server()
    
    # Dosya izleyiciyi başlat
    pm.start_watcher()
"""

from .models import (
    PluginInfo,
    ModelInfo,
    Event,
    HealthCheckResult,
    PluginConfig,
    PluginStatus,
    EventType
)

from .events import EventDispatcher, EventPublisher

from .loader import ModelLoader

from .watcher import FileWatcher

from .api import PluginAPI, PluginAPIHandler, APIResponse

from .manager import PluginManager

from .registry import PluginRegistry, RegistryEntry

from .worker import WorkerPool, WorkerThread, WorkerTask

from .connector import PluginConnector, HotReloadManager, ProxyConfig

__all__ = [
    # Veri Modelleri
    'PluginInfo',
    'ModelInfo',
    'Event',
    'HealthCheckResult',
    'PluginConfig',
    'PluginStatus',
    'EventType',
    
    # Event Sistemi
    'EventDispatcher',
    'EventPublisher',
    
    # Loader
    'ModelLoader',
    
    # Watcher
    'FileWatcher',
    
    # API
    'PluginAPI',
    'PluginAPIHandler',
    'APIResponse',
    
    # Manager
    'PluginManager',
    
    # Registry
    'PluginRegistry',
    'RegistryEntry',
    
    # Worker
    'WorkerPool',
    'WorkerThread',
    'WorkerTask',
    
    # Connector
    'PluginConnector',
    'HotReloadManager',
    'ProxyConfig',
]

__version__ = "1.0.0"
__author__ = "Mlx Plugin System"
__description__ = "MLX Proxy ve Server için mikroservis mimarisi plugin sistemi"
