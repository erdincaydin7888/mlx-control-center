"""
Plugin Sistemi - Model Loader
==============================

Bu modül model yükleme/boşaltma işlemlerini yönetir.
Sıcak yükleme (hot-reload) desteği sağlar.
"""

import os
import sys
import importlib.util
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import traceback

from .models import ModelInfo, PluginStatus, PluginConfig
from .events import EventPublisher, EventType


class ModelLoader:
    """Model yükleme/boşaltma yöneticisi"""
    
    def __init__(self, event_publisher: Optional[EventPublisher] = None):
        self.event_publisher = event_publisher or EventPublisher()
        self._models: Dict[str, ModelInfo] = {}
        self._instances: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._loaders: Dict[str, Callable] = {}
        self._config: PluginConfig = PluginConfig(plugin_path="")
    
    def register_loader(self, model_type: str, loader_func: Callable[[str, Dict[str, Any]], Any]) -> None:
        """Belirli bir model türü için loader fonksiyonu kaydeder"""
        with self._lock:
            self._loaders[model_type] = loader_func
    
    def load_model(self, model_path: str, model_name: Optional[str] = None, 
                   model_type: str = "language", config: Optional[Dict[str, Any]] = None) -> Optional[ModelInfo]:
        """Modeli yükler"""
        model_id = self._generate_id(model_path)
        
        with self._lock:
            if model_id in self._models:
                existing = self._models[model_id]
                if existing.loaded:
                    print(f"[ModelLoader] Model zaten yüklenmiş: {model_name or model_path}")
                    return existing
        
        model_info = ModelInfo(
            id=model_id,
            name=model_name or os.path.basename(model_path),
            path=model_path,
            type=model_type,
            status=PluginStatus.LOADING,
            config=config or {}
        )
        
        try:
            # Event: Model loading başlıyor
            self.event_publisher.publish(
                EventType.MODEL_LOADED,
                "ModelLoader",
                {"model_id": model_id, "status": "loading"}
            )
            
            # Loader'ı bul
            loader = self._loaders.get(model_type)
            if not loader:
                loader = self._default_loader
            
            # Modeli yükle
            start_time = time.time()
            instance = loader(model_path, model_info.config)
            load_time = time.time() - start_time
            
            with self._lock:
                model_info.loaded = True
                model_info.loaded_at = datetime.now()
                model_info.status = PluginStatus.ACTIVE
                model_info.metrics["load_time_seconds"] = load_time
                model_info.metrics["status"] = "loaded"
                self._models[model_id] = model_info
                self._instances[model_id] = instance
            
            # Event: Model yüklendi
            self.event_publisher.publish(
                EventType.MODEL_LOADED,
                "ModelLoader",
                {"model_id": model_id, "status": "loaded", "load_time": load_time}
            )
            
            print(f"[ModelLoader] Model yüklendi: {model_info.name} ({load_time:.2f}s)")
            return model_info
            
        except Exception as e:
            with self._lock:
                model_info.status = PluginStatus.ERROR
                model_info.metrics["error"] = str(e)
            
            self.event_publisher.publish(
                EventType.MODEL_UNLOADED,
                "ModelLoader",
                {"model_id": model_id, "status": "error", "error": str(e)}
            )
            
            print(f"[ModelLoader] Model yükleme hatası: {e}")
            traceback.print_exc()
            return None
    
    def unload_model(self, model_id: str) -> bool:
        """Modeli boşaltır"""
        with self._lock:
            if model_id not in self._models:
                return False
            
            model_info = self._models[model_id]
            if not model_info.loaded:
                return False
            
            model_info.status = PluginStatus.UNLOADING
            
            # Event: Model boşaltılıyor
            self.event_publisher.publish(
                EventType.MODEL_UNLOADED,
                "ModelLoader",
                {"model_id": model_id, "status": "unloading"}
            )
            
            # Instance'ı temizle
            if model_id in self._instances:
                del self._instances[model_id]
            
            model_info.loaded = False
            model_info.loaded_at = None
            model_info.status = PluginStatus.INACTIVE
            
            # Event: Model boşaltıldı
            self.event_publisher.publish(
                EventType.MODEL_UNLOADED,
                "ModelLoader",
                {"model_id": model_id, "status": "unloaded"}
            )
            
            print(f"[ModelLoader] Model boşaltıldı: {model_info.name}")
            return True
    
    def reload_model(self, model_id: str) -> Optional[ModelInfo]:
        """Modeli yeniden yükler (hot-reload)"""
        with self._lock:
            if model_id not in self._models:
                return None
            
            model_info = self._models[model_id]
            model_path = model_info.path
            config = model_info.config
            model_type = model_info.type
        
        # Önce boşalt
        self.unload_model(model_id)
        
        # Sonra tekrar yükle
        return self.load_model(model_path, model_info.name, model_type, config)
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Model bilgisini döner"""
        with self._lock:
            return self._models.get(model_id)
    
    def get_instance(self, model_id: str) -> Optional[Any]:
        """Model instance'ını döner"""
        with self._lock:
            return self._instances.get(model_id)
    
    def list_models(self) -> List[ModelInfo]:
        """Tüm modelleri listeler"""
        with self._lock:
            return list(self._models.values())
    
    def get_active_models(self) -> List[ModelInfo]:
        """Aktif modelleri listeler"""
        with self._lock:
            return [m for m in self._models.values() if m.loaded]
    
    def _generate_id(self, model_path: str) -> str:
        """Model ID üretir"""
        return f"model_{hash(model_path)}"
    
    def _default_loader(self, model_path: str, config: Dict[str, Any]) -> Any:
        """Varsayılan model loader - mlx-lm kullanır"""
        try:
            from mlx_lm import load, generate
            model, tokenizer = load(model_path)
            return {"model": model, "tokenizer": tokenizer}
        except ImportError:
            raise ImportError("mlx-lm bulunamadı. 'pip install mlx-lm' ile yükleyin.")
