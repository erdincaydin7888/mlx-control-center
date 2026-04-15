"""
Plugin Sistemi - Event Sistemi
===============================

Bu modül event türlerini ve event yöneticisini içerir.
Event-driven mimari için temel oluşturur.
"""

import threading
import queue
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid

from .models import Event, EventType


class EventDispatcher:
    """Event dağıtıcı - event'leri ilgili handler'lara yönlendirir"""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._global_handlers: List[Callable] = []
        self._lock = threading.Lock()
    
    def register(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Belirli bir event türüne handler ekler"""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
    
    def register_global(self, handler: Callable[[Event], None]) -> None:
        """Tüm event türlerine uygulanacak global handler ekler"""
        with self._lock:
            self._global_handlers.append(handler)
    
    def unregister(self, event_type: EventType, handler: Callable[[Event], None]) -> bool:
        """Handler'ı event türünden kaldırır"""
        with self._lock:
            if event_type in self._handlers:
                try:
                    self._handlers[event_type].remove(handler)
                    return True
                except ValueError:
                    return False
            return False
    
    def dispatch(self, event: Event) -> None:
        """Event'i dispatch eder"""
        with self._lock:
            handlers = list(self._global_handlers)
            if event.type in self._handlers:
                handlers.extend(self._handlers[event.type])
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # Hataları yakala ve devam et
                print(f"[EventDispatcher] Handler hatası: {e}")
    
    def dispatch_sync(self, event_type: EventType, source: str, payload: Dict[str, Any]) -> None:
        """Senkron event dispatch"""
        event = Event.create(event_type, source, payload)
        self.dispatch(event)


class EventPublisher:
    """Event yayıncısı - event'leri oluşturur ve dağıtır"""
    
    def __init__(self, dispatcher: Optional[EventDispatcher] = None):
        self.dispatcher = dispatcher or EventDispatcher()
        self._queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def publish(self, event_type: EventType, source: str, payload: Dict[str, Any]) -> Event:
        """Event oluşturur ve yayını yapar"""
        event = Event.create(event_type, source, payload)
        self.dispatcher.dispatch(event)
        return event
    
    def start(self) -> None:
        """Asenkron event processing başlatır"""
        self._running = True
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Event processing durdurur"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _process_queue(self) -> None:
        """Kuyruktaki event'leri işler"""
        while self._running:
            try:
                event_type, source, payload = self._queue.get(timeout=1)
                self.publish(event_type, source, payload)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[EventPublisher] Kuyruk işleme hatası: {e}")
    
    def enqueue(self, event_type: EventType, source: str, payload: Dict[str, Any]) -> None:
        """Event'i kuyruğa ekler"""
        self._queue.put((event_type, source, payload))
    
    @property
    def handlers_count(self) -> int:
        """Toplam handler sayısını döner"""
        with self.dispatcher._lock:
            count = len(self.dispatcher._global_handlers)
            for handlers in self.dispatcher._handlers.values():
                count += len(handlers)
            return count
