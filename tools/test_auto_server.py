#!/usr/bin/env python3
"""
MLX Otomatik Sunucusu Test Scripti
==================================

Bu script sunucunun calisip calismadigini test eder.
"""

import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8045"

def test_health():
    """Health endpoint testi"""
    print("1. Health endpoint testi...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"   Hata: {e}")
        return False

def test_status():
    """Status endpoint testi"""
    print("\n2. Status endpoint testi...")
    try:
        response = requests.get(f"{BASE_URL}/status")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"   Hata: {e}")
        return False

def test_ping():
    """Ping endpoint testi - modeli yukler"""
    print("\n3. Ping endpoint testi (model yukleme)...")
    try:
        response = requests.post(
            f"{BASE_URL}/generate",
            json={"type": "ping"},
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"   Hata: {e}")
        return False

def test_generate():
    """Generate endpoint testi"""
    print("\n4. Generate endpoint testi...")
    try:
        response = requests.post(
            f"{BASE_URL}/generate",
            json={
                "type": "generate",
                "prompt": "Merhaba, nasilsin?",
                "max_tokens": 100
            },
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"   Hata: {e}")
        return False

def test_unload():
    """Unload endpoint testi"""
    print("\n5. Unload endpoint testi (model silme)...")
    try:
        response = requests.post(
            f"{BASE_URL}/generate",
            json={"type": "unload"},
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"   Hata: {e}")
        return False

def main():
    print("=" * 60)
    print("MLX Otomatik Sunucu Testi")
    print("=" * 60)
    
    tests = [
        test_health,
        test_status,
        test_ping,
        test_generate,
        test_unload
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print(f"Sonuclar: {sum(results)}/{len(results)} test basarili")
    print("=" * 60)
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
