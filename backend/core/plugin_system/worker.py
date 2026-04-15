"""
Plugin Sistemi - Worker Thread Yönetimi
========================================

Bu modül plugin işlemleri için worker thread havuzunu yönetir.
"""

import threading
import queue
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from .models import PluginStatus


@dataclass
class WorkerTask:
    """Worker görevi"""
    id: str
    name: str
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    timeout: float = 300.0  # 5 dakika varsayılan timeout
    
    def execute(self) -> Any:
        """Görevi çalıştırır"""
        return self.func(*self.args, **self.kwargs)


class WorkerThread(threading.Thread):
    """Worker thread"""
    
    def __init__(self, name: str, task_queue: queue.Queue, shutdown_event: threading.Event):
        super().__init__(name=name, daemon=True)
        self.task_queue = task_queue
        self.shutdown_event = shutdown_event
        self.current_task: Optional[WorkerTask] = None
        self.tasks_completed = 0
        self.tasks_failed = 0
        self._lock = threading.Lock()
    
    def run(self) -> None:
        """Thread çalıştırma döngüsü"""
        while not self.shutdown_event.is_set():
            try:
                task = self.task_queue.get(timeout=1.0)
                self._execute_task(task)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[WorkerThread] Hata: {e}")
    
    def _execute_task(self, task: WorkerTask) -> None:
        """Görevi çalıştırır"""
        with self._lock:
            self.current_task = task
        
        try:
            result = task.execute()
            with self._lock:
                self.tasks_completed += 1
            return result
        except Exception as e:
            with self._lock:
                self.tasks_failed += 1
            print(f"[WorkerThread] Görev hatası ({task.name}): {e}")
            raise
        finally:
            with self._lock:
                self.current_task = None


class WorkerPool:
    """Worker thread havuzu"""
    
    def __init__(self, num_workers: int = 4, max_queue_size: int = 100):
        self.num_workers = num_workers
        self.max_queue_size = max_queue_size
        self.task_queue = queue.Queue(maxsize=max_queue_size)
        self.shutdown_event = threading.Event()
        self.workers: List[WorkerThread] = []
        self._lock = threading.Lock()
        self._started = False
    
    def start(self) -> None:
        """Worker havuzunu başlatır"""
        if self._started:
            return
        
        self.shutdown_event.clear()
        
        for i in range(self.num_workers):
            worker = WorkerThread(
                name=f"PluginWorker-{i}",
                task_queue=self.task_queue,
                shutdown_event=self.shutdown_event
            )
            worker.start()
            self.workers.append(worker)
        
        self._started = True
        print(f"[WorkerPool] Başlatıldı - {self.num_workers} worker")
    
    def stop(self) -> None:
        """Worker havuzunu durdurur"""
        if not self._started:
            return
        
        self.shutdown_event.set()
        
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers.clear()
        self._started = False
        print("[WorkerPool] Durduruldu")
    
    def submit(self, name: str, func: Callable, *args, priority: int = 0, **kwargs) -> Optional[WorkerTask]:
        """Görevi havuza ekler"""
        if not self._started:
            raise RuntimeError("WorkerPool başlatılmamış")
        
        task = WorkerTask(
            id=str(uuid.uuid4()),
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority
        )
        
        try:
            self.task_queue.put(task, block=False)
            return task
        except queue.Full:
            print(f"[WorkerPool] Kuyruk dolu: {name}")
            return None
    
    def submit_async(self, name: str, func: Callable, *args, priority: int = 0, **kwargs) -> threading.Thread:
        """Görevi asenkron olarak çalıştırır"""
        def wrapper():
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(f"[WorkerPool] Asenkron görev hatası ({name}): {e}")
        
        thread = threading.Thread(target=wrapper, name=f"Async-{name}", daemon=True)
        thread.start()
        return thread
    
    def get_stats(self) -> Dict[str, Any]:
        """İstatistikleri döner"""
        with self._lock:
            total_completed = sum(w.tasks_completed for w in self.workers)
            total_failed = sum(w.tasks_failed for w in self.workers)
            current_tasks = [w.current_task.name if w.current_task else None for w in self.workers]
        
        return {
            "num_workers": len(self.workers),
            "total_completed": total_completed,
            "total_failed": total_failed,
            "queue_size": self.task_queue.qsize(),
            "current_tasks": current_tasks
        }
    
    def is_running(self) -> bool:
        """Havuzun çalışıp çalışmadığını döner"""
        return self._started
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
