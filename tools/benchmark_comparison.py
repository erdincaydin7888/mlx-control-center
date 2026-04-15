import time
import requests
import json
import subprocess
import os

# Configs
QWEN_PORT = 8080
GEMMA_PORT = 8081
QWEN_MODEL = "/Users/erdinc/.lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-MLX-4bit"
GEMMA_MODEL = "/Users/erdinc/.lmstudio/models/mlx-community/gemma-4-26b-a4b-it-4bit"

PROMPT = "Write a high-performance Python script to scrape a website and save data to a database. Explain each step clearly."

def get_perfect_stats(port, model_path):
    url = f"http://localhost:{port}/v1/chat/completions"
    print(f"[*] Testing {model_path.split('/')[-1]} on port {port}...")
    
    try:
        start_time = time.time()
        ttft = None
        token_count = 0
        final_usage = {}
        
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "messages": [{"role": "user", "content": PROMPT}],
                "model": model_path,
                "max_tokens": 512,
                "stream": True 
            },
            stream=True,
            timeout=300
        )
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data_str)
                        # Detect TTFT and Count Tokens
                        if chunk.get('choices'):
                            content = chunk['choices'][0].get('delta', {}).get('content')
                            if content:
                                if ttft is None:
                                    ttft = time.time() - start_time
                                token_count += 1 # Rough token approximation by chunk
                        
                        if chunk.get('usage'):
                            final_usage = chunk['usage']
                    except:
                        continue
        
        end_time = time.time()
        gen_duration = end_time - (start_time + (ttft or 0))
        
        # Stats Calculation
        effective_tokens = final_usage.get('output_tokens') or final_usage.get('completion_tokens', token_count)
        native_tps = final_usage.get('generation_tps')
        calculated_tps = effective_tokens / gen_duration if gen_duration > 0 else 0
        
        return {
            "tps": round(native_tps or calculated_tps, 2),
            "ttft": round(ttft * 1000, 2) if ttft else "N/A",
            "prompt_tps": round(final_usage.get('prompt_tps', 0), 2) if final_usage.get('prompt_tps') else "N/A",
            "memory": round(final_usage.get('peak_memory', 0), 2) if final_usage.get('peak_memory') else "N/A",
            "status": "success"
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}

def run_perfect_comparison():
    print("\n🚀 Apple Silicon MLX Gelişmiş Benchmark Karşılaştırması Başlıyor...\n")
    
    # 1. Test Qwen3-30B
    qwen_results = get_perfect_stats(QWEN_PORT, QWEN_MODEL)
    
    # 2. Test Gemma 4 26B MoE
    gemma_results = get_perfect_stats(GEMMA_PORT, GEMMA_MODEL)
    
    print("\n" + "="*90)
    header = f"{'Gelişmiş Metrikler':<30} | {'Qwen3-30B (Dense)':<25} | {'Gemma 4 (MoE)':<25}"
    print(header)
    print("-" * 90)
    
    print(f"{'Üretim Hızı (TPS)':<30} | {qwen_results.get('tps', 0):<25} | {gemma_results.get('tps', 0):<25}")
    print(f"{'İlk Kelime Gecikmesi (TTFT)':<30} | {qwen_results.get('ttft', 'N/A'):<25} | {gemma_results.get('ttft', 'N/A'):<25}")
    print(f"{'Prompt İşleme Hızı (PPS)':<30} | {qwen_results.get('prompt_tps', 'N/A'):<25} | {gemma_results.get('prompt_tps', 'N/A'):<25}")
    print(f"{'Bellek Kullanımı (VRAM)':<30} | {qwen_results.get('memory', 'N/A'):<25} | {gemma_results.get('memory', 'N/A'):<25}")
    
    print("="*90)
    
    tps_q = qwen_results.get('tps', 0)
    tps_g = gemma_results.get('tps', 0)
    
    if tps_g > tps_q:
        print(f"\n🏆 VERİMLİLİK ŞAMPİYONU: Gemma 4 MoE (Gemma 4 %{round((tps_g/tps_q-1)*100,1)} daha hızlı)")
    else:
        print(f"\n🏆 GÜÇ ŞAMPİYONU: Qwen3-30B (Qwen3 %{round((tps_q/tps_g-1)*100,1)} daha hızlı)")

if __name__ == "__main__":
    run_perfect_comparison()
