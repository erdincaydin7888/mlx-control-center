"""
Plugin Sistemi - Registry
=========================

Bu modül plugin registry sistemini sağlar.
Plugin'leri merkezi olarak kaydeder ve yönetir.
"""

import os
import json
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from .models import PluginInfo, PluginStatus


@dataclass
class RegistryEntry:
    """Registry girdisi"""
    plugin_id: str
    plugin_info: PluginInfo
    registered_at: datetime
    last_heartbeat: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "plugin_info": self.plugin_info.to_dict(),
            "registered_at": self.registered_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "metadata": self.metadata
        }


class PluginRegistry:
    """Merkezi plugin registry"""
    
    def __init__(self, registry_path: str = None):
        self.registry_path = registry_path or os.path.join(
            os.path.expanduser("~"), ".mlx", "plugin_registry.json"
        )
        self._entries: Dict[str, RegistryEntry] = {}
        self._lock = threading.RLock()
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Registry dosyasından yükler"""
        try:
            if os.path.exists(self.registry_path):
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                    for plugin_id, entry_data in data.get("entries", {}).items():
                        plugin_info = PluginInfo(
                            id=entry_data["plugin_info"]["id"],
                            name=entry_data["plugin_info"]["name"],
                            version=entry_data["plugin_info"]["version"],
                            description=entry_data["plugin_info"]["description"],
                            author=entry_data["plugin_info"]["author"],
                            entry_point=entry_data["plugin_info"]["entry_point"],
                            status=PluginStatus(entry_data["plugin_info"]["status"]),
                            created_at=datetime.fromisoformat(entry_data["plugin_info"]["created_at"]),
                            updated_at=datetime.fromisoformat(entry_data["plugin_info"]["updated_at"]),
                            config=entry_data["plugin_info"].get("config", {}),
                            dependencies=entry_data["plugin_info"].get("dependencies", []),
                            metadata=entry_data["plugin_info"].get("metadata", {})
                        )
                        self._entries[plugin_id] = RegistryEntry(
                            plugin_id=plugin_id,
                            plugin_info=plugin_info,
                            registered_at=datetime.fromisoformat(entry_data["registered_at"]),
                            last_heartbeat=datetime.fromisoformat(entry_data["last_heartbeat"]),
                            metadata=entry_data.get("metadata", {})
                        )
        except Exception as e:
            print(f"[PluginRegistry] Registry yükleme hatası: {e}")
    
    def _save_registry(self) -> None:
        """Registry'yi dosyaya kaydeder"""
        try:
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            data = {
                "entries": {
                    pid: entry.to_dict()
                    for pid, entry in self._entries.items()
                },
                "last_updated": datetime.now().isoformat()
            }
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[PluginRegistry] Registry kaydetme hatası: {e}")
    
    def register(self, plugin_info: PluginInfo, metadata: Dict[str, Any] = None) -> RegistryEntry:
        """Plugin'i kaydeder"""
        with self._lock:
            plugin_id = plugin_info.id
            entry = RegistryEntry(
                plugin_id=plugin_id,
                plugin_info=plugin_info,
                registered_at=datetime.now(),
                last_heartbeat=datetime.now(),
                metadata=metadata or {}
            )
            self._entries[plugin_id] = entry
            self._save_registry()
            return entry
    
    def unregister(self, plugin_id: str) -> bool:
        """Plugin'i kayıttan kaldırır"""
        with self._lock:
            if plugin_id in self._entries:
                del self._entries[plugin_id]
                self._save_registry()
                return True
            return False
    
    def update_heartbeat(self, plugin_id: str) -> bool:
        """Heartbeat günceller"""
        with self._lock:
            if plugin_id in self._entries:
                self._entries[plugin_id].last_heartbeat = datetime.now()
                self._save_registry()
                return True
            return False
    
    def get(self, plugin_id: str) -> Optional[RegistryEntry]:
        """Plugin kaydını döner"""
        with self._lock:
            return self._entries.get(plugin_id)
    
    def get_all(self) -> List[RegistryEntry]:
        """Tüm kayıtları döner"""
        with self._lock:
            return list(self._entries.values())
    
    def get_by_status(self, status: PluginStatus) -> List[RegistryEntry]:
        """Belirli durumdaki kayıtları döner"""
        with self._lock:
            return [
                e for e in self._entries.values()
                if e.plugin_info.status == status
            ]
    
    def get_active(self) -> List[RegistryEntry]:
        """Aktif kayıtları döner"""
        return self.get_by_status(PluginStatus.ACTIVE)
    
    def get_by_name(self, name: str) -> Optional[RegistryEntry]:
        """İsme göre kaydı döner"""
        with self._lock:
            for entry in self._entries.values():
                if entry.plugin_info.name == name:
                    return entry
            return None
    
    def clear(self) -> None:
        """Tüm kayıtları temizler"""
        with self._lock:
            self._entries.clear()
            self._save_registry()
