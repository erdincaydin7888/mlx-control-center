"""MLX Dashboard — Configuration & Constants."""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------
# Model directory (configurable via environment variable)
# ---------------------------------------------------------------
MODELS_BASE_DIR = Path(
    os.getenv("MLX_MODELS_DIR", str(Path.home() / ".lmstudio" / "models"))
)

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
