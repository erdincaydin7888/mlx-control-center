"""MLX Dashboard — Model Scanner.

Diskteki tüm MLX/GGUF modellerini tarar ve metadata çıkarır.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import MODELS_BASE_DIR, MLX_EXTENSIONS, GGUF_EXTENSIONS

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Tek bir modelin özet bilgisi."""

    name: str
    publisher: str
    path: str
    format: str  # "mlx" | "gguf" | "unknown"
    size_gb: float
    quant_type: str
    architecture: str
    param_hint: str  # Dizin adından çıkarılan parametre ipucu
    num_experts: int | None = None
    max_context: int | None = None
    hidden_size: int | None = None
    num_layers: int | None = None
    num_heads: int | None = None
    model_type: str = ""
    vocab_size: int | None = None
    is_moe: bool = False


def _guess_quant(dirname: str) -> str:
    """Dizin adından quantization tipini çıkar."""
    dirname_lower = dirname.lower()
    for q in ["8bit", "8-bit", "6bit", "5bit", "4bit", "4.8bit", "4-bit"]:
        if q in dirname_lower:
            return q.replace("-", "")
    if "gguf" in dirname_lower:
        return "gguf"
    return "unknown"


def _guess_params(dirname: str) -> str:
    """Dizin adından parametre ipucu çıkar (ör. '35B', '480B')."""
    import re

    match = re.search(r"(\d+(?:\.\d+)?)\s*[Bb]\b", dirname)
    if match:
        return match.group(0).upper().strip()
    return ""


def _dir_size_gb(path: Path) -> float:
    """Dizinin toplam boyutunu GB cinsinden hesapla."""
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    except OSError:
        pass
    return round(total / (1024**3), 2)


def _detect_format(path: Path) -> str:
    """Model formatını dosya uzantılarına göre belirle."""
    for f in path.iterdir():
        if f.is_file():
            if f.suffix in MLX_EXTENSIONS:
                return "mlx"
            if f.suffix in GGUF_EXTENSIONS:
                return "gguf"
    return "unknown"


def _read_config(path: Path) -> dict[str, Any]:
    """config.json dosyasını oku."""
    config_file = path / "config.json"
    if config_file.exists():
        try:
            return json.loads(config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("config.json okunamadı: %s — %s", config_file, exc)
    return {}


def scan_model(model_dir: Path, publisher: str) -> ModelInfo | None:
    """Tek bir model dizinini tarar."""
    if not model_dir.is_dir():
        return None

    config = _read_config(model_dir)
    dirname = model_dir.name
    fmt = _detect_format(model_dir)

    # MoE kontrolü
    num_experts = config.get("num_experts") or config.get("num_local_experts")
    is_moe = bool(num_experts and int(num_experts) > 1)

    architectures = config.get("architectures", [])
    arch = architectures[0] if architectures else config.get("model_type", "")

    return ModelInfo(
        name=dirname,
        publisher=publisher,
        path=str(model_dir),
        format=fmt,
        size_gb=_dir_size_gb(model_dir),
        quant_type=_guess_quant(dirname),
        architecture=arch,
        param_hint=_guess_params(dirname),
        num_experts=int(num_experts) if num_experts else None,
        max_context=config.get("max_position_embeddings"),
        hidden_size=config.get("hidden_size"),
        num_layers=config.get("num_hidden_layers"),
        num_heads=config.get("num_attention_heads"),
        model_type=config.get("model_type", ""),
        vocab_size=config.get("vocab_size"),
        is_moe=is_moe,
    )


def scan_all_models(base_dir: Path | None = None) -> list[ModelInfo]:
    """Tüm model dizinini tarar, ModelInfo listesi döner."""
    base = base_dir or MODELS_BASE_DIR
    models: list[ModelInfo] = []

    if not base.exists():
        logger.warning("Model dizini bulunamadı: %s", base)
        return models

    for publisher_dir in sorted(base.iterdir()):
        if not publisher_dir.is_dir() or publisher_dir.name.startswith("."):
            continue
        publisher = publisher_dir.name
        for model_dir in sorted(publisher_dir.iterdir()):
            if not model_dir.is_dir() or model_dir.name.startswith("."):
                continue
            info = scan_model(model_dir, publisher)
            if info:
                models.append(info)

    logger.info("Toplam %d model bulundu.", len(models))
    return models


def get_model_detail(model_path: str) -> dict[str, Any]:
    """Model dizininin detaylı bilgisini döner."""
    path = Path(model_path)
    config = _read_config(path)

    gen_config_file = path / "generation_config.json"
    gen_config: dict[str, Any] = {}
    if gen_config_file.exists():
        try:
            gen_config = json.loads(gen_config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Dosya envanteri
    files: list[dict[str, Any]] = []
    for f in sorted(path.iterdir()):
        if f.is_file():
            files.append(
                {
                    "name": f.name,
                    "size_mb": round(f.stat().st_size / (1024**2), 1),
                }
            )

    return {
        "path": str(path),
        "config": config,
        "generation_config": gen_config,
        "files": files,
        "total_size_gb": _dir_size_gb(path),
    }
