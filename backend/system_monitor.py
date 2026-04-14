"""MLX Dashboard — System Monitor.

Sistem kaynaklarını (RAM, CPU, disk) ve inference istatistiklerini izler.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SystemStats:
    """Sistem kaynak kullanımı."""

    total_memory_gb: float = 0.0
    used_memory_gb: float = 0.0
    free_memory_gb: float = 0.0
    memory_percent: float = 0.0
    cpu_percent: float = 0.0
    mlx_process_memory_gb: float = 0.0
    models_disk_gb: float = 0.0
    models_disk_used_gb: float = 0.0


def get_system_stats(mlx_pid: int | None = None) -> SystemStats:
    """Sistem kaynak kullanımını topla."""
    stats = SystemStats()

    # Toplam bellek (sysctl)
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True, timeout=3,
        )
        total_bytes = int(result.stdout.strip())
        stats.total_memory_gb = round(total_bytes / (1024**3), 1)
    except Exception:
        stats.total_memory_gb = 512.0  # Fallback

    # Bellek kullanımı (vm_stat)
    try:
        result = subprocess.run(
            ["vm_stat"],
            capture_output=True, text=True, timeout=3,
        )
        lines = result.stdout.splitlines()
        page_size = 16384  # Apple Silicon varsayılan
        pages: dict[str, int] = {}
        for line in lines:
            if "page size of" in line:
                try:
                    page_size = int(line.split("of")[-1].strip().rstrip("."))
                except ValueError:
                    pass
            elif ":" in line:
                parts = line.split(":")
                key = parts[0].strip()
                try:
                    val = int(parts[1].strip().rstrip("."))
                    pages[key] = val
                except ValueError:
                    pass

        free_pages = pages.get("Pages free", 0)
        inactive_pages = pages.get("Pages inactive", 0)
        active_pages = pages.get("Pages active", 0)
        wired_pages = pages.get("Pages wired down", 0)
        speculative_pages = pages.get("Pages speculative", 0)
        compressed_pages = pages.get("Pages stored in compressor", 0)

        used_bytes = (active_pages + wired_pages + compressed_pages) * page_size
        free_bytes = (free_pages + inactive_pages + speculative_pages) * page_size

        stats.used_memory_gb = round(used_bytes / (1024**3), 1)
        stats.free_memory_gb = round(free_bytes / (1024**3), 1)
        stats.memory_percent = round(
            (stats.used_memory_gb / stats.total_memory_gb) * 100, 1
        ) if stats.total_memory_gb > 0 else 0.0

    except Exception as exc:
        logger.warning("vm_stat okunamadı: %s", exc)

    # CPU kullanımı (top snapshot)
    try:
        result = subprocess.run(
            ["top", "-l", "1", "-n", "0", "-stats", "cpu"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if "CPU usage" in line:
                # "CPU usage: 5.88% user, 3.92% sys, 90.19% idle"
                import re
                idle_match = re.search(r"([\d.]+)%\s*idle", line)
                if idle_match:
                    idle = float(idle_match.group(1))
                    stats.cpu_percent = round(100.0 - idle, 1)
                break
    except Exception as exc:
        logger.warning("CPU bilgisi okunamadı: %s", exc)

    # MLX sürecinin bellek kullanımı
    if mlx_pid:
        try:
            result = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(mlx_pid)],
                capture_output=True, text=True, timeout=3,
            )
            rss_kb = int(result.stdout.strip())
            stats.mlx_process_memory_gb = round(rss_kb / (1024**2), 1)
        except Exception:
            pass

    # Model dizini disk kullanımı (hızlı hesaplama yerine cache'lenebilir)
    try:
        model_dir = os.path.expanduser("~/.lmstudio/models")
        result = subprocess.run(
            ["du", "-s", "-k", model_dir],
            capture_output=True, text=True, timeout=10,
        )
        kb = int(result.stdout.split()[0])
        stats.models_disk_used_gb = round(kb / (1024**2), 1)
    except Exception:
        stats.models_disk_used_gb = 4200.0  # Fallback ~4.2TB

    return stats
