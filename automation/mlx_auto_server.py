#!/usr/bin/env python3
"""
MLX Otomatik Sunucu - Tam Otomasyonlu Model Yonetimi
====================================================

Bu sunucu sucuru:
- "ping" komutu geldiginde otomatik olarak RAM'e model yukler
- Belirli bir sure bosta kalirsa modeli RAM'den siler
- Cursor ve OpenCode gibi IDE'lerden dogrudan baglanabilir
- Hot-reload destegi ile model degistirme yapilabilir

Kullanım:
    python mlx_auto_server.py --port 8045 --model mlx-community/Qwen3-Coder-Next-5bit
    python mlx_auto_server.py --port 8045 --model mlx-community/Llama-3.2-3B-Instruct-4bit
"""

import argparse
import asyncio
import gc
import json
import logging
import os
import signal
import sys
import time
import threading
from dataclasses import dataclass
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs

import mlx.core as mx
from mlx_lm import load, generate, stream_generate

# ==================== LOGGING YAPILANDIRMASI ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/mlx_auto_server.log')
    ]
)
logger = logging.getLogger(__name__)

# ==================== GLOBAL DEGISKENLER ====================
_MODEL_CACHE: Dict[str, Any] = {}
_MODEL_PATH: Optional[str] = None
_IS_READY: bool = False
_LAST_ACCESS_TIME: float = 0.0
_IDLE_TIMEOUT: float = 900.0  # 15 dakika
_INFERENCE_LOCK = threading.Lock()
_MODEL_LOADING_LOCK = asyncio.Lock()

# ==================== DATA CLASSES ====================
@dataclass
class ModelConfig:
    """Model yapılandırma sınıfı"""
    path: str
    name: str
    loaded: bool = False
    last_used: float = 0.0


