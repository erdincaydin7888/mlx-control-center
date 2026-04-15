"""MLX Dashboard — Configuration & Constants."""

import os
import sys
import json
from pathlib import Path

# Load settings from settings.json if exists
_SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"
_app_settings = {}
if _SETTINGS_FILE.exists():
    try:
        with open(_SETTINGS_FILE, "r") as f:
            _app_settings = json.load(f)
    except Exception:
        pass

# ---------------------------------------------------------------
# Model directory (configurable via environment variable or settings.json)
# ---------------------------------------------------------------
_default_models_dir = _app_settings.get("models_dir")
if not _default_models_dir:
    _default_models_dir = os.getenv("MLX_MODELS_DIR", str(Path.home() / ".lmstudio" / "models"))

MODELS_BASE_DIR = Path(_default_models_dir)

# ---------------------------------------------------------------
# MLX server / proxy scripts (relative to this project)
# ---------------------------------------------------------------
_CORE_DIR = Path(__file__).resolve().parent / "core"
MLX_SERVER_SCRIPT = _CORE_DIR / "mlx_server_patch.py"
MLX_PROXY_SCRIPT = _CORE_DIR / "mlx_proxy.py"

# Fallback: check parent Mlx directory (legacy layout)
if not MLX_SERVER_SCRIPT.exists():
    _LEGACY_DIR = Path.home() / "Desktop" / "MLX"
    MLX_SERVER_SCRIPT = _LEGACY_DIR / "mlx_server_patch.py"
    MLX_PROXY_SCRIPT = _LEGACY_DIR / "mlx_proxy.py"

# ---------------------------------------------------------------
# Python binary (prefer the interpreter running this process)
# ---------------------------------------------------------------
PYTHON_BIN = os.getenv("MLX_PYTHON_BIN", sys.executable)

# ---------------------------------------------------------------
# Default ports
# ---------------------------------------------------------------
DEFAULT_PROXY_PORT = int(os.getenv("MLX_PROXY_PORT", "8087"))
# Server port = proxy port + 10

# Dashboard port
DASHBOARD_PORT = int(os.getenv("MLX_DASHBOARD_PORT", "8070"))

# WebSocket update interval (seconds)
WS_UPDATE_INTERVAL = 2.0

# Model file formats
MLX_EXTENSIONS = {".safetensors"}
GGUF_EXTENSIONS = {".gguf"}
