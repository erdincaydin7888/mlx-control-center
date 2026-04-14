"""MLX Dashboard — Hardware Compatibility Checker.

Github'daki 'whichllm' ve 'CanIRunThisLLM' projelerinin arkasındaki
VRAM ve Donanım Uyumluluk formüllerini içeren modül.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .system_monitor import get_system_stats

@dataclass
class CompatibilityResult:
    can_run: bool
    estimated_vram_gb: float
    free_ram_gb: float
    total_ram_gb: float
    max_context_fit: int
    speed_tier: str  # "Çok Hızlı", "Hızlı", "Orta", "Yavaş"
    bottleneck: str
    message: str

def calculate_compatibility(
    param_count_billions: float,
    quantization_bits: float = 8.0,
    context_length: int = 4096,
    is_moe: bool = False,
    active_experts: int = 2
) -> CompatibilityResult:
    """
    Modelin donanımda çalışıp çalışmayacağını ve performansını tahmin eder.
    Formül: (Parametreler_milyar * (Bit/8)) * Overhead
    MoE ise aktif expertler üzerinden aktif bellek bant genişliği hesaplanır.
    """
    stats = get_system_stats()
    
    # 1. Model Ağırlıkları (Weights)
    weight_vram = param_count_billions * (quantization_bits / 8.0)
    
    # 2. KV Cache & Context Overhead (Kaba tahmin: ~1.2 çarpan veya context bazlı)
    # Context başına kabaca GB hesabı (model model değişir ama basit tutuyoruz)
    # 100k context = ~8-15GB modeline göre. Biz 4096 için küçük bir overhead ekliyoruz.
    kv_vram = (context_length / 1024) * (param_count_billions / 10) * 0.1
    
    total_estimated_vram = weight_vram + kv_vram
    
    # Apple Silicon'da VRAM = Unified Memory
    # macOS her zaman RAM'in bir kısmını sisteme ayırır (kablolu bellek).
    max_usable_ram = stats.total_memory_gb * 0.85  # %85'i MLX için güvenli sınır
    
    can_run = total_estimated_vram <= max_usable_ram
    
    # Hız (Speed Tier) Tahmini - Apple M3 Ultra bellek bant genişliği: 800 GB/s
    bandwidth_gb_s = 800.0
    
    # Tek tokende okunması gereken veri (MoE ise sadece aktif expertler)
    if is_moe:
        # Toplam VRAM yüksek olsa da okunacak weight sadece aktif expertler kadardır.
        active_params = param_count_billions * (active_experts / (param_count_billions / active_experts)) # Sadece bir oran tahmini
        active_weight_gb = weight_vram * 0.25 # Kaba tahmin: MoE iterasyonunda ağırlıkların %25'i
    else:
        active_weight_gb = weight_vram
        
    estimated_tps = bandwidth_gb_s / (active_weight_gb if active_weight_gb > 0 else 1)
    
    if estimated_tps > 80:
        speed = "⚡ Çok Hızlı (>80 t/s)"
    elif estimated_tps > 30:
        speed = "🚀 Hızlı (30-80 t/s)"
    elif estimated_tps > 10:
        speed = "🏃 Orta (10-30 t/s)"
    else:
        speed = "🐢 Yavaş (<10 t/s)"
        
    if not can_run:
        bottleneck = "RAM Yetersiz"
        msg = f"Model ({total_estimated_vram:.1f} GB) sistemin güvenli bellek limitini ({max_usable_ram:.1f} GB) aşıyor."
    elif total_estimated_vram > stats.free_memory_gb:
        bottleneck = "Mevcut RAM"
        msg = f"Model çalışabilir ancak şu anki boş RAM ({stats.free_memory_gb:.1f} GB) yetersiz. Arka planda çalışan uygulamaları kapatın."
    else:
        bottleneck = "Yok"
        msg = "Sistem bu modeli rahatlıkla çalıştırabilir."
        
    return CompatibilityResult(
        can_run=can_run,
        estimated_vram_gb=round(total_estimated_vram, 2),
        free_ram_gb=stats.free_memory_gb,
        total_ram_gb=stats.total_memory_gb,
        max_context_fit=int(((max_usable_ram - weight_vram) / (kv_vram / context_length))) if (kv_vram > 0 and max_usable_ram > weight_vram) else context_length,
        speed_tier=speed,
        bottleneck=bottleneck,
        message=msg
    )
