# Laporan Permasalahan Endpoint Chat API
**Tanggal:** 18 Juni 2026  
**Tahap:** Sprint 1b – Core Chat E2E  
**Status:** API aktif, namun AgentLoop belum terhubung dengan ModelManager

---

# 1. Latar Belakang

Setelah seluruh langkah setup berhasil dilakukan, pengujian dilanjutkan pada endpoint:

```
http://localhost:8000/api/docs#/chat/chat_api_v1_chat_post
```

Tujuan pengujian:

- Memastikan endpoint `/api/v1/chat` menghasilkan respons nyata dari model.
- Memastikan alur end-to-end sudah berjalan:

```
User
 ↓
FastAPI
 ↓
Chat Route
 ↓
AgentLoop
 ↓
ModelManager
 ↓
OllamaAdapter
 ↓
Qwen2.5:3b
 ↓
Response
```

---

# 2. Hasil Pengujian

Request:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Halo!"
    }
  ],
  "session_id": "string",
  "stream": false,
  "agent_name": "string",
  "temperature": 0.7
}
```

Response:

```json
{
  "content": "[Tidak ada hasil]",
  "session_id": "string",
  "model": "agent_loop",
  "agent_used": "string"
}
```

Expected:

```json
{
  "content": "Halo! Saya Qwen ...",
  "session_id": "...",
  "model": "qwen2.5:3b"
}
```

---

# 3. Verifikasi Komponen

## 3.1 FastAPI

Endpoint:

```
/health
```

Response:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "model_connected": true,
  "model": "OllamaAdapter"
}
```

Status:

- FastAPI : ✅
- App State : ✅
- ModelManager : ✅
- OllamaAdapter : ✅

---

## 3.2 Swagger UI

Endpoint:

```
http://localhost:8000/api/docs
```

Status:

- Swagger aktif : ✅
- Endpoint `/api/v1/chat` tersedia : ✅

---

## 3.3 Ollama

Menjalankan:

```bash
ollama serve
```

Status:

- Server aktif : ✅
- GPU CUDA terdeteksi : ✅
- Qwen2.5:3b tersedia : ✅

---

## 3.4 Adapter

Menjalankan:

```bash
python test_model.py --prompt "Halo siapa kamu?" --stream
```

Output:

```text
Halo! Saya Qwen, sebagai asisten yang dibuat oleh Alibaba Cloud...
```

Status:

- OllamaAdapter : ✅
- Streaming : ✅
- Model : ✅

---

# 4. Analisis Alur Endpoint

## Route Chat

chat.py mencoba AgentLoop terlebih dahulu:

```python
agent_loop = _get_agent_loop(request)

if agent_loop is not None:
    result = agent_loop.run(...)
    return ChatResponse(...)
```

ModelManager hanya dipanggil apabila AgentLoop melempar exception:

```python
except Exception:
    # fallback ke model manager
```

Karena AgentLoop tidak menghasilkan exception, maka fallback tidak pernah terjadi.

---

# 5. Investigasi AgentLoop

Pada server.py:

```python
agent_loop = AgentLoop(max_iterations=10)
```

AgentLoop dibuat tanpa:

- model_manager
- supervisor

---

## _execute_task()

Bagian akhir:

```python
if self.supervisor:
    ...
    return success

return {
    "success": False,
    "error": "Tidak ada executor/supervisor tersedia",
    "output": None
}
```

Karena supervisor tidak tersedia, seluruh task gagal.

---

# 6. Dampak pada run()

Nilai:

```python
tasks_completed = 0
tasks_failed > 0
final_answer = ""
```

Pada akhir fungsi:

```python
LoopRunResult(
    final_answer=final_answer or "[Tidak ada hasil]"
)
```

Sehingga menghasilkan:

```json
{
  "content": "[Tidak ada hasil]",
  "model": "agent_loop"
}
```

---

# 7. Root Cause

## Root Cause Utama

AgentLoop belum memiliki koneksi ke ModelManager.

Arsitektur saat ini:

```
User
 ↓
FastAPI
 ↓
Chat Route
 ↓
AgentLoop
 ↓
Planner
 ↓
Task
 ↓
_execute_task()
 ↓
Tidak ada supervisor
 ↓
Tidak ada model
 ↓
"[Tidak ada hasil]"
```

Padahal arsitektur yang diharapkan:

```
User
 ↓
FastAPI
 ↓
Chat Route
 ↓
AgentLoop
 ↓
ModelManager
 ↓
OllamaAdapter
 ↓
Qwen2.5:3b
 ↓
Response
```

---

# 8. Solusi Sementara

Pada chat.py, setelah:

```python
result = agent_loop.run(...)
```

Tambahkan validasi:

```python
answer = (
    result.final_answer
    if hasattr(result, "final_answer")
    else str(result)
)

if answer in ("", "[Tidak ada hasil]"):
    raise RuntimeError(
        "AgentLoop returned empty result"
    )
```

Sehingga:

```python
except Exception:
```

akan memicu fallback ke:

```python
model_manager.complete(...)
```

---

# 9. Solusi Permanen

## Tambahkan model_manager ke AgentLoop

Pada constructor:

```python
class AgentLoop:
    def __init__(
        ...
        model_manager=None
    ):
        self.model_manager = model_manager
```

---

## Hubungkan saat startup

server.py

Dari:

```python
agent_loop = AgentLoop(max_iterations=10)
```

Menjadi:

```python
agent_loop = AgentLoop(
    model_manager=model_manager,
    max_iterations=10
)
```

---

## Tambahkan fallback model di _execute_task()

Jika tidak ada tool dan supervisor:

```python
if self.model_manager:
    result = self.model_manager.complete(
        messages=[
            {
                "role": "user",
                "content": str(task.input)
            }
        ]
    )

    return {
        "success": True,
        "output": result["content"]
    }
```

---

# 10. Arsitektur Setelah Perbaikan

```
POST /api/v1/chat
            │
            ▼
        AgentLoop
            │
            ▼
       Planner Task
            │
            ▼
      _execute_task()
            │
            ▼
      ModelManager.complete()
            │
            ▼
        OllamaAdapter
            │
            ▼
        qwen2.5:3b
            │
            ▼
         Response
```

---

# 11. Kriteria Keberhasilan

## Functional

### Endpoint

Request:

```json
{
  "messages":[
    {
      "role":"user",
      "content":"Halo!"
    }
  ]
}
```

Response:

```json
{
  "content":"Halo! Saya Qwen...",
  "session_id":"xxxx",
  "model":"qwen2.5:3b"
}
```

---

## System

- FastAPI berjalan.
- Swagger dapat diakses.
- AgentLoop aktif.
- AgentLoop terhubung ke ModelManager.
- ModelManager terhubung ke OllamaAdapter.
- Ollama dapat menghasilkan respons.

---

## Sprint 1b dianggap selesai apabila

Alur berikut berhasil:

```
POST /api/v1/chat
 ↓
AgentLoop
 ↓
ModelManager
 ↓
OllamaAdapter
 ↓
Qwen2.5:3b
 ↓
Response
```

dan endpoint tidak lagi menghasilkan:

```
"[Tidak ada hasil]"
```