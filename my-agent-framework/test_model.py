#!/usr/bin/env python3
"""
test_model.py — Sprint 1a: Qwen Connector Validation Script

Usage:
    python test_model.py --prompt "Halo siapa kamu?"
    python test_model.py --prompt "Tulis kode Python untuk fibonacci" --model qwen2.5-coder:7b
    python test_model.py --stream
    python test_model.py --health

Success criteria (Sprint 1a):
    Model menjawab dan token muncul secara streaming di terminal.
    Tidak ada crash, tidak ada timeout.
"""

import argparse
import sys
import time

sys.path.insert(0, ".")


def check_health(adapter) -> bool:
    print("[Health] Memeriksa koneksi Ollama...")
    try:
        ok = adapter.check_health()
        if ok:
            print("[Health] Ollama OK - dapat dijangkau")
        else:
            print("[Health] GAGAL - Ollama tidak dapat dijangkau")
            print("         Jalankan: ollama serve")
        return ok
    except Exception as e:
        print(f"[Health] ERROR: {e}")
        return False


def list_models(adapter) -> list:
    try:
        models = adapter.get_available_models(use_cache=False)
        if models:
            print(f"\n[Models] Model yang tersedia ({len(models)}):")
            for m in models:
                print(f"  - {m}")
        else:
            print("\n[Models] Tidak ada model yang terinstall")
            print("         Jalankan: ollama pull qwen2.5:3b")
        return models
    except Exception as e:
        print(f"[Models] ERROR: {e}")
        return []


def run_complete(adapter, prompt: str, model_name: str = None) -> dict:
    """Non-streaming complete — satu prompt, satu response."""
    print(f"\n[Complete] Prompt: {prompt!r}")
    print(f"[Complete] Model: {model_name or adapter.model_name}")
    print("-" * 50)

    start = time.time()
    result = adapter.complete(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        model_override=model_name,
    )
    elapsed = time.time() - start

    content = result.get("content", "")
    model_used = result.get("model", "?")
    usage = result.get("usage", {})

    print(content)
    print("-" * 50)
    print(f"[Stats] Model: {model_used}")
    print(f"[Stats] Elapsed: {elapsed:.2f}s")
    if usage:
        out_tokens = usage.get("output_tokens", 0)
        if out_tokens and elapsed > 0:
            print(f"[Stats] Tokens: {out_tokens} ({out_tokens/elapsed:.1f} TPS)")
    return result


def run_stream(adapter, prompt: str, model_name: str = None):
    """Streaming — cetak token per token ke stdout."""
    print(f"\n[Stream] Prompt: {prompt!r}")
    print(f"[Stream] Model: {model_name or adapter.model_name}")
    print("-" * 50)

    start = time.time()
    token_count = 0

    from model_layer.adapters.ollama_adapter import TaskType
    for token in adapter.stream(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        model_override=model_name,
    ):
        print(token, end="", flush=True)
        token_count += 1

    elapsed = time.time() - start
    print()
    print("-" * 50)
    print(f"[Stats] Elapsed: {elapsed:.2f}s | Tokens: ~{token_count}")


def run_benchmark(adapter):
    """Quick benchmark — 3 prompt, ukur latency dan TPS."""
    prompts = [
        "Apa ibu kota Indonesia? Jawab singkat.",
        "Jelaskan apa itu list comprehension di Python dalam 2 kalimat.",
        "Sebutkan 3 keunggulan model transformer.",
    ]

    print(f"\n[Benchmark] {len(prompts)} prompts...")
    print("-" * 50)

    total_elapsed = 0
    total_tokens = 0
    for i, prompt in enumerate(prompts, 1):
        start = time.time()
        result = adapter.complete([{"role": "user", "content": prompt}], max_tokens=150)
        elapsed = time.time() - start
        content = result.get("content", "")
        tokens = result.get("usage", {}).get("output_tokens", len(content) // 4)
        tps = tokens / elapsed if elapsed > 0 else 0
        total_elapsed += elapsed
        total_tokens += tokens
        print(f"  [{i}] {elapsed:.2f}s | ~{tokens}t | {tps:.0f} TPS | {content[:60]!r}...")

    avg_tps = total_tokens / total_elapsed if total_elapsed > 0 else 0
    print(f"\n[Benchmark] Total: {total_elapsed:.1f}s | Avg TPS: {avg_tps:.0f}")


def main():
    parser = argparse.ArgumentParser(
        description="Test Model Connector (Sprint 1a — Qwen Connector Validation)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_model.py --prompt "Halo siapa kamu?"
  python test_model.py --prompt "Tulis fibonacci Python" --stream
  python test_model.py --model qwen3:4b --prompt "Analisis ini..."
  python test_model.py --health
  python test_model.py --list-models
  python test_model.py --benchmark
        """,
    )
    parser.add_argument("--prompt", "-p", type=str, help="Prompt yang dikirim ke model")
    parser.add_argument("--model", "-m", type=str, help="Override model name (misal: qwen3:4b)")
    parser.add_argument("--stream", "-s", action="store_true", help="Gunakan streaming mode")
    parser.add_argument("--health", action="store_true", help="Cek koneksi Ollama")
    parser.add_argument("--list-models", action="store_true", help="List model yang tersedia")
    parser.add_argument("--benchmark", action="store_true", help="Jalankan quick benchmark")
    parser.add_argument("--base-url", type=str, default="http://localhost:11434", help="Ollama base URL")

    args = parser.parse_args()

    # Default prompt jika tidak ada argumen
    if not any([args.prompt, args.health, args.list_models, args.benchmark]):
        args.prompt = "Halo, siapa kamu?"
        args.stream = True

    print("=" * 50)
    print("  Agent Framework — Model Connector Test")
    print("  Sprint 1a: Qwen Connector Validation")
    print("=" * 50)

    # Import adapter
    try:
        from model_layer.adapters.ollama_adapter import OllamaAdapter
        adapter = OllamaAdapter(
            model_name=args.model or "qwen2.5:3b",
            base_url=args.base_url,
        )
        print(f"[Init] OllamaAdapter @ {args.base_url}")
    except ImportError as e:
        print(f"[ERROR] Gagal import OllamaAdapter: {e}")
        print("        Pastikan kamu menjalankan dari folder my-agent-framework/")
        sys.exit(1)

    # Health check
    if args.health or not args.prompt:
        healthy = check_health(adapter)
        if not healthy:
            sys.exit(1)

    # List models
    if args.list_models:
        list_models(adapter)

    # Benchmark
    if args.benchmark:
        run_benchmark(adapter)

    # Run prompt
    if args.prompt:
        if not check_health(adapter):
            print("\n[ERROR] Ollama tidak tersedia. Jalankan: ollama serve")
            sys.exit(1)

        if args.stream:
            run_stream(adapter, args.prompt, args.model)
        else:
            run_complete(adapter, args.prompt, args.model)

    print("\n[Done] Sprint 1a test selesai!")


if __name__ == "__main__":
    main()
