import subprocess
import json
import time

# Model Yolları
MODEL_NEXT_PATH = "/Users/erdinc/.lmstudio/models/mlx-community/Qwen3-Coder-Next-5bit"
MODEL_30B_PATH = "/Users/erdinc/.lmstudio/hub/models/qwen/qwen3-coder-30b"

def run_benchmark(model_path, prompt_tokens=64, generation_tokens=256):
    print(f"\n[*] {model_path.split('/')[-1]} için test başlatılıyor...")
    try:
        # MLX Benchmark komutunu çalıştır (Subprocess ile)
        cmd = [
            "python3", "-m", "mlx_lm.benchmark",
            "--model", model_path,
            "--prompt-tokens", str(prompt_tokens),
            "--generation-tokens", str(generation_tokens)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Çıktıdan verileri ayıkla (Örn: Trial 1:  prompt_tps=408.998, generation_tps=53.991)
        output = result.stdout
        if "generation_tps" in output:
            # Basit bir parser: Son trial verilerini alalım
            lines = output.strip().split("\n")
            last_trial = [l for l in lines if "Trial" in l][-1]
            return last_trial
        else:
            return f"Hata: {result.stderr.strip() if result.stderr else 'Model yüklenemedi'}"
            
    except Exception as e:
        return f"Beklenmedik hata: {str(e)}"

def main():
    print("="*60)
    print(" QWEN CODER BENCHMARK COMPARISON ")
    print("="*60)
    
    # Testleri Koş
    res_next = run_benchmark(MODEL_NEXT_PATH)
    res_30b = run_benchmark(MODEL_30B_PATH)
    
    # Sonuç Raporu
    print("\n" + "="*60)
    print(" BENCHMARK SONUÇLARI ")
    print("="*60)
    print(f"Qwen Coder Next (5bit):  {res_next}")
    print(f"Qwen Coder 30B (4bit):    {res_30b}")
    print("="*60)
    print("\n[İPUCU] prompt_tps = Giriş anlama hızı | generation_tps = Yazma hızı")
    print("Apple Studio'da MoE modeller (Next) genellikle daha dengeli bir hız sunar.")

if __name__ == "__main__":
    main()
