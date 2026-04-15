"""
Örnek Plugin - Request Interceptor
===================================

Bu plugin, gelen request'leri filtreler ve değiştirir.
"""

import os
import sys
import json
import time
from typing import Dict, Any, Optional, Callable

# Plugin meta bilgileri
__plugin_name__ = "Request Interceptor"
__version__ = "1.0.0"
__description__ = "Gelen request'leri filtreler ve değiştirir"
__author__ = "Plugin System"
__plugin_path__ = os.path.dirname(os.path.abspath(__file__))


class RequestInterceptor:
    """Request interceptor plugin"""
    
    def __init__(self):
        self.name = __plugin_name__
        self.version = __version__
        self.enabled = True
        self._filters: Dict[str, Callable] = {}
        self._interceptors: Dict[str, Callable] = {}
        self._stats = {
            "total_requests": 0,
            "filtered_requests": 0,
            "intercepted_requests": 0
        }
        self._lock = __import__("threading").RLock()
    
    def register_filter(self, name: str, filter_func: Callable[[Dict[str, Any]], bool]) -> None:
        """Filter kaydeder - True dönerse request kabul edilir"""
        self._filters[name] = filter_func
        print(f"[RequestInterceptor] Filter kaydedildi: {name}")
    
    def register_interceptor(self, name: str, interceptor_func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """Interceptor kaydeder - Request'i değiştirir"""
        self._interceptors[name] = interceptor_func
        print(f"[RequestInterceptor] Interceptor kaydedildi: {name}")
    
    def filter_request(self, request: Dict[str, Any]) -> bool:
        """Request'i filtreler"""
        with self._lock:
            self._stats["total_requests"] += 1
        
        for name, filter_func in self._filters.items():
            try:
                if not filter_func(request):
                    with self._lock:
                        self._stats["filtered_requests"] += 1
                    return False
            except Exception as e:
                print(f"[RequestInterceptor] Filter hatası ({name}): {e}")
        
        return True
    
    def intercept_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Request'i interceptor'larla işler"""
        with self._lock:
            self._stats["total_requests"] += 1
        
        result = request.copy()
        for name, interceptor_func in self._interceptors.items():
            try:
                result = interceptor_func(result)
                with self._lock:
                    self._stats["intercepted_requests"] += 1
            except Exception as e:
                print(f"[RequestInterceptor] Interceptor hatası ({name}): {e}")
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """İstatistikleri döner"""
        with self._lock:
            return self._stats.copy()
    
    def get_info(self) -> Dict[str, Any]:
        """Plugin bilgilerini döner"""
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "filters_count": len(self._filters),
            "interceptors_count": len(self._interceptors),
            "stats": self.get_stats()
        }


# Plugin instance
plugin_instance = RequestInterceptor()


def get_plugin() -> RequestInterceptor:
    """Plugin instance'ını döner"""
    return plugin_instance


def on_load() -> None:
    """Plugin yüklendiğinde çağrılır"""
    print(f"[RequestInterceptor] Plugin yüklendi: {__plugin_name__} v{__version__}")
    
    # Örnek filter - max_tokens kontrolü
    def max_tokens_filter(request: Dict[str, Any]) -> bool:
        max_tokens = request.get("max_tokens", 0)
        return max_tokens <= 8192  # 8192 token üst sınırı
    
    plugin_instance.register_filter("max_tokens_limit", max_tokens_filter)
    
    # Örnek interceptor - default max_tokens ekle
    def add_default_max_tokens(request: Dict[str, Any]) -> Dict[str, Any]:
        if "max_tokens" not in request:
            request["max_tokens"] = 1024
        return request
    
    plugin_instance.register_interceptor("add_defaults", add_default_max_tokens)


def on_unload() -> None:
    """Plugin boşaltıldığında çağrılır"""
    print(f"[RequestInterceptor] Plugin boşaltıldı: {__plugin_name__}")
