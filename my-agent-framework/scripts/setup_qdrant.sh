#!/bin/bash
# setup_qdrant.sh — Install and start Qdrant via Docker
echo "Setting up Qdrant vector database..."
docker pull qdrant/qdrant:latest
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/data/qdrant:/qdrant/storage \
    qdrant/qdrant:latest
echo "[OK] Qdrant running at http://localhost:6333"
echo "     Dashboard: http://localhost:6333/dashboard"
