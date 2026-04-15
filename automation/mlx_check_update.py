#!/usr/bin/env python3
import urllib.request
import json
import pkg_resources
import sys

def check_mlx():
    package = "mlx-lm"
    try:
        # Get current installed version
        current_version = pkg_resources.get_distribution(package).version
        
        # Get latest version from PyPI
        url = f"https://pypi.org/pypi/{package}/json"
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode())
            latest_version = data["info"]["version"]
        
        print(f"\033[1;34m[MLX-CHECK]\033[0m Mevcut: \033[1;32m{current_version}\033[0m | En Yeni: \033[1;33m{latest_version}\033[0m")
        
        if current_version != latest_version:
            print(f"\033[1;31m[!]\033[0m Yeni bir MLX sürümü mevcut! Güncellemek isterseniz: \033[1;36mpip install -U {package}\033[0m")
            print("\033[1;33mNot:\033[0m Güncelleme sonrası sunucu yamalarımızı kontrol etmeyi unutmayın.")
        else:
            print("\033[1;32m[✔]\033[0m MLX kütüphaneniz şu an en güncel sürümde.")
            
    except Exception as e:
        print(f"\033[1;31m[HATA]\033[0m Kontrol yapılamadı (İnternet bağlantısını kontrol edin).")

if __name__ == "__main__":
    check_mlx()
