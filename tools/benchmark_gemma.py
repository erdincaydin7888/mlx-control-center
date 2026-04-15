import time
import requests
import json
import subprocess
import os

# Config
GEMMA_PORT = 8081
GEMMA_MODEL_PATH = "/Users/erdinc/.lmstudio/models/mlx-community/gemma-4-26b-a4b-it-4bit"
PROMPT = "Write a high-performance Python script to scrape a website and save data to a database. Explain each step clearly."

def test_mlx_native():
    print(f"[*] Testing Gemma 4 (MoE) using mlx-vlm on port {GEMMA_PORT}...")
    
    server_url = f"http://localhost:{GEMMA_PORT}/v1/chat/completions"
    try:
        requests.get(f"http://localhost:{GEMMA_PORT}/v1/models", timeout=2)
    except:
        print("[!] mlx-vlm server not found. Starting Gemma 4 26B MoE...")
        subprocess.Popen(
            ["mlx_vlm.server", "--model", GEMMA_MODEL_PATH, "--port", str(GEMMA_PORT)],
            stdout=open("/tmp/gemma_server.log", "w"),
            stderr=subprocess.STDOUT
        )
        print("[*] Model yükleniyor...")
        for i in range(60):
            try:
                requests.get(f"http://localhost:{GEMMA_PORT}/v1/models", timeout=2)
                print(" [HAZIR]")
                break
            except:
                time.sleep(2)
    
    print("[*] İstek gönderiliyor...")
    response = requests.post(
        server_url,
        headers={"Content-Type": "application/json"},
        json={
            "messages": [{"role": "user", "content": PROMPT}],
            "model": GEMMA_MODEL_PATH,
            "max_tokens": 512,
            "stream": False
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        usage = data.get('usage', {})
        # mlx-vlm specific fields
        tps = usage.get('generation_tps', 0)
        tokens = usage.get('output_tokens', 0)
        memory = usage.get('peak_memory', 0)
        
        return {
            "tps": round(tps, 2),
            "tokens": tokens,
            "memory": round(memory, 2)
        }
    else:
        return {"error": f"Status {response.status_code}"}

if __name__ == "__main__":
    results = test_mlx_native()
    print("\n" + "="*50)
    print("GEMMA 4 26B MoE (mlx-vlm) - PERFORMANCE RESULTS")
    print("="*50)
    if "error" in results:
        print(f"Error: {results['error']}")
    else:
        print(f"TPS (Tokens Per Second): {results['tps']} tok/sn")
        print(f"Total Output Tokens: {results['tokens']} tokens")
        print(f"Peak Memory Usage: {results['memory']} GB")
    print("="*50)
