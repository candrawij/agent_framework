# API Reference

Base URL: `http://localhost:8000`

## Authentication

Semua endpoint (kecuali `/health`) membutuhkan JWT token:

```
Authorization: Bearer <access_token>
```

---

## Endpoints

### POST /api/v1/chat
Kirim pesan dan dapatkan response dari agent.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Apa ibu kota Indonesia?"}
  ],
  "session_id": "abc123",
  "stream": false,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "content": "Ibu kota Indonesia adalah Jakarta.",
  "session_id": "abc123",
  "model": "qwen2.5:3b",
  "agent_used": "ReactAgent"
}
```

---

### GET /api/v1/agents
Daftar semua agent yang terdaftar.

**Response:**
```json
[
  {"name": "supervisor", "description": "...", "enabled": true, "tools": []},
  {"name": "ReactAgent", "description": "...", "enabled": true, "tools": ["web_search"]}
]
```

---

### GET /api/v1/models
Daftar model yang tersedia.

---

### POST /api/v1/upload
Upload file ke knowledge base.

**Form Data:** `file` (multipart)

---

### WebSocket /ws/chat/{session_id}
Streaming chat via WebSocket.

**Send:**
```json
{"content": "Jelaskan machine learning"}
```

**Receive (stream):**
```json
{"type": "token", "content": "Machine", "session_id": "abc123"}
{"type": "token", "content": " learning", "session_id": "abc123"}
{"type": "agent_done", "session_id": "abc123"}
```

---

## Error Responses

| Code | Meaning |
|------|---------|
| 400 | Bad Request |
| 401 | Unauthorized (invalid/missing JWT) |
| 403 | Forbidden (prompt injection detected) |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
