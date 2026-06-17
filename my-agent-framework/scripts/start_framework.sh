#!/bin/bash
# start_framework.sh — Jalankan framework API server
# Adaptasi dari saki_ai_assistant/scripts/start_saki.bat

set -e

echo "========================================"
echo "  Agent Framework — Starting Server"
echo "========================================"

# Aktifkan virtual env jika ada
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load .env jika ada
if [ -f "config/.env" ]; then
    export $(cat config/.env | grep -v "^#" | xargs)
    echo "[OK] Loaded config/.env"
fi

# Cek Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[WARN] Ollama tidak terdeteksi di localhost:11434"
    echo "       Jalankan: ollama serve"
fi

# Start FastAPI
echo "[OK] Starting API server on port ${API_PORT:-8000}..."
python -m uvicorn framework.api.server:app \
    --host "${API_HOST:-0.0.0.0}" \
    --port "${API_PORT:-8000}" \
    --reload
