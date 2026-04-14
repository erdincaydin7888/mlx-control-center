"""MLX Dashboard — Configuration & Constants."""

from pathlib import Path

# Model dizini
MODELS_BASE_DIR = Path.home() / ".lmstudio" / "models"

# MLX server / proxy script'leri
MLX_DIR = Path.home() / "Desktop" / "MLX"
MLX_SERVER_SCRIPT = MLX_DIR / "mlx_server_patch.py"
MLX_PROXY_SCRIPT = MLX_DIR / "mlx_proxy.py"

# Python binary
PYTHON_BIN = "/opt/homebrew/bin/python3"

# Varsayılan portlar
DEFAULT_PROXY_PORT = 8087
# Server port = proxy port + 10

# Dashboard portu
DASHBOARD_PORT = 8070

# WebSocket güncelleme aralığı (saniye)
WS_UPDATE_INTERVAL = 2.0

# Model formatları
MLX_EXTENSIONS = {".safetensors"}
GGUF_EXTENSIONS = {".gguf"}
