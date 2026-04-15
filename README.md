# MLX Control Center

A modern, fast, and feature-rich React/HTML Dashboard to control and manage Apple Silicon MLX Language Models via HTTP Proxy.

## Features

* **Visual Model Scanner:** Automatically scans `~/.lmstudio/models` (or your configured path) for any `.safetensors`, `.gguf`, etc. format files.
* **Intelligent HW Checker:** Evaluates memory limits and model parameter size (quantization) to check if the model fits. Features an optimized VRAM estimation logic for high-context models.
* **Consolidated Automation Tools:** Now includes a full suite of automation scripts (`automation/`) and benchmarking tools (`tools/`) directly in the repository.
* **Integrated HW Monitor:** Displays system RAM and CPU compute metrics in real time, now elegantly integrated into the top-left header.
* **Modern AI Prompt Box:** High-fidelity glassmorphic chat interface with Search, Think, Canvas modes, and Voice/Image support.
* **Instant Start & Switch:** Launch or swap MLX models instantly without typing terminal commands. 
* **Lightweight:** Uses raw HTML/JS for frontend and FastAPI for backend, no `node_modules` overhead.

---

# MLX Kontrol Merkezi (Turkish)

Apple Silicon MLX tabanlı Doğal Dil İşleme (LLM) modellerini HTTP Proxy üzerinden yönetmek, izlemek ve kontrol etmek için tasarlanmış modern, hızlı ve yetenekli bir kontrol paneli.

## Özellikler

* **Görsel Model Tarayıcı:** Yapılandırılmış veya standart dizinlerdeki modelleri otomatik bulur.
* **Akıllı Donanım Testi:** Model parametreleri ve bit formatına göre Mac belleğine uyumluluğu ölçer. Yüksek context'li modeller için optimize edilmiş VRAM tahminleme mantığına sahiptir.
* **Konsolide Araç Seti:** Tüm otomasyon betikleri (`automation/`) ve benchmark araçları (`tools/`) artık tek bir çatı altında deponun içindedir.
* **Entegre Sistem İzleme:** Sistem RAM ve CPU durumlarını canlı olarak doğrudan başlık alanında (sol üst) gösterir.
* **Modern AI Mesaj Kutusu:** Search, Think, Canvas modları ile Sesli/Görsel girdi desteği barındıran premium sohbet arayüzü.
* **Hızlı Başlat ve Değiştir:** Modelleri konsola kod yazmadan hemen aktif edebilir veya anında değiştirebilirsiniz.
* **Hafif Çekirdek:** FastAPI ve saf HTML+Javascript kullanır, derleme süreci barındırmaz.

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
