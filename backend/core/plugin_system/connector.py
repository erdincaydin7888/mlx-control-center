"""
Plugin Sistemi - Proxy-Servis Entegrasyonu
===========================================

Bu modül plugin sisteminin mlx_proxy ve mlx_server ile entegrasyonunu sağlar.
"""

import os
import sys
import json
import http.client
import threading
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .models import PluginInfo, ModelInfo, PluginStatus
from .manager import PluginManager
from .loader import ModelLoader


@dataclass
class ProxyConfig:
    """Proxy yapılandırması"""
    proxy_port: int
    server_port: int
    plugin_port: int
    enabled: bool = True


class PluginConnector:
    """Plugin connector - Proxy ve Server ile entegrasyon"""
    
    def __init__(self, plugin_manager: PluginManager, proxy_port: int = 5000):
        self.plugin_manager = plugin_manager
        self.proxy_port = proxy_port
        self.server_port = proxy_port + 10
        self._config = ProxyConfig(
            proxy_port=proxy_port,
            server_port=self.server_port,
            plugin_port=8080
        )
        self._running = False
        self._lock = threading.RLock()
    
    def start(self) -> None:
        """Connector'ı başlatır"""
        self._running = True
        print(f"[PluginConnector] Başlatıldı - Proxy:{self.proxy_port}, Server:{self.server_port}")
    
    def stop(self) -> None:
        """Connector'ı durdurur"""
        self._running = False
        print("[PluginConnector] Durduruldu")
    
    def get_server_address(self) -> str:
        """Server adresini döner"""
        return f"localhost:{self.server_port}"
    
    def forward_request(self, path: str, method: str = "GET", 
                       headers: Dict[str, str] = None, 
                       body: bytes = None) -> Optional[http.client.HTTPResponse]:
        """Request'i server'a yönlendirir"""
        try:
            conn = http.client.HTTPConnection("localhost", self.server_port, timeout=60)
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            return response
        except Exception as e:
            print(f"[PluginConnector] Forward hatası: {e}")
            return None
        finally:
            try:
                conn.close()
            except:
                pass
    
    def check_server_health(self) -> bool:
        """Server sağlık kontrolü"""
        try:
            conn = http.client.HTTPConnection("localhost", self.server_port, timeout=5)
            conn.request("GET", "/health")
            response = conn.getresponse()
            return response.status == 200
        except:
            return False
        finally:
            try:
                conn.close()
            except:
                pass
    
    def get_active_models_from_server(self) -> List[Dict[str, Any]]:
        """Server'dan aktif modelleri çeker"""
        response = self.forward_request("/v1/models")
        if response and response.status == 200:
            try:
                data = json.loads(response.read().decode())
                return data.get("data", [])
            except:
                return []
        return []
    
    def load_model_on_server(self, model_path: str, model_name: str = None) -> bool:
        """Server'a model yükletir"""
        payload = {
            "model_path": model_path,
            "model_name": model_name or os.path.basename(model_path)
        }
        
        try:
            conn = http.client.HTTPConnection("localhost", self.server_port, timeout=60)
            conn.request("POST", "/v1/models", 
                        body=json.dumps(payload).encode(),
                        headers={"Content-Type": "application/json"})
            response = conn.getresponse()
            return response.status == 200
        except Exception as e:
            print(f"[PluginConnector] Model yükleme hatası: {e}")
            return False
        finally:
            try:
                conn.close()
            except:
                pass
    
    def unload_model_on_server(self, model_id: str) -> bool:
        """Server'dan model boşaltır"""
        try:
            conn = http.client.HTTPConnection("localhost", self.server_port, timeout=60)
            conn.request("DELETE", f"/v1/models/{model_id}")
            response = conn.getresponse()
            return response.status == 200
        except Exception as e:
            print(f"[PluginConnector] Model boşaltma hatası: {e}")
            return False
        finally:
            try:
                conn.close()
            except:
                pass
    
    def sync_with_server(self) -> None:
        """Server ile senkronize olur"""
        if not self.check_server_health():
            print("[PluginConnector] Server sağlık kontrolü başarısız")
            return
        
        # Server'daki modelleri al
        server_models = self.get_active_models_from_server()
        
        # Local plugin manager'daki modelleri güncelle
        with self._lock:
            for server_model in server_models:
                model_id = server_model.get("id")
                if model_id and model_id not in self.plugin_manager._models:
                    # Local'e ekle
                    model_info = ModelInfo(
                        id=model_id,
                        name=server_model.get("name", model_id),
                        path=server_model.get("path", ""),
                        type=server_model.get("type", "language"),
                        status=PluginStatus.ACTIVE,
                        loaded=True
                    )
                    self.plugin_manager._models[model_id] = model_info
        
        print(f"[PluginConnector] Senkronizasyon tamamlandı - {len(server_models)} model")


class HotReloadManager:
    """Hot-reload yöneticisi"""
    
    def __init__(self, plugin_manager: PluginManager, check_interval: int = 5):
        self.plugin_manager = plugin_manager
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_mtime: Dict[str, float] = {}
    
    def start(self) -> None:
        """Hot-reload kontrolünü başlatır"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()
        print(f"[HotReloadManager] Başlatıldı - {self.check_interval}s kontrol aralığı")
    
    def stop(self) -> None:
        """Hot-reload kontrolünü durdurur"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[HotReloadManager] Durduruldu")
    
    def _check_loop(self) -> None:
        """Döngüsel kontrol"""
        while self._running:
            try:
                self._check_plugins()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"[HotReloadManager] Kontrol hatası: {e}")
    
    def _check_plugins(self) -> None:
        """Plugin dosyalarını kontrol eder"""
        for plugin in self.plugin_manager.list_plugins():
            if plugin.status != PluginStatus.ACTIVE:
                continue
            
            init_path = os.path.join(plugin.entry_point, "__init__.py")
            if not os.path.exists(init_path):
                continue
            
            try:
                current_mtime = os.path.getmtime(init_path)
                last_mtime = self._last_mtime.get(plugin.id, 0)
                
                if current_mtime > last_mtime:
                    print(f"[HotReloadManager] Değişiklik tespit edildi: {plugin.name}")
                    self._last_mtime[plugin.id] = current_mtime
                    self.plugin_manager.reload_plugin(plugin.id)
                else:
                    self._last_mtime[plugin.id] = current_mtime
            except Exception as e:
                print(f"[HotReloadManager] Mtime kontrol hatası: {e}")
    
    def register_plugin(self, plugin_id: str) -> None:
        """Plugin'i izlemeye alır"""
        plugin = self.plugin_manager.get_plugin(plugin_id)
        if plugin:
            init_path = os.path.join(plugin.entry_point, "__init__.py")
            if os.path.exists(init_path):
                self._last_mtime[plugin_id] = os.path.getmtime(init_path)
    
    def unregister_plugin(self, plugin_id: str) -> None:
        """Plugin'i izlemeden çıkarır"""
        if plugin_id in self._last_mtime:
            del self._last_mtime[plugin_id]
