import time
import argparse
import psutil
import os
import json
import requests

def get_memory_usage():
    """Sistemin o anki RAM kullanımını (MB) döner."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def benchmark_mlx(model_path, prompt, max_tokens):
    import mlx.core as mx
    is_vlm = "-vl" in model_path.lower()
    
    start_mem = get_memory_usage()
    
    if is_vlm:
        try:
            from mlx_vlm import load, generate
            from mlx_vlm.utils import generate_step
            print("\n📸 VLM (Vision-Language) Modeli algılandı...")
        except ImportError:
            print("❌ mlx-vlm bulunamadı.")
            return None
    else:
        try:
            from mlx_lm import load, generate
            from mlx_lm.generate import generate_step
        except ImportError:
            print("❌ mlx-lm bulunamadı.")
            return None

    print(f"--- 🍏 Apple MLX Framework: {model_path} ---")
    print("Model yükleniyor...")
    start_load = time.time()
    try:
        model, tokenizer = load(model_path)
    except Exception as e:
        print(f"Hata: {e}")
        return None
    
    load_time = time.time() - start_load
    print(f"Yüklendi ({load_time:.2f}s)")
    
    proc = tokenizer.tokenizer if hasattr(tokenizer, 'tokenizer') else tokenizer
    prompt_tokens = proc.encode(prompt)
    prompt_len = len(prompt_tokens)

    # Warmup
    generate(model, tokenizer, prompt="Hi", max_tokens=5, verbose=False)
    
    start_time = time.time()
    ttft = None
    tokens = []
    
    try:
        input_ids = mx.array(prompt_tokens)
        for i, token in enumerate(generate_step(input_ids, model)):
            if i == 0:
                ttft = time.time() - start_time
            if i >= max_tokens:
                break
            tokens.append(token)
    except Exception as e:
        print(f"Üretim hatası: {e}")
        return None
        
    end_time = time.time()
    total_duration = end_time - start_time
    gen_duration = end_time - (start_time + ttft) if ttft else total_duration
    
    tps = len(tokens) / gen_duration if gen_duration > 0 else 0
    prompt_tps = prompt_len / ttft if ttft and ttft > 0 else 0
    end_mem = get_memory_usage()
    
    result = {
        "ttft": ttft,
        "tps": tps,
        "prompt_tps": prompt_tps,
        "total_duration": total_duration,
        "tokens": len(tokens),
        "peak_mem": end_mem,
        "prompt_len": prompt_len
    }
    return result

def benchmark_lm_studio(prompt, max_tokens, prompt_len):
    try:
        import openai
    except ImportError:
        return None

    client = openai.OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    
    try:
        models = client.models.list()
        if not models.data: return None
        model_name = models.data[0].id
    except:
        return None

    print(f"\n--- 🤖 LM Studio (MLX Engine): {model_name} ---")
    
    start_time = time.time()
    ttft = None
    token_count = 0
    
    try:
        stream = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.0,
            stream=True
        )
        
        for chunk in stream:
            if ttft is None:
                ttft = time.time() - start_time
            if chunk.choices[0].delta.content:
                token_count += 1
                
    except Exception as e:
        print(f"LM Studio Hatası: {e}")
        return None
        
    end_time = time.time()
    total_duration = end_time - start_time
    gen_duration = end_time - (start_time + ttft) if ttft else total_duration
    tps = token_count / gen_duration if gen_duration > 0 else 0
    prompt_tps = prompt_len / ttft if ttft and ttft > 0 else 0
    
    return {
        "ttft": ttft,
        "tps": tps,
        "prompt_tps": prompt_tps,
        "total_duration": total_duration,
        "tokens": token_count,
        "model_name": model_name
    }

def benchmark_ollama(model_name, prompt, max_tokens, prompt_len):
    print(f"\n--- 🥇 Ollama (Llama.cpp Engine): {model_name} ---")
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0
        }
    }
    
    start_time = time.time()
    ttft = None
    token_count = 0
    
    try:
        response = requests.post(url, json=payload, stream=True)
        for line in response.iter_lines():
            if line:
                if ttft is None:
                    ttft = time.time() - start_time
                
                data = json.loads(line)
                if not data.get("done"):
                    token_count += 1
                else:
                    # Ollama'nın kendi istatistiklerini de alabiliriz
                    # data["eval_count"] / (data["eval_duration"] / 1e9)
                    pass
    except Exception as e:
        print(f"Ollama Hatası: {e}")
        return None

    end_time = time.time()
    total_duration = end_time - start_time
    gen_duration = end_time - (start_time + ttft) if ttft else total_duration
    tps = token_count / gen_duration if gen_duration > 0 else 0
    prompt_tps = prompt_len / ttft if ttft and ttft > 0 else 0

    return {
        "ttft": ttft,
        "tps": tps,
        "prompt_tps": prompt_tps,
        "total_duration": total_duration,
        "tokens": token_count
    }

def print_triple_table(mlx, lms, oll, mlx_model_name, oll_model_name):
    m_name = os.path.basename(mlx_model_name)[:20]
    l_name = lms['model_name'][:20]
    o_name = oll_model_name[:20]

    print("\n" + "╔" + "═"*114 + "╗")
    print(f"║ {'🚀 ÜÇLÜ DEV KARŞILAŞTIRMA (MLX vs LM STUDIO vs OLLAMA)':^112} ║")
    print("╠" + "═"*27 + "╦" + "═"*22 + "╦" + "═"*22 + "╦" + "═"*22 + "╦" + "═"*15 + "╣")
    print(f"║ {'PLATFORM':<25} ║ {'APPLE MLX':^20} ║ {'LM STUDIO':^20} ║ {'OLLAMA':^20} ║ {'LİDER':^13} ║")
    print(f"║ {'(MODEL)':<25} ║ ({m_name:^18}) ║ ({l_name:^18}) ║ ({o_name:^18}) ║ {'':^13} ║")
    print("╠" + "═"*27 + "╬" + "═"*22 + "╬" + "═"*22 + "╬" + "═"*22 + "╬" + "═"*15 + "╣")
    
    def get_winner(m, l, o, lower_is_better=False):
        vals = [v for v in [m, l, o] if v is not None]
        if not vals: return "-"
        winner_val = min(vals) if lower_is_better else max(vals)
        if winner_val == m: return "🏆 MLX"
        if winner_val == l: return "🏆 LMS"
        return "🏆 OLL"

    metrics = [
        ("Üretim Hızı (TPS)", f"{mlx['tps']:.2f} tok/s", f"{lms['tps']:.2f} tok/s", f"{oll['tps']:.2f} tok/s", get_winner(mlx['tps'], lms['tps'], oll['tps'])),
        ("İlk Token (Gecikme)", f"{mlx['ttft']:.3f} s", f"{lms['ttft']:.3f} s", f"{oll['ttft']:.3f} s", get_winner(mlx['ttft'], lms['ttft'], oll['ttft'], True)),
        ("Prompt Analizi", f"{mlx['prompt_tps']:.1f} tok/s", f"{lms['prompt_tps']:.1f} tok/s", f"{oll['prompt_tps']:.1f} tok/s", get_winner(mlx['prompt_tps'], lms['prompt_tps'], oll['prompt_tps'])),
        ("Toplam Süre", f"{mlx['total_duration']:.2f} s", f"{lms['total_duration']:.2f} s", f"{oll['total_duration']:.2f} s", "-"),
        ("Üretilen Token", f"{mlx['tokens']}", f"{lms['tokens']}", f"{oll['tokens']}", "-"),
    ]
    
    for label, m, l, o, winner in metrics:
        print(f"║ {label:<25} ║ {m:^20} ║ {l:^20} ║ {o:^20} ║ {winner:^13} ║")
    
    print("╚" + "═"*27 + "╩" + "═"*22 + "╩" + "═"*22 + "╩" + "═"*22 + "╩" + "═"*15 + "╝\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mlx-model", type=str, required=True)
    parser.add_argument("--ollama-model", type=str, default="qwen3-coder:30b")
    parser.add_argument("--tokens", type=int, default=150)
    args = parser.parse_args()

    test_prompt = "Python'da asenkron programlamanın mantığını 3 madde ile açıklar mısın?"
    
    print("\n🔥 Test Başlatılıyor, Lütfen Bekleyin...\n")
    
    mlx_res = benchmark_mlx(args.mlx_model, test_prompt, args.tokens)
    if not mlx_res: sys.exit(1)
    
    p_len = mlx_res['prompt_len']
    lms_res = benchmark_lm_studio(test_prompt, args.tokens, p_len)
    oll_res = benchmark_ollama(args.ollama_model, test_prompt, args.tokens, p_len)
    
    if mlx_res and lms_res and oll_res:
        print_triple_table(mlx_res, lms_res, oll_res, args.mlx_model, args.ollama_model)
    else:
        print("Hata: Bazı servislerden veri alınamadı. (LM Studio veya Ollama açık mı?)")
