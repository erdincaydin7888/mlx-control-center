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
    Apple Silicon için optimize edilmiştir.
    """
    stats = get_system_stats()
    
    # 1. Model Ağırlıkları (Weights) - Temel VRAM ihtiyacı
    weight_vram = param_count_billions * (quantization_bits / 8.0)
    
    # 2. KV Cache & Context Overhead
    # ÖNEMLİ: Uyumluluk kontrolü için modelin desteklediği MAKSİMUM context (örn 262k) değil,
    # gerçekçi bir başlangıç context'i (örn 8192) baz alınır. 
    base_context = min(context_length, 8192) if context_length > 0 else 4096
    
    # MLX tabanlı kaba KV Cache formülü
    kv_vram = (base_context / 1024) * (param_count_billions / 10) * 0.08
    
    total_estimated_vram = weight_vram + kv_vram
    
    # Apple Silicon'da VRAM = Unified Memory
    # macOS her zaman RAM'in bir kısmını sisteme ayırır (kablolu bellek).
    # Sistemin güvenli üst sınırı toplam RAM'in %90'ıdır.
    safe_ram_limit = stats.total_memory_gb * 0.90
    
    can_run = total_estimated_vram <= safe_ram_limit
    
    # Hız (Speed Tier) Tahmini - Apple M-Series bellek bant genişliği dinamik aralığı
    bandwidth_gb_s = 250.0 
    
    # Tek tokende okunması gereken veri (MoE ise sadece aktif expertler)
    if is_moe:
        # MoE'de her adımda sadece aktif expertlerin parametreleri okunur.
        # 30B MoE modelinde genellikle ~3-5B arası veri akar.
        active_ratio = 0.15 
        active_weight_gb = weight_vram * active_ratio
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
        bottleneck = "RAM Kapasitesi"
        msg = f"Model ({total_estimated_vram:.1f} GB) sistemin fiziksel bellek kapasitesini ({stats.total_memory_gb:.1f} GB) zorluyor."
    elif total_estimated_vram > stats.free_memory_gb:
        bottleneck = "Boş RAM"
        msg = f"Model çalışabilir ancak şu anki boş RAM ({stats.free_memory_gb:.1f} GB) yetersiz. Arka planda çalışan uygulamaları kapatın."
    else:
        bottleneck = "Yok"
        msg = "Sistem bu modeli rahatlıkla çalıştırabilir."
        
    # Maksimum sığabilecek context hesabı
    remaining_ram = safe_ram_limit - weight_vram
    max_ctx = int((remaining_ram / (kv_vram / base_context))) if kv_vram > 0 and remaining_ram > 0 else base_context

    return CompatibilityResult(
        can_run=can_run,
        estimated_vram_gb=round(total_estimated_vram, 2),
        free_ram_gb=stats.free_memory_gb,
        total_ram_gb=stats.total_memory_gb,
        max_context_fit=max_ctx,
        speed_tier=speed,
        bottleneck=bottleneck,
        message=msg
    )
