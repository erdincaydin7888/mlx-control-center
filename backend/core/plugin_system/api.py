"""
Plugin Sistemi - REST API
=========================

Bu modül plugin yönetimini için REST API endpoint'leri sağlar.
"""

import json
import http.server
import socketserver
import urllib.parse
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .models import PluginInfo, ModelInfo, PluginStatus, HealthCheckResult
from .loader import ModelLoader
from .events import EventPublisher, EventType


@dataclass
class APIResponse:
    """API yanıt yapısı"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "timestamp": self.timestamp.isoformat()
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
        return result
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class PluginAPIHandler(http.server.BaseHTTPRequestHandler):
    """Plugin API HTTP handler"""
    
    def __init__(self, plugin_manager: 'PluginManager', *args, **kwargs):
        self.plugin_manager = plugin_manager
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Log mesajlarını sessize al"""
        return
    
    def _send_json_response(self, response: APIResponse, status_code: int = 200) -> None:
        """JSON yanıt gönderir"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response.to_json().encode())
    
    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        """JSON body'yi okur"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return {}
            body = self.rfile.read(content_length)
            return json.loads(body.decode())
        except Exception as e:
            self.send_error(400, f"Invalid JSON: {e}")
            return None
    
    def do_OPTIONS(self) -> None:
        """CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self) -> None:
        """GET isteklerini işler"""
        parsed_path = urllib.parse.urlparse(self.path)
        path_parts = parsed_path.path.split('/')
        
        # /v1/plugins - Tüm plugin'leri listele
        if path_parts[-1] == "plugins" and len(path_parts) == 3:
            plugins = self.plugin_manager.list_plugins()
            response = APIResponse(
                success=True,
                data=[p.to_dict() for p in plugins]
            )
            self._send_json_response(response)
        
        # /v1/plugins/{id} - Belirli plugin'i al
        elif len(path_parts) == 4 and path_parts[-2] == "plugins":
            plugin_id = path_parts[-1]
            plugin = self.plugin_manager.get_plugin(plugin_id)
            if plugin:
                response = APIResponse(success=True, data=plugin.to_dict())
            else:
                response = APIResponse(success=False, error="Plugin bulunamadı")
            self._send_json_response(response)
        
        # /v1/models - Tüm modelleri listele
        elif path_parts[-1] == "models" and len(path_parts) == 3:
            models = self.plugin_manager.list_models()
            response = APIResponse(
                success=True,
                data=[m.to_dict() for m in models]
            )
            self._send_json_response(response)
        
        # /v1/models/{id} - Belirli modeli al
        elif len(path_parts) == 4 and path_parts[-2] == "models":
            model_id = path_parts[-1]
            model = self.plugin_manager.get_model(model_id)
            if model:
                response = APIResponse(success=True, data=model.to_dict())
            else:
                response = APIResponse(success=False, error="Model bulunamadı")
            self._send_json_response(response)
        
        # /v1/health - Sağlık kontrolü
        elif path_parts[-1] == "health" and len(path_parts) == 3:
            health = self.plugin_manager.health_check()
            response = APIResponse(success=True, data=health.to_dict())
            self._send_json_response(response)
        
        # /v1/events - Event log
        elif path_parts[-1] == "events" and len(path_parts) == 3:
            events = self.plugin_manager.get_recent_events(100)
            response = APIResponse(success=True, data=[e.to_dict() for e in events])
            self._send_json_response(response)
        
        else:
            response = APIResponse(success=False, error="Bilinmeyen endpoint")
            self._send_json_response(response, 404)
    
    def do_POST(self) -> None:
        """POST isteklerini işler"""
        parsed_path = urllib.parse.urlparse(self.path)
        path_parts = parsed_path.path.split('/')
        
        # /v1/plugins - Yeni plugin yükle
        if path_parts[-1] == "plugins" and len(path_parts) == 3:
            body = self._read_json_body()
            if body:
                plugin_path = body.get("plugin_path")
                if plugin_path:
                    result = self.plugin_manager.load_plugin(plugin_path)
                    if result:
                        response = APIResponse(success=True, data=result.to_dict())
                    else:
                        response = APIResponse(success=False, error="Plugin yüklenemedi")
                    self._send_json_response(response)
                else:
                    response = APIResponse(success=False, error="plugin_path gerekli")
                    self._send_json_response(response, 400)
            else:
                response = APIResponse(success=False, error="Geçersiz JSON")
                self._send_json_response(response, 400)
        
        # /v1/plugins/{id}/reload - Plugin'i yeniden yükle
        elif len(path_parts) == 4 and path_parts[-2] == "plugins":
            plugin_id = path_parts[-1]
            result = self.plugin_manager.reload_plugin(plugin_id)
            if result:
                response = APIResponse(success=True, data=result.to_dict())
            else:
                response = APIResponse(success=False, error="Plugin yeniden yüklenemedi")
            self._send_json_response(response)
        
        # /v1/plugins/{id}/unload - Plugin'i boşalt
        elif len(path_parts) == 4 and path_parts[-2] == "plugins":
            plugin_id = path_parts[-1]
            result = self.plugin_manager.unload_plugin(plugin_id)
            if result:
                response = APIResponse(success=True, data={"status": "unloaded"})
            else:
                response = APIResponse(success=False, error="Plugin boşaltılamadı")
            self._send_json_response(response)
        
        # /v1/models - Yeni model yükle
        elif path_parts[-1] == "models" and len(path_parts) == 3:
            body = self._read_json_body()
            if body:
                model_path = body.get("model_path")
                model_name = body.get("model_name")
                model_type = body.get("model_type", "language")
                config = body.get("config", {})
                
                if model_path:
                    result = self.plugin_manager.load_model(model_path, model_name, model_type, config)
                    if result:
                        response = APIResponse(success=True, data=result.to_dict())
                    else:
                        response = APIResponse(success=False, error="Model yüklenemedi")
                    self._send_json_response(response)
                else:
                    response = APIResponse(success=False, error="model_path gerekli")
                    self._send_json_response(response, 400)
            else:
                response = APIResponse(success=False, error="Geçersiz JSON")
                self._send_json_response(response, 400)
        
        # /v1/models/{id}/reload - Model'i yeniden yükle
        elif len(path_parts) == 4 and path_parts[-2] == "models":
            model_id = path_parts[-1]
            result = self.plugin_manager.reload_model(model_id)
            if result:
                response = APIResponse(success=True, data=result.to_dict())
            else:
                response = APIResponse(success=False, error="Model yeniden yüklenemedi")
            self._send_json_response(response)
        
        # /v1/models/{id}/unload - Model'i boşalt
        elif len(path_parts) == 4 and path_parts[-2] == "models":
            model_id = path_parts[-1]
            result = self.plugin_manager.unload_model(model_id)
            if result:
                response = APIResponse(success=True, data={"status": "unloaded"})
            else:
                response = APIResponse(success=False, error="Model boşaltılamadı")
            self._send_json_response(response)
        
        else:
            response = APIResponse(success=False, error="Bilinmeyen endpoint")
            self._send_json_response(response, 404)
    
    def do_DELETE(self) -> None:
        """DELETE isteklerini işler"""
        parsed_path = urllib.parse.urlparse(self.path)
        path_parts = parsed_path.path.split('/')
        
        # /v1/plugins/{id} - Plugin'i tamamen kaldır
        if len(path_parts) == 4 and path_parts[-2] == "plugins":
            plugin_id = path_parts[-1]
            result = self.plugin_manager.unload_plugin(plugin_id)
            if result:
                response = APIResponse(success=True, data={"status": "removed"})
            else:
                response = APIResponse(success=False, error="Plugin kaldırılamadı")
            self._send_json_response(response)
        
        else:
            response = APIResponse(success=False, error="Bilinmeyen endpoint")
            self._send_json_response(response, 404)


class PluginAPI:
    """Plugin API sunucusu"""
    
    def __init__(self, plugin_manager: 'PluginManager', port: int = 8080):
        self.plugin_manager = plugin_manager
        self.port = port
        self._server: Optional[socketserver.TCPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self) -> None:
        """API sunucusunu başlatır"""
        if self._running:
            return
        
        handler = lambda *args, **kwargs: PluginAPIHandler(self.plugin_manager, *args, **kwargs)
        self._server = socketserver.TCPServer(("0.0.0.0", self.port), handler)
        self._server.allow_reuse_address = True
        
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._running = True
        
        print(f"[PluginAPI] Başlatıldı - Port {self.port}")
    
    def stop(self) -> None:
        """API sunucusunu durdurur"""
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        print("[PluginAPI] Durduruldu")
    
    def is_running(self) -> bool:
        """Sunucunun çalışıp çalışmadığını döner"""
        return self._running
