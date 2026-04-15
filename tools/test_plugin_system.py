"""
Plugin Sistemi Test Dosyası
============================

Bu dosya, plugin sisteminin temel işlevlerini test eder.
"""

import sys
import os
import time
import json
import threading
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugin_system import (
    PluginManager,
    PluginAPI,
    HotReloadManager,
    ModelLoader,
    EventPublisher,
    EventType,
    PluginInfo,
    PluginStatus,
    ModelInfo,
    APIResponse
)


def test_plugin_manager():
    """PluginManager testi"""
    print("\n=== PluginManager Testi ===")
    
    pm = PluginManager(proxy_port=5000, api_port=8080)
    
    # Plugin bilgisi oluştur
    plugin_info = PluginInfo(
        id="test_plugin_1",
        name="Test Plugin",
        version="1.0.0",
        description="Test plugin",
        author="Test Author",
        entry_point="/tmp/test_plugin"
    )
    
    print(f"Plugin bilgisi: {plugin_info.to_dict()}")
    print("✓ PluginManager testi başarılı")
    return True


def test_model_loader():
    """ModelLoader testi"""
    print("\n=== ModelLoader Testi ===")
    
    el = EventPublisher()
    ml = ModelLoader(el)
    
    # Varsayılan loader'ı test et
    print("ModelLoader oluşturuldu")
    print("✓ ModelLoader testi başarılı")
    return True


def test_event_publisher():
    """EventPublisher testi"""
    print("\n=== EventPublisher Testi ===")
    
    ep = EventPublisher()
    
    # Event handler kaydet
    def handler(event):
        print(f"Event alındı: {event.type.value}")
    
    ep.dispatcher.register(EventType.PLUGIN_LOADED, handler)
    
    # Event yayını
    ep.publish(EventType.PLUGIN_LOADED, "test", {"test": "data"})
    
    print("✓ EventPublisher testi başarılı")
    return True


def test_api_response():
    """APIResponse testi"""
    print("\n=== APIResponse Testi ===")
    
    # Başarılı yanıt
    response = APIResponse(success=True, data={"key": "value"})
    print(f"JSON: {response.to_json()}")
    
    # Hata yanıt
    error_response = APIResponse(success=False, error="Test hatası")
    print(f"Hata JSON: {error_response.to_json()}")
    
    print("✓ APIResponse testi başarılı")
    return True


def test_health_check():
    """Health check testi"""
    print("\n=== Health Check Testi ===")
    
    pm = PluginManager(proxy_port=5000, api_port=8080)
    health = pm.health_check()
    
    print(f"Health status: {health.status}")
    print(f"Active plugins: {health.plugins_active}")
    print(f"Active models: {health.models_loaded}")
    
    print("✓ Health check testi başarılı")
    return True


def test_api_server():
    """API Server testi"""
    print("\n=== API Server Testi ===")
    
    pm = PluginManager(proxy_port=5000, api_port=8080)
    
    # API sunucusunu başlat
    pm.start_api_server()
    time.sleep(1)  # Sunucunun başlaması için bekle
    
    print("API sunucusu başlatıldı")
    
    # API sunucusunu durdur
    pm.stop_api_server()
    
    print("✓ API Server testi başarılı")
    return True


def test_hot_reload():
    """Hot-reload testi"""
    print("\n=== Hot-Reload Testi ===")
    
    pm = PluginManager(proxy_port=5000, api_port=8080)
    hrm = HotReloadManager(pm)
    
    # Hot-reload başlat
    hrm.start()
    time.sleep(1)
    
    print("Hot-reload başlatıldı")
    
    # Hot-reload durdur
    hrm.stop()
    
    print("✓ Hot-Reload testi başarılı")
    return True


def test_full_integration():
    """Tam entegrasyon testi"""
    print("\n=== Tam Entegrasyon Testi ===")
    
    pm = PluginManager(proxy_port=5000, api_port=8080)
    
    # Bileşenleri başlat
    pm.start_api_server()
    pm.start_watcher()
    
    print("Tüm bileşenler başlatıldı")
    
    # API sunucusunu durdur
    pm.stop_api_server()
    pm.stop_watcher()
    
    print("✓ Tam entegrasyon testi başarılı")
    return True


def main():
    """Tüm testleri çalıştır"""
    print("=" * 60)
    print("Plugin Sistemi Testleri")
    print("=" * 60)
    
    tests = [
        ("PluginManager", test_plugin_manager),
        ("ModelLoader", test_model_loader),
        ("EventPublisher", test_event_publisher),
        ("APIResponse", test_api_response),
        ("Health Check", test_health_check),
        ("API Server", test_api_server),
        ("Hot-Reload", test_hot_reload),
        ("Tam Entegrasyon", test_full_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} testi başarısız: {e}")
            results.append((name, False))
    
    # Özet
    print("\n" + "=" * 60)
    print("Test Özet")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nToplam: {passed}/{total} test başarılı")
    
    return all(r for _, r in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
