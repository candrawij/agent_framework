#!/usr/bin/env python3
"""Benchmark model performance (TPS, latency)"""
import time
import sys
sys.path.insert(0, ".")

from model_layer.adapters.ollama_adapter import OllamaAdapter

PROMPTS = [
    "Apa ibu kota Indonesia?",
    "Jelaskan konsep machine learning dalam 3 kalimat.",
    "Tulis fungsi Python untuk menghitung fibonacci.",
]

def benchmark(model_name: str, prompts: list):
    adapter = OllamaAdapter(model_name=model_name)
    print(f"\nBenchmarking: {model_name}")
    print("=" * 50)
    total_tokens = 0
    total_time = 0
    for i, prompt in enumerate(prompts, 1):
        start = time.time()
        result = adapter.complete([{"role": "user", "content": prompt}])
        elapsed = time.time() - start
        tokens = result.get("usage", {}).get("output_tokens", len(result.get("content","")) // 4)
        tps = tokens / elapsed if elapsed > 0 else 0
        print(f"  [{i}] {elapsed:.2f}s | {tokens} tokens | {tps:.1f} TPS")
        total_tokens += tokens
        total_time += elapsed
    avg_tps = total_tokens / total_time if total_time > 0 else 0
    print(f"  AVG: {total_time/len(prompts):.2f}s | {avg_tps:.1f} TPS")

if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:3b"
    benchmark(model, PROMPTS)
