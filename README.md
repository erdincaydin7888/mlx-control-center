# MLX Control Center

A modern, fast, and feature-rich React/HTML Dashboard to control and manage Apple Silicon MLX Language Models via HTTP Proxy.

## Features

* **Visual Model Scanner:** Automatically scans `~/.lmstudio/models` (or your configured path) for any `.safetensors`, `.gguf`, etc. format files.
* **Intelligent HW Checker:** Evaluates memory limits and model parameter size (quantization) to check if the model fits Apple Silicon.
* **Core MLX Scripts Attached:** Comes out of the box with the core MLX Proxy and patched Server. You do *not* need to rely on external MLX repos.
* **Instant Start & Switch:** Launch or swap MLX models instantly without typing terminal commands. 
* **Real-time Metrics:** Displays system RAM and CPU compute metrics in real time.
* **In-Dashboard Chat:** Communicate via the standard `v1/chat/completions` REST API right inside the dashboard.
* **Lightweight:** Uses raw HTML/JS for frontend and FastAPI for backend, no `node_modules` overhead.

---

# MLX Kontrol Merkezi (Turkish)

Apple Silicon MLX tabanlı Doğal Dil İşleme (LLM) modellerini HTTP Proxy üzerinden yönetmek, izlemek ve kontrol etmek için tasarlanmış modern, hızlı ve yetenekli bir kontrol paneli.

## Özellikler

* **Görsel Model Tarayıcı:** Yapılandırılmış veya standart `~/.lmstudio/models` dizinindeki modelleri (Örn: `.safetensors`, `.gguf`) otomatik bulur.
* **Akıllı Donanım Testi:** Model parametreleri ve bit formatına göre (quantization) Mac belleğine sığıp sığmayacağını size önden söyler.
* **Dahili MLX Betikleri:** Gelişmiş MLX API proxy ve sunucu betikleri projenin içindedir, dış bağımlılıklara ihtiyaç duymaz.
* **Hızlı Başlat ve Değiştir:** Modelleri konsola kod yazmadan hemen aktif edebilir veya anında değiştirebilirsiniz.
* **Canlı Metrikler:** Sisteminizin o anki RAM ve CPU durumlarını canlı olarak grafiklerle gösterir.
* **Dashboard İçi Sohbet:** Başlattığınız modele `v1/chat/completions` API altyapısı kullanarak hemen test amaçlı mesaj atıp yanıt alabilirsiniz.
* **Hafif Çekirdek:** Sadece FastAPI (Python) ve saf HTML+Javascript kullanır, Node.js veya kompleks derleme süreçleri barındırmaz.

## 🚀 Quick Start / Hızlı Başlangıç

### 1- Install Requirements / Gereksinimleri Yükleyin
```bash
git clone https://github.com/erdincaydin7888/mlx-control-center.git
cd mlx-control-center
pip install -r requirements.txt
```

### 2- Run Dashboard / Arayüzü Başlatın 
```bash
python3 run.py
```
> Sonrasında tarayıcınızdan **http://127.0.0.1:8070** bağlantısına gidebilirsiniz.

### 3- Configuration / Yapılandırma (Optional)
MLX modellerinizin farklı bir dizinde olduğunu belirtmek için sistem çevresel değişkeni (environment variable) kullanabilirsiniz:

```bash
export MLX_MODELS_DIR="/Users/your_user/OtherPath"
python3 run.py
```

## Architecture / Mimari

- **FastAPI Backend (`backend/`)**: Serves the API, reads system metrics, handles WebSockets, and controls Python sub-processes.
- **HTML Frontend (`frontend/index.html`)**: The monolithic modern user interface combining HTML, vanilla CSS, and basic vanilla JS logic.
- **Core Engine (`backend/core/`)**: Includes the advanced MLX patching server and proxy logic originally developed to enhance the native MLX local runs.
