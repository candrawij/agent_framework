"""
tokenizer_utils.py — Utilitas Token Counting

Helper functions untuk menghitung token tanpa dependency berat.
"""

def count_tokens(text: str) -> int:
    """Estimasi jumlah token (~4 char per token untuk bahasa Latin)."""
    if not text:
        return 0
    try:
        from tokenizers import Tokenizer
        tok = Tokenizer.from_pretrained("Xenova/qwen2-tokenizer")
        return len(tok.encode(text).ids)
    except Exception:
        return max(1, len(text) // 4)

def estimate_cost(tokens: int, model: str = "gpt-4o-mini") -> float:
    """Estimasi biaya dalam USD (untuk referensi)."""
    rates = {"gpt-4o": 0.005, "gpt-4o-mini": 0.00015, "gpt-3.5-turbo": 0.0005}
    rate = rates.get(model, 0.0)
    return tokens * rate / 1000