# ==================== MLX YONETIM SINIFI ====================
class MLXManager:
    """MLX model yonetici sinifi"""
    
    def __init__(self, model_path: str, idle_timeout: float = 900.0):
        self.model_path = model_path
        self.idle_timeout = idle_timeout
        self.model = None
        self.tokenizer = None
        self._lock = threading.Lock()
        
    def _lazy_init(self):
        """MLX'i gecikmeli baslat"""
        try:
            mx.set_cache_limit(0)  # Dinamik bellek yonetimi
        except Exception as e:
            logger.warning(f"MLX cache limit ayarlanamadi: {e}")
    
    async def load_model(self) -> bool:
        """Modeli RAM'e yukle"""
        global _IS_READY, _LAST_ACCESS_TIME
        
        async with _MODEL_LOADING_LOCK:
            if self.model is not None:
                logger.info("Model zaten RAM'de yuklu")
                _LAST_ACCESS_TIME = time.time()
                return True
            
            try:
                logger.info(f"Model yukleniyor: {self.model_path}")
                self._lazy_init()
                
                start_time = time.time()
                self.model, self.tokenizer = await asyncio.to_thread(
                    load, self.model_path
                )
                load_time = time.time() - start_time
                
                logger.info(f"Model {load_time:.2f}s icinde yuklendi")
                _IS_READY = True
                _LAST_ACCESS_TIME = time.time()
                return True
                
            except Exception as e:
                logger.error(f"Model yukleme hatasi: {e}")
                self.model = None
                self.tokenizer = None
                return False
    
    async def unload_model(self) -> bool:
        """Modeli RAM'den sil"""
        global _IS_READY
        
        async with _MODEL_LOADING_LOCK:
            if self.model is None:
                logger.info("Model zaten RAM'de degil")
                return True
            
            try:
                logger.info("Model RAM'den siliniyor...")
                
                with _INFERENCE_LOCK:
                    self.model = None
                    self.tokenizer = None
                    mx.clear_cache()
                
                gc.collect()
                _IS_READY = False
                
                logger.info("Model basariyla RAM'den silindi")
                return True
                
            except Exception as e:
                logger.error(f"Model silme hatasi: {e}")
                return False
    
    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Metin uret"""
        global _LAST_ACCESS_TIME
        
        if self.model is None:
            raise ValueError("Model yuklu degil. Önce 'load_model' cagrin.")
        
        _LAST_ACCESS_TIME = time.time()
        
        with _INFERENCE_LOCK:
            response = await asyncio.to_thread(
                generate,
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                verbose=False
            )
        
        return response
    
    async def generate_stream(self, prompt: str, max_tokens: int = 4096):
        """Metin akisli olarak uret"""
        global _LAST_ACCESS_TIME
        
        if self.model is None:
            raise ValueError("Model yuklu degil.")
        
        _LAST_ACCESS_TIME = time.time()
        
        with _INFERENCE_LOCK:
            for token in await asyncio.to_thread(
                stream_generate,
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=max_tokens
            ):
                if hasattr(token, 'text'):
                    yield token.text
                else:
                    yield str(token)
    
    def is_model_loaded(self) -> bool:
        """Modelin yuklu olup olmadigini kontrol et"""
        return self.model is not None
    
    def get_last_access_time(self) -> float:
        """Son erisim zamanini dondur"""
        return _LAST_ACCESS_TIME
    
    def get_idle_time(self) -> float:
        """Ne kadar süredir bosta oldugunu dondur"""
        return time.time() - _LAST_ACCESS_TIME
    
    def needs_unload(self) -> bool:
        """Modelin silinip silinmesi gerektigini kontrol et"""
        return self.get_idle_time() > self.idle_timeout


# ==================== SUNUCU YONETICISI ====================
class AutoMLXServer:
    """Otomatik MLX sunucu sinifi"""
    
    def __init__(self, port: int = 8045, model_path: str = None, idle_timeout: float = 900.0):
        self.port = port
        self.model_path = model_path or os.getenv("MLX_MODEL_PATH")
        self.idle_timeout = idle_timeout
        self.manager: Optional[MLXManager] = None
        self._shutdown_event = threading.Event()
        self._idle_checker: Optional[asyncio.Task] = None
        
        if self.model_path:
            self.manager = MLXManager(self.model_path, idle_timeout)
        
        logger.info(f"Sunucu baslatiliyor - Port: {port}, Model: {self.model_path}")
    
    async def _idle_checker_loop(self):
        """Bosta kalan modelleri kontrol eden döngü"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(60)  # Her 60 saniyede bir kontrol et
                
                if self.manager and self.manager.needs_unload():
                    logger.info(f"Model {self.manager.get_idle_time():.0f}s bosta kaldi, RAM'den siliniyor...")
                    await self.manager.unload_model()
                    
            except Exception as e:
                logger.error(f"Idle checker hatasi: {e}")
    
    async def ensure_model_loaded(self) -> bool:
        """Modelin yuklu oldugundan emin ol"""
        if not self.manager:
            return False
        
        if not self.manager.is_model_loaded():
            logger.info("Model yuklu degil, otomatik yukleniyor...")
            return await self.manager.load_model()
        
        return True
    
    async def handle_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Gelen istegi isle"""
        global _LAST_ACCESS_TIME
        
        request_type = data.get("type", "unknown")
        
        if request_type == "ping":
            # Ping istegi - modeli yukle
            if self.manager:
                await self.ensure_model_loaded()
                return {
                    "status": "ok",
                    "message": "Sunucu hazir",
                    "model_loaded": self.manager.is_model_loaded(),
                    "idle_time": self.manager.get_idle_time()
                }
            return {"status": "ok", "message": "Sunucu hazir"}
        
        elif request_type == "generate":
            # Metin uretme istegi
            if not await self.ensure_model_loaded():
                return {"error": "Model yuklenemedi"}
            
            prompt = data.get("prompt", "")
            max_tokens = data.get("max_tokens", 4096)
            
            try:
                response = await self.manager.generate(prompt, max_tokens)
                return {
                    "status": "ok",
                    "response": response,
                    "model": self.model_path
                }
            except Exception as e:
                logger.error(f"Generate hatasi: {e}")
                return {"error": str(e)}
        
        elif request_type == "unload":
            # Modeli manuel olarak sil
            if self.manager:
                await self.manager.unload_model()
                return {"status": "ok", "message": "Model silindi"}
            return {"error": "Yonetici yok"}
        
        elif request_type == "status":
            # Durum bilgisi
            return {
                "status": "ok",
                "model_loaded": self.manager.is_model_loaded() if self.manager else False,
                "idle_time": self.manager.get_idle_time() if self.manager else 0,
                "model_path": self.model_path
            }
        
        else:
            return {"error": f"Bilinmeyen istek tipi: {request_type}"}
    
    def start(self):
        """Sunucuyu baslat"""
        # HTTP sunucusu baslat
        server = ThreadedHTTPServer(("0.0.0.0", self.port), self)
        logger.info(f"Sunucu basariyla baslatildi - Port: {self.port}")

        # Sinyal handler'lar
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Idle checker döngüsünü baslat
        self._idle_checker = asyncio.run_coroutine_threadsafe(self._idle_checker_loop(), server.loop)

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown(server)
    
    def shutdown(self, server: HTTPServer):
        """Sunucuyu kapat"""
        logger.info("Sunucu kapatiliyor...")
        self._shutdown_event.set()
        
        if self._idle_checker:
            self._idle_checker.cancel()
        
        if self.manager:
            asyncio.run(self.manager.unload_model())
        
        server.shutdown()
        logger.info("Sunucu kapatildi")
    
    def _signal_handler(self, signum, frame):
        """Sinyal handler"""
        logger.info(f"Sinyal alindi: {signum}")
        self.shutdown()


# ==================== HTTP HANDLER ====================
class ThreadedHTTPHandler(BaseHTTPRequestHandler):
    """HTTP istek handler sinifi"""
    
    server_instance: AutoMLXServer = None
    
    def log_message(self, format, *args):
        """Log mesajlari"""
        logger.info(f"HTTP: {args[0]}")
    
    def do_GET(self):
        """GET istekleri"""
        parsed = urlparse(self.path)
        
        if parsed.path == "/health" or parsed.path == "/":
            self.send_json_response({
                "status": "ok",
                "service": "mlx-auto-server",
                "version": "1.0.0"
            })
        elif parsed.path == "/status":
            asyncio.run(self.server_instance.handle_request({"type": "status"}))
            self.send_json_response({
                "status": "ok",
                "model_loaded": self.server_instance.manager.is_model_loaded() if self.server_instance.manager else False
            })
        else:
            self.send_error(404, "Bulunamadi")
    
    def do_POST(self):
        """POST istekleri"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
            
            result = asyncio.run(self.server_instance.handle_request(data))
            
            self.send_json_response(result)
            
        except json.JSONDecodeError as e:
            self.send_error(400, f"JSON hatasi: {e}")
        except Exception as e:
            logger.error(f"POST hatasi: {e}")
            self.send_error(500, str(e))
    
    def send_json_response(self, data: Dict[str, Any], status: int = 200):
        """JSON response gonder"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))


class ThreadedHTTPServer(HTTPServer):
    """Threaded HTTP sunucusu"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shutdown_event = threading.Event()
        self.loop = None

    def start_background_loop(self):
        """Arka plan event loop"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._background_tasks())
        self.loop.close()

    async def _background_tasks(self):
        """Arka plan görevleri"""
        if self.manager:
            self._idle_checker = self.loop.create_task(self.manager._idle_checker_loop())
            await self._idle_checker


# ==================== MAIN ====================
def main():
    """Ana fonksiyon"""
    parser = argparse.ArgumentParser(description="MLX Otomatik Sunucu")
    parser.add_argument("--port", type=int, default=8080, help="Sunucu portu")
    parser.add_argument("--model", type=str, default=None, help="Model yolu")
    parser.add_argument("--idle-timeout", type=float, default=900.0, help="Idle timeout (saniye)")
    parser.add_argument("--preload", action="store_true", help="Sunucu baslatilirken modeli onceden yukle")
    
    args = parser.parse_args()
    
    # Environment variable'ları kontrol et
    if not args.model:
        args.model = os.getenv("MLX_MODEL_PATH")
    
    if not args.model:
        logger.error("Model yolu belirtilmedi! --model veya MLX_MODEL_PATH kullanin.")
        sys.exit(1)
    
    # Sunucuyu baslat
    server = AutoMLXServer(
        port=args.port,
        model_path=args.model,
        idle_timeout=args.idle_timeout
    )
    
    # ThreadedHTTPHandler'i server ile bagla
    ThreadedHTTPHandler.server_instance = server
    
    if args.preload:
        logger.info("Model onceden yukleniyor...")
        asyncio.run(server.ensure_model_loaded())
    
    server.start()


if __name__ == "__main__":
    main()
