"""MLX Dashboard — Process Manager.

MLX server ve proxy süreçlerini başlatır, durdurur ve izler.
"""

from __future__ import annotations

import logging
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .config import MLX_SERVER_SCRIPT, MLX_PROXY_SCRIPT, PYTHON_BIN, DEFAULT_PROXY_PORT

logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """Aktif model süreci bilgisi."""

    server_pid: int | None = None
    proxy_pid: int | None = None
    model_name: str = ""
    model_path: str = ""
    proxy_port: int = DEFAULT_PROXY_PORT
    server_port: int = DEFAULT_PROXY_PORT + 10
    started_at: float = 0.0
    status: str = "stopped"  # "running" | "starting" | "stopped" | "error"


# Modül seviyesinde aktif süreç takibi
_active: ProcessInfo = ProcessInfo()
_server_proc: subprocess.Popen | None = None
_proxy_proc: subprocess.Popen | None = None


def get_active_model() -> ProcessInfo:
    """Aktif model bilgisini döner. Önce iç state'e, sonra ps'e bakar."""
    global _active

    # Eğer iç state'de running varsa, PID hâlâ yaşıyor mu kontrol et
    if _active.status == "running" and _active.server_pid:
        try:
            os.kill(_active.server_pid, 0)
        except (OSError, ProcessLookupError):
            _active.status = "stopped"
            _active.server_pid = None
            _active.proxy_pid = None
            return _active
        return _active

    # İç state boşsa, ps ile bul (önceden başlatılmış süreçler)
    info = _detect_from_ps()
    if info:
        _active = info
    return _active


def _detect_from_ps() -> ProcessInfo | None:
    """ps aux ile çalışan MLX süreçlerini tespit et."""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = result.stdout.splitlines()
    except Exception:
        return None

    server_pid = None
    proxy_pid = None
    model_path = ""
    model_name = ""
    server_port = 0
    proxy_port = 0

    for line in lines:
        if "mlx_server_patch.py" in line and "--model" in line:
            parts = line.split()
            try:
                server_pid = int(parts[1])
            except (IndexError, ValueError):
                continue

            # Model path'i çıkar
            model_match = re.search(r"--model\s+(\S+)", line)
            if model_match:
                model_path = model_match.group(1)
                model_name = Path(model_path).name

            # Port'u çıkar
            port_match = re.search(r"--port\s+(\d+)", line)
            if port_match:
                server_port = int(port_match.group(1))

        elif "mlx_proxy.py" in line:
            parts = line.split()
            try:
                proxy_pid = int(parts[1])
            except (IndexError, ValueError):
                continue
            # Proxy port
            port_match = re.search(r"mlx_proxy\.py\s+(\d+)", line)
            if port_match:
                proxy_port = int(port_match.group(1))

    if server_pid:
        return ProcessInfo(
            server_pid=server_pid,
            proxy_pid=proxy_pid,
            model_name=model_name,
            model_path=model_path,
            proxy_port=proxy_port or DEFAULT_PROXY_PORT,
            server_port=server_port or (proxy_port + 10 if proxy_port else DEFAULT_PROXY_PORT + 10),
            started_at=time.time(),
            status="running",
        )
    return None


def stop_model() -> bool:
    """Aktif MLX server ve proxy'yi durdur."""
    global _active, _server_proc, _proxy_proc

    stopped_any = False

    # İç subprocess referanslarını durdur
    for label, proc in [("server", _server_proc), ("proxy", _proxy_proc)]:
        if proc and proc.poll() is None:
            logger.info("%s durduruluyor (PID %d)...", label, proc.pid)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
            stopped_any = True

    # ps'den tespit edilen PID'leri de durdur
    for pid in [_active.server_pid, _active.proxy_pid]:
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                # Biraz bekle
                for _ in range(50):
                    try:
                        os.kill(pid, 0)
                        time.sleep(0.1)
                    except OSError:
                        break
                else:
                    # Hâlâ yaşıyorsa SIGKILL
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except OSError:
                        pass
                stopped_any = True
            except (OSError, ProcessLookupError):
                pass

    _server_proc = None
    _proxy_proc = None
    _active = ProcessInfo()
    logger.info("Model durduruldu.")
    return stopped_any


def start_model(model_path: str, proxy_port: int = DEFAULT_PROXY_PORT, adapter_path: str | None = None) -> ProcessInfo:
    """Modeli başlat. Önce mevcut aktif modeli durdurur."""
    global _active, _server_proc, _proxy_proc

    # Önceki modeli durdur
    if _active.status == "running":
        stop_model()

    server_port = proxy_port + 10
    model_name = Path(model_path).name

    _active = ProcessInfo(
        model_name=model_name,
        model_path=model_path,
        proxy_port=proxy_port,
        server_port=server_port,
        started_at=time.time(),
        status="starting",
    )

    try:
        # 1. MLX Server başlat
        logger.info("MLX Server başlatılıyor: %s (port %d)", model_name, server_port)
        cmd_args = [
            PYTHON_BIN,
            str(MLX_SERVER_SCRIPT),
            "--model", model_path,
            "--port", str(server_port),
            "--log-level", "INFO",
        ]
        if adapter_path:
            cmd_args.extend(["--adapter-path", adapter_path])
            
        _server_proc = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _active.server_pid = _server_proc.pid

        # Server'ın yüklenmesini bekle (model yükleme zaman alabilir)
        time.sleep(3)

        if _server_proc.poll() is not None:
            # Süreç hemen çıktıysa hata var
            output = _server_proc.stdout.read() if _server_proc.stdout else ""
            _active.status = "error"
            logger.error("MLX Server başlatılamadı: %s", output[:500])
            raise RuntimeError(f"MLX Server başlatılamadı: {output[:500]}")

        # 2. MLX Proxy başlat
        logger.info("MLX Proxy başlatılıyor: port %d", proxy_port)
        _proxy_proc = subprocess.Popen(
            [
                PYTHON_BIN,
                str(MLX_PROXY_SCRIPT),
                str(proxy_port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _active.proxy_pid = _proxy_proc.pid

        time.sleep(1)
        if _proxy_proc.poll() is not None:
            output = _proxy_proc.stdout.read() if _proxy_proc.stdout else ""
            _active.status = "error"
            # Server'ı da durdur
            _server_proc.terminate()
            logger.error("MLX Proxy başlatılamadı: %s", output[:500])
            raise RuntimeError(f"MLX Proxy başlatılamadı: {output[:500]}")

        _active.status = "running"
        logger.info("Model başarıyla başlatıldı: %s", model_name)
        return _active

    except Exception as exc:
        _active.status = "error"
        logger.exception("Model başlatma hatası")
        raise


def switch_model(model_path: str, proxy_port: int = DEFAULT_PROXY_PORT, adapter_path: str | None = None) -> ProcessInfo:
    """Aktif modeli değiştir (stop → start)."""
    logger.info("Model değiştiriliyor: %s", Path(model_path).name)
    return start_model(model_path, proxy_port, adapter_path)


def read_server_logs(max_lines: int = 30) -> list[str]:
    """Aktif MLX server'ın son log satırlarını oku."""
    global _server_proc
    if not _server_proc or not _server_proc.stdout:
        return []

    lines: list[str] = []
    try:
        # Non-blocking okuma
        import select
        while select.select([_server_proc.stdout], [], [], 0)[0]:
            line = _server_proc.stdout.readline()
            if line:
                lines.append(line.rstrip())
            else:
                break
    except Exception:
        pass
    return lines[-max_lines:]
