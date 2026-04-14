"""MLX Dashboard — FastAPI Application.

Tüm API endpoint'leri, WebSocket ve static file serving.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import MODELS_BASE_DIR, DEFAULT_PROXY_PORT, WS_UPDATE_INTERVAL
from .model_scanner import scan_all_models, get_model_detail, ModelInfo
from .process_manager import (
    get_active_model,
    start_model,
    stop_model,
    switch_model,
    ProcessInfo,
)
from .system_monitor import get_system_stats
from .compatibility import calculate_compatibility

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------
# Cache
# ---------------------------------------------------------------
_model_cache: list[ModelInfo] = []
_cache_time: float = 0.0
CACHE_TTL = 300  # 5 dakika


def _get_models(force: bool = False) -> list[ModelInfo]:
    global _model_cache, _cache_time
    if force or not _model_cache or (time.time() - _cache_time > CACHE_TTL):
        _model_cache = scan_all_models()
        _cache_time = time.time()
    return _model_cache


# ---------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MLX Dashboard başlatılıyor...")
    _get_models()
    logger.info("Model taraması tamamlandı: %d model", len(_model_cache))
    yield
    logger.info("MLX Dashboard kapanıyor.")


# ---------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------
app = FastAPI(title="MLX Control Center", lifespan=lifespan)

# Frontend static dosyaları
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ---------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------
class StartRequest(BaseModel):
    model_path: str
    port: int = DEFAULT_PROXY_PORT


class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    max_tokens: int = 4096
    temperature: float = 0.7
    stream: bool = False


class CompatibilityRequest(BaseModel):
    param_count_billions: float
    quantization_bits: float = 8.0
    context_length: int = 4096
    is_moe: bool = False
    active_experts: int = 2


# ---------------------------------------------------------------
# Helper
# ---------------------------------------------------------------
def _model_to_dict(m: ModelInfo) -> dict[str, Any]:
    return dataclasses.asdict(m)


def _process_to_dict(p: ProcessInfo) -> dict[str, Any]:
    return dataclasses.asdict(p)


# ---------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------
@app.get("/api/models")
def list_models():
    """Tüm modelleri listele."""
    models = _get_models()
    return {"count": len(models), "models": [_model_to_dict(m) for m in models]}


@app.post("/api/models/rescan")
def rescan_models():
    """Model dizinini yeniden tara."""
    models = _get_models(force=True)
    return {"count": len(models), "message": f"{len(models)} model bulundu."}


@app.get("/api/models/detail")
def model_detail(path: str):
    """Tek modelin detayları."""
    p = Path(path)
    if not p.exists():
        raise HTTPException(404, f"Model dizini bulunamadı: {path}")
    return get_model_detail(path)


@app.get("/api/active")
def active_model():
    """Aktif model bilgisi."""
    info = get_active_model()
    return _process_to_dict(info)


@app.post("/api/start")
def start(req: StartRequest):
    """Modeli başlat."""
    p = Path(req.model_path)
    if not p.exists():
        raise HTTPException(404, f"Model dizini bulunamadı: {req.model_path}")
    try:
        info = start_model(req.model_path, req.port)
        return _process_to_dict(info)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc))


@app.post("/api/stop")
def stop():
    """Aktif modeli durdur."""
    stopped = stop_model()
    return {"stopped": stopped}


@app.post("/api/switch")
def switch(req: StartRequest):
    """Model değiştir."""
    p = Path(req.model_path)
    if not p.exists():
        raise HTTPException(404, f"Model dizini bulunamadı: {req.model_path}")
    try:
        info = switch_model(req.model_path, req.port)
        return _process_to_dict(info)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc))


@app.get("/api/system")
def system_stats():
    """Sistem kaynak kullanımı."""
    active = get_active_model()
    stats = get_system_stats(mlx_pid=active.server_pid)
    return dataclasses.asdict(stats)


@app.post("/api/compatibility")
def check_compatibility(req: CompatibilityRequest):
    """CanIRunThisLLM benzeri donanım uyumluluk hesaplaması."""
    result = calculate_compatibility(
        param_count_billions=req.param_count_billions,
        quantization_bits=req.quantization_bits,
        context_length=req.context_length,
        is_moe=req.is_moe,
        active_experts=req.active_experts
    )
    return dataclasses.asdict(result)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Aktif modele chat mesajı gönder."""
    active = get_active_model()
    if active.status != "running":
        raise HTTPException(400, "Aktif model yok. Önce bir model başlatın.")

    url = f"http://localhost:{active.proxy_port}/v1/chat/completions"
    payload = {
        "model": active.model_name,
        "messages": req.messages,
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "MLX server yanıt zaman aşımı (300s).")
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"MLX server hatası: {exc}")


# ---------------------------------------------------------------
# WebSocket — Canlı durum güncellemesi
# ---------------------------------------------------------------
@app.websocket("/ws/status")
async def ws_status(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            active = get_active_model()
            stats = get_system_stats(mlx_pid=active.server_pid)
            payload = {
                "active": _process_to_dict(active),
                "system": dataclasses.asdict(stats),
                "timestamp": time.time(),
            }
            await ws.send_text(json.dumps(payload))
            await asyncio.sleep(WS_UPDATE_INTERVAL)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket hatası: %s", exc)


# ---------------------------------------------------------------
# Frontend Serving
# ---------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>MLX Control Center — Frontend bulunamadı</h1>")
