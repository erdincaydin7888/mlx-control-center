"""
Plugin Sistemi - Veri Modelleri
================================

Bu modül plugin sisteminin veri yapılarını ve DTO'larını içerir.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from datetime import datetime
import uuid


class PluginStatus(Enum):
    """Plugin yaşam döngüsü durumları"""
    PENDING = "pending"
    LOADING = "loading"
    ACTIVE = "active"
    UNLOADING = "unloading"
    INACTIVE = "inactive"
    ERROR = "error"


class EventType(Enum):
    """Sistem event türleri"""
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"
    MODEL_LOADED = "model_loaded"
    MODEL_UNLOADED = "model_unloaded"
    MODEL_RELOADED = "model_reloaded"
    HEALTH_CHECK = "health_check"
    CONFIG_CHANGED = "config_changed"


@dataclass
class PluginInfo:
    """Plugin meta bilgileri"""
    id: str
    name: str
    version: str
    description: str
    author: str
    entry_point: str
    status: PluginStatus = PluginStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "entry_point": self.entry_point,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "config": self.config,
            "dependencies": self.dependencies,
            "metadata": self.metadata
        }


@dataclass
class ModelInfo:
    """Model meta bilgileri"""
    id: str
    name: str
    path: str
    type: str
    status: PluginStatus = PluginStatus.PENDING
    loaded: bool = False
    loaded_at: Optional[datetime] = None
    config: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "status": self.status.value,
            "loaded": self.loaded,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "config": self.config,
            "metrics": self.metrics
        }


@dataclass
class Event:
    """Sistem eventi"""
    id: str
    type: EventType
    timestamp: datetime
    source: str
    payload: Dict[str, Any]

    @classmethod
    def create(cls, event_type: EventType, source: str, payload: Dict[str, Any]) -> 'Event':
        return cls(
            id=str(uuid.uuid4()),
            type=event_type,
            timestamp=datetime.now(),
            source=source,
            payload=payload
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "payload": self.payload
        }


@dataclass
class HealthCheckResult:
    """Sistem sağlık kontrolü sonucu"""
    status: str
    timestamp: datetime = field(default_factory=datetime.now)
    plugins_active: int = 0
    models_loaded: int = 0
    memory_usage_mb: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "plugins_active": self.plugins_active,
            "models_loaded": self.models_loaded,
            "memory_usage_mb": self.memory_usage_mb,
            "errors": self.errors
        }


@dataclass
class PluginConfig:
    """Plugin yapılandırma şeması"""
    plugin_path: str
    enabled: bool = True
    auto_reload: bool = False
    watch_interval: int = 5
    model_config: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginConfig':
        return cls(
            plugin_path=data.get("plugin_path", ""),
            enabled=data.get("enabled", True),
            auto_reload=data.get("auto_reload", False),
            watch_interval=data.get("watch_interval", 5),
            model_config=data.get("model_config", {}),
            environment=data.get("environment", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_path": self.plugin_path,
            "enabled": self.enabled,
            "auto_reload": self.auto_reload,
            "watch_interval": self.watch_interval,
            "model_config": self.model_config,
            "environment": self.environment
        }
