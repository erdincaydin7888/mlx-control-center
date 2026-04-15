"""
Örnek Plugin - Özel Model Loader
=================================

Bu plugin, özel model yükleme mantığı sağlar.
"""

import os
import sys
import time
from typing import Dict, Any, Optional

# Plugin meta bilgileri
__plugin_name__ = "Custom Model Loader"
__version__ = "1.0.0"
__description__ = "Özel model yükleme mantığı sağlar"
__author__ = "Plugin System"
__plugin_path__ = os.path.dirname(os.path.abspath(__file__))


class CustomModelLoader:
    """Özel model loader plugin"""
    
    def __init__(self):
        self.name = __plugin_name__
        self.version = __version__
        self.enabled = True
        self._custom_loaders: Dict[str, Any] = {}
    
    def register_custom_loader(self, model_type: str, loader_func) -> None:
        """Özel loader kaydeder"""
        self._custom_loaders[model_type] = loader_func
        print(f"[CustomModelLoader] Loader kaydedildi: {model_type}")
    
    def load_custom_model(self, model_path: str, model_type: str = "custom") -> Optional[Any]:
        """Özel model yükler"""
        loader = self._custom_loaders.get(model_type)
        if loader:
            return loader(model_path)
        
        # Varsayılan loader
        try:
            import mlx.core as mx
            from mlx_lm import load
            model, tokenizer = load(model_path)
            return {"model": model, "tokenizer": tokenizer}
        except ImportError:
            print(f"[CustomModelLoader] mlx-lm bulunamadı")
            return None
    
    def unload_custom_model(self, model_id: str) -> bool:
        """Özel model boşaltır"""
        if model_id in self._custom_loaders:
            del self._custom_loaders[model_id]
            return True
        return False
    
    def get_info(self) -> Dict[str, Any]:
        """Plugin bilgilerini döner"""
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "custom_loaders_count": len(self._custom_loaders)
        }


# Plugin instance
plugin_instance = CustomModelLoader()


def get_plugin() -> CustomModelLoader:
    """Plugin instance'ını döner"""
    return plugin_instance


def on_load() -> None:
    """Plugin yüklendiğinde çağrılır"""
    print(f"[CustomModelLoader] Plugin yüklendi: {__plugin_name__} v{__version__}")


def on_unload() -> None:
    """Plugin boşaltıldığında çağrılır"""
    print(f"[CustomModelLoader] Plugin boşaltıldı: {__plugin_name__}")
