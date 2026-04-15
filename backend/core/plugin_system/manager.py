"""
Plugin Sistemi - Plugin Manager
================================

Bu modül merkezi plugin yönetimini sağlar.
Tüm plugin'leri yükler, yönetir ve event'leri dağıtır.
"""

import os
import sys
import importlib.util
import importlib.metadata
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import traceback

from .models import PluginInfo, ModelInfo, PluginStatus, PluginConfig, HealthCheckResult
from .loader import ModelLoader
from .events import EventPublisher, EventType
from .watcher import FileWatcher
from .api import PluginAPI


class PluginManager:
    """Merkezi plugin yöneticisi"""
    
    def __init__(self, proxy_port: int = 5000, api_port: int = 8080):
        self.proxy_port = proxy_port
        self.api_port = api_port
        
        # Bileşenler
        self.event_publisher = EventPublisher()
        self.model_loader = ModelLoader(self.event_publisher)
        self.file_watcher = FileWatcher()
        self.api_server: Optional[PluginAPI] = None
        
        # Veri yapıları
        self._plugins: Dict[str, PluginInfo] = {}
        self._models: Dict[str, ModelInfo] = {}
        self._plugin_instances: Dict[str, Any] = {}
        self._event_log: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        
        # Konfigürasyon
        self._config: PluginConfig = PluginConfig(plugin_path="")
        
        # Event handler'ları kaydet
        self._setup_event_handlers()
    
    def _setup_event_handlers(self) -> None:
        """Event handler'ları kaydeder"""
        self.event_publisher.dispatcher.register(
            EventType.PLUGIN_LOADED,
            lambda e: self._log_event(e)
        )
        self.event_publisher.dispatcher.register(
            EventType.PLUGIN_UNLOADED,
            lambda e: self._log_event(e)
        )
        self.event_publisher.dispatcher.register(
            EventType.MODEL_LOADED,
            lambda e: self._log_event(e)
        )
        self.event_publisher.dispatcher.register(
            EventType.MODEL_UNLOADED,
            lambda e: self._log_event(e)
        )
    
    def _log_event(self, event) -> None:
        """Event'i loglara ekler"""
        with self._lock:
            self._event_log.append(event.to_dict())
            # Log boyutunu sınırla
            if len(self._event_log) > 1000:
                self._event_log = self._event_log[-1000:]
    
    def get_recent_events(self, count: int = 100) -> List[Dict[str, Any]]:
        """Son event'leri döner"""
        with self._lock:
            return list(self._event_log[-count:])
    
    def load_plugin(self, plugin_path: str, config: Optional[Dict[str, Any]] = None) -> Optional[PluginInfo]:
        """Plugin'i yükler"""
        plugin_id = self._generate_plugin_id(plugin_path)
        
        with self._lock:
            if plugin_id in self._plugins:
                existing = self._plugins[plugin_id]
                if existing.status == PluginStatus.ACTIVE:
                    print(f"[PluginManager] Plugin zaten aktif: {plugin_path}")
                    return existing
        
        # Plugin bilgilerini oku
        plugin_info = self._read_plugin_info(plugin_path)
        if not plugin_info:
            print(f"[PluginManager] Plugin bilgileri okunamadı: {plugin_path}")
            return None
        
        plugin_info.status = PluginStatus.LOADING
        
        try:
            # Event: Plugin loading başlıyor
            self.event_publisher.publish(
                EventType.PLUGIN_LOADED,
                "PluginManager",
                {"plugin_id": plugin_id, "status": "loading"}
            )
            
            # Plugin instance'ını yükle
            instance = self._load_plugin_instance(plugin_path)
            if not instance:
                raise Exception("Plugin instance oluşturulamadı")
            
            # Plugin'i kaydet
            with self._lock:
                plugin_info.status = PluginStatus.ACTIVE
                plugin_info.updated_at = datetime.now()
                self._plugins[plugin_id] = plugin_info
                self._plugin_instances[plugin_id] = instance
            
            # Event: Plugin yüklendi
            self.event_publisher.publish(
                EventType.PLUGIN_LOADED,
                "PluginManager",
                {"plugin_id": plugin_id, "status": "loaded"}
            )
            
            print(f"[PluginManager] Plugin yüklendi: {plugin_info.name}")
            return plugin_info
            
        except Exception as e:
            with self._lock:
                plugin_info.status = PluginStatus.ERROR
                plugin_info.metadata["error"] = str(e)
            
            self.event_publisher.publish(
                EventType.PLUGIN_UNLOADED,
                "PluginManager",
                {"plugin_id": plugin_id, "status": "error", "error": str(e)}
            )
            
            print(f"[PluginManager] Plugin yükleme hatası: {e}")
            traceback.print_exc()
            return None
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """Plugin'i boşaltır"""
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            
            plugin_info = self._plugins[plugin_id]
            plugin_info.status = PluginStatus.UNLOADING
            
            # Event: Plugin boşaltılıyor
            self.event_publisher.publish(
                EventType.PLUGIN_UNLOADED,
                "PluginManager",
                {"plugin_id": plugin_id, "status": "unloading"}
            )
            
            # Plugin instance'ı temizle
            if plugin_id in self._plugin_instances:
                del self._plugin_instances[plugin_id]
            
            # Model'leri de boşalt
            models_to_unload = [
                m for m in self._models.values() 
                if m.id.startswith(plugin_id)
            ]
            for model in models_to_unload:
                self.model_loader.unload_model(model.id)
            
            plugin_info.status = PluginStatus.INACTIVE
            
            # Event: Plugin boşaltıldı
            self.event_publisher.publish(
                EventType.PLUGIN_UNLOADED,
                "PluginManager",
                {"plugin_id": plugin_id, "status": "unloaded"}
            )
            
            print(f"[PluginManager] Plugin boşaltıldı: {plugin_info.name}")
            return True
    
    def reload_plugin(self, plugin_id: str) -> Optional[PluginInfo]:
        """Plugin'i yeniden yükler"""
        with self._lock:
            if plugin_id not in self._plugins:
                return None
            plugin_info = self._plugins[plugin_id]
            plugin_path = plugin_info.entry_point
        
        self.unload_plugin(plugin_id)
        return self.load_plugin(plugin_path)
    
    def load_model(self, model_path: str, model_name: Optional[str] = None,
                   model_type: str = "language", config: Optional[Dict[str, Any]] = None) -> Optional[ModelInfo]:
        """Model yükler"""
        return self.model_loader.load_model(model_path, model_name, model_type, config or {})
    
    def unload_model(self, model_id: str) -> bool:
        """Model boşaltır"""
        return self.model_loader.unload_model(model_id)
    
    def reload_model(self, model_id: str) -> Optional[ModelInfo]:
        """Model yeniden yükler"""
        return self.model_loader.reload_model(model_id)
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInfo]:
        """Plugin bilgisini döner"""
        with self._lock:
            return self._plugins.get(plugin_id)
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Model bilgisini döner"""
        with self._lock:
            return self._models.get(model_id)
    
    def list_plugins(self) -> List[PluginInfo]:
        """Tüm plugin'leri listeler"""
        with self._lock:
            return list(self._plugins.values())
    
    def list_models(self) -> List[ModelInfo]:
        """Tüm modelleri listeler"""
        with self._lock:
            return list(self._models.values())
    
    def get_active_plugins(self) -> List[PluginInfo]:
        """Aktif plugin'leri listeler"""
        with self._lock:
            return [p for p in self._plugins.values() if p.status == PluginStatus.ACTIVE]
    
    def get_active_models(self) -> List[ModelInfo]:
        """Aktif modelleri listeler"""
        with self._lock:
            return [m for m in self._models.values() if m.loaded]
    
    def health_check(self) -> HealthCheckResult:
        """Sistem sağlık kontrolü yapar"""
        active_plugins = self.get_active_plugins()
        active_models = self.get_active_models()
        
        # Hafıza kullanımını kontrol et
        try:
            import psutil
            memory_usage = psutil.Process().memory_info().rss / (1024 * 1024)
        except ImportError:
            memory_usage = 0.0
        
        # Hata kontrolü
        errors = []
        for plugin in self._plugins.values():
            if plugin.status == PluginStatus.ERROR:
                errors.append(f"Plugin {plugin.name}: {plugin.metadata.get('error', 'Bilinmeyen hata')}")
        
        status = "healthy"
        if errors:
            status = "unhealthy"
        elif len(active_plugins) == 0:
            status = "degraded"
        
        return HealthCheckResult(
            status=status,
            plugins_active=len(active_plugins),
            models_loaded=len(active_models),
            memory_usage_mb=memory_usage,
            errors=errors
        )
    
    def start_api_server(self) -> None:
        """API sunucusunu başlatır"""
        if self.api_server:
            self.api_server.start()
    
    def stop_api_server(self) -> None:
        """API sunucusunu durdurur"""
        if self.api_server:
            self.api_server.stop()
    
    def start_watcher(self) -> None:
        """Dosya izleyiciyi başlatır"""
        self.file_watcher.start()
    
    def stop_watcher(self) -> None:
        """Dosya izleyiciyi durdurur"""
        self.file_watcher.stop()
    
    def _generate_plugin_id(self, plugin_path: str) -> str:
        """Plugin ID üretir"""
        return f"plugin_{hash(plugin_path)}"
    
    def _read_plugin_info(self, plugin_path: str) -> Optional[PluginInfo]:
        """Plugin bilgilerini okur"""
        # Varsayılan bilgiler
        plugin_name = os.path.basename(plugin_path)
        
        # __init__.py'den bilgi oku
        init_path = os.path.join(plugin_path, "__init__.py")
        if os.path.exists(init_path):
            try:
                spec = importlib.util.spec_from_file_location("plugin_init", init_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Plugin meta bilgilerini oku
                    name = getattr(module, "__plugin_name__", plugin_name)
                    version = getattr(module, "__version__", "1.0.0")
                    description = getattr(module, "__description__", "")
                    author = getattr(module, "__author__", "")
                    
                    return PluginInfo(
                        id=self._generate_plugin_id(plugin_path),
                        name=name,
                        version=version,
                        description=description,
                        author=author,
                        entry_point=plugin_path,
                        status=PluginStatus.PENDING
                    )
            except Exception as e:
                print(f"[PluginManager] Plugin info okuma hatası: {e}")
        
        # Varsayılan döndür
        return PluginInfo(
            id=self._generate_plugin_id(plugin_path),
            name=plugin_name,
            version="1.0.0",
            description="",
            author="",
            entry_point=plugin_path,
            status=PluginStatus.PENDING
        )
    
    def _load_plugin_instance(self, plugin_path: str) -> Optional[Any]:
        """Plugin instance'ını yükler"""
        init_path = os.path.join(plugin_path, "__init__.py")
        if not os.path.exists(init_path):
            return None
        
        try:
            spec = importlib.util.spec_from_file_location("plugin_module", init_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Plugin instance'ı al
                if hasattr(module, "plugin_instance"):
                    return module.plugin_instance
                elif hasattr(module, "Plugin"):
                    return module.Plugin()
                else:
                    return module
        except Exception as e:
            print(f"[PluginManager] Plugin instance yükleme hatası: {e}")
            traceback.print_exc()
            return None
