"""
Örnek Plugin - Metrics Collector
=================================

Bu plugin, sistem metriklerini toplar ve raporlar.
"""

import os
import sys
import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

# Plugin meta bilgileri
__plugin_name__ = "Metrics Collector"
__version__ = "1.0.0"
__description__ = "Sistem metriklerini toplar ve raporlar"
__author__ = "Plugin System"
__plugin_path__ = os.path.dirname(os.path.abspath(__file__))


@dataclass
class MetricPoint:
    """Tek metrik noktası"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Metrics collector plugin"""
    
    def __init__(self):
        self.name = __plugin_name__
        self.version = __version__
        self.enabled = True
        self._metrics: Dict[str, List[MetricPoint]] = {}
        self._gauges: Dict[str, float] = {}
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def record_metric(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Metrik kaydeder"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            
            point = MetricPoint(
                timestamp=datetime.now(),
                value=value,
                labels=labels or {}
            )
            self._metrics[name].append(point)
            
            # 1000 noktadan fazlaysa eski noktaları sil
            if len(self._metrics[name]) > 1000:
                self._metrics[name] = self._metrics[name][-1000:]
    
    def set_gauge(self, name: str, value: float) -> None:
        """Gauge metriğini ayarlar"""
        with self._lock:
            self._gauges[name] = value
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Counter metriğini artırır"""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = 0
            self._counters[name] += value
    
    def record_histogram(self, name: str, value: float) -> None:
        """Histogram metriğini kaydeder"""
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = []
            self._histograms[name].append(value)
            
            # 1000 noktadan fazlaysa eski noktaları sil
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-1000:]
    
    def get_metric(self, name: str, window_seconds: int = 60) -> List[Dict[str, Any]]:
        """Metriği döner"""
        with self._lock:
            if name not in self._metrics:
                return []
            
            cutoff = datetime.now().timestamp() - window_seconds
            return [
                {
                    "timestamp": p.timestamp.isoformat(),
                    "value": p.value,
                    "labels": p.labels
                }
                for p in self._metrics[name]
                if p.timestamp.timestamp() > cutoff
            ]
    
    def get_gauge(self, name: str) -> Optional[float]:
        """Gauge metriğini döner"""
        with self._lock:
            return self._gauges.get(name)
    
    def get_counter(self, name: str) -> int:
        """Counter metriğini döner"""
        with self._lock:
            return self._counters.get(name, 0)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Histogram istatistiklerini döner"""
        with self._lock:
            if name not in self._histograms:
                return {}
            
            values = self._histograms[name]
            return {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values) if values else 0,
                "min": min(values) if values else 0,
                "max": max(values) if values else 0
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Tüm metrikleri döner"""
        with self._lock:
            return {
                "gauges": self._gauges.copy(),
                "counters": self._counters.copy(),
                "histograms": {
                    k: self.get_histogram_stats(k)
                    for k in self._histograms.keys()
                }
            }
    
    def get_info(self) -> Dict[str, Any]:
        """Plugin bilgilerini döner"""
        with self._lock:
            return {
                "name": self.name,
                "version": self.version,
                "enabled": self.enabled,
                "metrics_count": len(self._metrics),
                "gauges_count": len(self._gauges),
                "counters_count": len(self._counters),
                "histograms_count": len(self._histograms)
            }
    
    def start(self) -> None:
        """Metrics toplamayı başlatır"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()
        print(f"[MetricsCollector] Başlatıldı")
    
    def stop(self) -> None:
        """Metrics toplamayı durdurur"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print(f"[MetricsCollector] Durduruldu")
    
    def _collect_loop(self) -> None:
        """Döngüsel metrik toplama"""
        while self._running:
            try:
                # Sistem metriklerini topla
                try:
                    import psutil
                    process = psutil.Process()
                    
                    # RAM kullanımı
                    self.set_gauge("memory_usage_mb", process.memory_info().rss / (1024 * 1024))
                    
                    # CPU kullanımı
                    self.set_gauge("cpu_usage_percent", process.cpu_percent())
                    
                    # Thread sayısı
                    self.set_gauge("thread_count", process.num_threads())
                except ImportError:
                    pass
                
                time.sleep(10)  # Her 10 saniyede bir
            except Exception as e:
                print(f"[MetricsCollector] Toplama hatası: {e}")


# Plugin instance
plugin_instance = MetricsCollector()


def get_plugin() -> MetricsCollector:
    """Plugin instance'ını döner"""
    return plugin_instance


def on_load() -> None:
    """Plugin yüklendiğinde çağrılır"""
    print(f"[MetricsCollector] Plugin yüklendi: {__plugin_name__} v{__version__}")
    plugin_instance.start()


def on_unload() -> None:
    """Plugin boşaltıldığında çağrılır"""
    print(f"[MetricsCollector] Plugin boşaltıldı: {__plugin_name__}")
    plugin_instance.stop()
