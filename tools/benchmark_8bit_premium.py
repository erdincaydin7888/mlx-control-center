import subprocess
import time
import os

# 8-Bit Model Yolu (Hub Alias Üzerinden)
MODEL_8BIT_PATH = "/Users/erdinc/.lmstudio/hub/models/qwen/qwen3-coder-next"

def run_test(tokens_in, tokens_out):
    print(f"\n[*] Test Parametresi: {tokens_in} giriş / {tokens_out} çıkış...")
    try:
        cmd = [
            "python3", "-m", "mlx_lm.benchmark",
            "--model", MODEL_8BIT_PATH,
            "--prompt-tokens", str(tokens_in),
            "--generation-tokens", str(tokens_out)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout
        
        if "generation_tps" in output:
            lines = output.strip().split("\n")
            # "Trial 1:" içeren son satırı bul
            trials = [l for l in lines if "Trial" in l]
            if trials:
                return trials[-1]
        return f"Hata: {result.stderr.strip() if result.stderr else 'Sonuç alınamadı'}"
        
    except Exception as e:
        return f"Hata: {str(e)}"

def main():
    print("="*60)
    print(" QWEN3-CODER-NEXT 8-BIT PREMIUM BENCHMARK ")
    print(" (Apple Studio - 512GB Unified Memory) ")
    print("="*60)
    
    # 1. Hızlı Sohbet/Kısa Kod Testi
    res_short = run_test(512, 256)
    
    # 2. Yoğun Kodlama/Geniş Bağlam Testi
    res_long = run_test(4096, 256)
    
    print("\n" + "="*60)
    print(" 8-BIT PERFORMANS RAPORU ")
    print("="*60)
    print(f"Kısa Bağlam (512t): {res_short}")
    print(f"Yoğun Bağlam (4k):  {res_long}")
    print("="*60)
    print("\n[BİLGİ] prompt_tps: Giriş kodlarını saniyede okuma hızı")
    print("[BİLGİ] generation_tps: Yeni kodu saniyede üretme hızı")
    print("============================================================")

if __name__ == "__main__":
    if os.path.exists(MODEL_8BIT_PATH):
        main()
    else:
        print(f"[!] Hata: {MODEL_8BIT_PATH} yolunda model dosyaları bulunamadı.")
