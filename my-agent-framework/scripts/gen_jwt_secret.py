#!/usr/bin/env python3
"""Generate a secure JWT secret and save to .env"""
import secrets
import sys
from pathlib import Path

secret = secrets.token_hex(32)
print(f"JWT_SECRET={secret}")

env_file = Path("config/.env")
if env_file.exists():
    content = env_file.read_text()
    if "JWT_SECRET=" in content:
        lines = [f"JWT_SECRET={secret}" if l.startswith("JWT_SECRET=") else l for l in content.splitlines()]
        env_file.write_text("\n".join(lines))
    else:
        env_file.write_text(content + f"\nJWT_SECRET={secret}\n")
    print(f"[OK] JWT_SECRET updated in {env_file}")
else:
    print(f"[INFO] Add JWT_SECRET={secret} to your .env file")
