"""
Plugin Sistemi - Dosya İzleyici (File Watcher)
==============================================

Bu modül dosya değişikliklerini izleyerek otomatik yeniden yükleme (hot-reload) sağlar.
"""

import os
import time
import threading
import fnmatch
from typing import Dict, List, Callable, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent


class PluginFileHandler(FileSystemEventHandler):
    """Dosya değişikliklerini yakalayan handler"""
    
    def __init__(self, callback: Callable[[str, str], None]):
        self.callback = callback
        self._last_check = time.time()
        self._debounce_delay = 2.0  # Debounce süresi (saniye)
    
    def on_modified(self, event: FileModifiedEvent) -> None:
        """Dosya değiştirildiğinde çağrılır"""
        if event.is_directory:
            return
        self._handle_event("modified", event.src_path)
    
    def on_created(self, event: FileCreatedEvent) -> None:
        """Dosya oluşturulduğunda çağrılır"""
        if event.is_directory:
            return
        self._handle_event("created", event.src_path)
    
    def on_deleted(self, event: FileDeletedEvent) -> None:
        """Dosya silindiğinde çağrılır"""
        if event.is_directory:
            return
        self._handle_event("deleted", event.src_path)
    
    def _handle_event(self, event_type: str, path: str) -> None:
        """Event'i işler (debounce ile)"""
        current_time = time.time()
        if current_time - self._last_check < self._debounce_delay:
            return
        self._last_check = current_time
        self.callback(event_type, path)


class FileWatcher:
    """Dosya değişikliklerini izleyen watcher"""
    
    def __init__(self, watch_interval: int = 5):
        self._watch_interval = watch_interval
        self._watched_paths: Dict[str, Set[str]] = {}  # plugin_path -> set of file patterns
        self._callbacks: Dict[str, List[Callable[[str, str], None]]] = {}
        self._observer: Optional[Observer] = None
        self._running = False
        self._lock = threading.RLock()
    
    def add_watch(self, plugin_path: str, patterns: List[str] = None) -> None:
        """Yeni bir yol izlemeye başlar"""
        patterns = patterns or ["*.py", "*.json", "*.yaml", "*.yml"]
        
        with self._lock:
            self._watched_paths[plugin_path] = set(patterns)
            
            if self._observer:
                self._observer.schedule(
                    PluginFileHandler(self._on_file_change),
                    plugin_path,
                    recursive=True
                )
    
    def remove_watch(self, plugin_path: str) -> None:
        """Yolun izlemesini durdurur"""
        with self._lock:
            if plugin_path in self._watched_paths:
                del self._watched_paths[plugin_path]
            
            if self._observer:
                # Observer'dan event handler'ı kaldır
                for handler in list(self._observer.handlers):
                    if hasattr(handler, 'callback'):
                        self._observer.unschedule(handler)
    
    def register_callback(self, plugin_path: str, callback: Callable[[str, str], None]) -> None:
        """Callback kaydeder"""
        with self._lock:
            if plugin_path not in self._callbacks:
                self._callbacks[plugin_path] = []
            self._callbacks[plugin_path].append(callback)
    
    def start(self) -> None:
        """Watcher'ı başlatır"""
        if self._running:
            return
        
        self._running = True
        self._observer = Observer()
        
        with self._lock:
            for plugin_path in self._watched_paths.keys():
                self._observer.schedule(
                    PluginFileHandler(self._on_file_change),
                    plugin_path,
                    recursive=True
                )
        
        self._observer.start()
        print(f"[FileWatcher] Başlatıldı - {len(self._watched_paths)} yol izleniyor")
    
    def stop(self) -> None:
        """Watcher'ı durdurur"""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
        print("[FileWatcher] Durduruldu")
    
    def _on_file_change(self, event_type: str, path: str) -> None:
        """Dosya değişikliği olduğunda çağrılır"""
        with self._lock:
            for plugin_path, patterns in self._watched_paths.items():
                if path.startswith(plugin_path):
                    for pattern in patterns:
                        if fnmatch.fnmatch(os.path.basename(path), pattern):
                            callbacks = list(self._callbacks.get(plugin_path, []))
                            for callback in callbacks:
                                try:
                                    callback(event_type, path)
                                except Exception as e:
                                    print(f"[FileWatcher] Callback hatası: {e}")
                            break
    
    def is_watching(self, plugin_path: str) -> bool:
        """Yolun izlenip izlenmediğini kontrol eder"""
        with self._lock:
            return plugin_path in self._watched_paths
    
    def get_watched_paths(self) -> List[str]:
        """İzlenen tüm yolları döner"""
        with self._lock:
            return list(self._watched_paths.keys())
