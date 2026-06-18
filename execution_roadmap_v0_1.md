# My Agent Framework — Execution Roadmap v0.2

> **Changelog dari v0.1:**
> Sprint 3 dan 4 dibalik (ReAct Loop sebelum Memory). Sprint 1 dipecah menjadi 1a dan 1b. Preparation Stage dijadikan Sprint 0 dengan durasi eksplisit. Plugin SDK dimajukan ke Sprint 5 (sebelum agent spesifik). Durasi estimasi ditambahkan per sprint. Mobile gateway ditambahkan sebagai sub-task Sprint 1b. Dependensi antar sprint ditulis eksplisit.

---

## Purpose

Dokumen ini berisi rencana implementasi setelah boilerplate selesai dibuat.
Tujuan utama fase berikutnya adalah mengubah boilerplate menjadi framework yang benar-benar hidup dan siap berkembang menjadi platform agent seperti OpenClaw.

---

## Current Status

### Selesai

- PRD
- Folder Structure
- Boilerplate
- API Layer
- Model Layer
- Gateway Desktop
- Gateway Mobile
- Shared Schema
- Testing
- Documentation

### Belum Production Ready

- Agent Loop
- Tool Calling
- Memory System
- Workflow Engine
- Multi-Agent
- RAG
- Plugin SDK

---

## Architecture Goal

```
Desktop / Mobile
↓
Gateway
↓
FastAPI
↓
Agent Loop
↓
Model Manager
↓
Qwen Connector
↓
Local Model
```

---

## Konvensi Dokumen Ini

| Simbol | Arti |
|--------|------|
| ⏱ | Estimasi durasi sprint |
| 🔗 | Dependensi dari sprint sebelumnya |
| ✅ | Success criteria |

---

## Sprint 0 — Foundation Contracts

**⏱ Estimasi: 3–5 hari**

Sprint ini memastikan semua modul berbicara dengan "bahasa yang sama" sebelum implementasi dimulai. Tidak ada fitur yang dibangun di sini — hanya kontrak.

### Interface Contract

Semua modul harus berkomunikasi menggunakan interface, bukan implementasi langsung. Tidak ada dependency silang antar modul.

**Base Adapter**
```
generate()
stream()
```

**Base Tool**
```
execute()
```

**Base Agent**
```
think()
act()
observe()
reflect()
```

### Shared Schema

Object utama yang digunakan oleh Desktop, Mobile, API, dan Agent Core:

- `ChatRequest`
- `ChatResponse`
- `Message`
- `ToolCall`
- `ToolResult`
- `AgentState`

### Event System

Event yang dapat dipantau melalui WebSocket:

- `USER_MESSAGE`
- `MODEL_STREAM`
- `TOOL_START`
- `TOOL_END`
- `ERROR`

### Logging

Setiap log entry menggunakan:

- `request_id`
- `session_id`
- `trace_id`

### ✅ Success Criteria

- Tidak ada dependency silang langsung antar modul.
- Adapter dapat diganti tanpa mengubah Agent Core.
- Desktop, Mobile, API, dan Agent Core menggunakan struktur data yang sama.
- Semua event dapat dipantau melalui WebSocket.
- Semua error dapat ditelusuri menggunakan tiga ID di atas.

---

## Sprint 1a — Qwen Connector (Model Validation)

**⏱ Estimasi: 3–4 hari**
**🔗 Dependensi: Sprint 0 (Base Adapter interface selesai)**

Sebelum menyentuh UI, pastikan model bisa berkomunikasi dengan benar. Sprint ini hanya memvalidasi bahwa Qwen Connector bekerja — via terminal atau curl, bukan lewat gateway.

### Scope

- Implementasi `QwenAdapter` mengikuti `Base Adapter` dari Sprint 0
- `generate()` — non-streaming, satu prompt → satu respons
- `stream()` — streaming token per token ke stdout
- `ModelManager` — load config dari `models.yaml`, instantiate adapter yang benar

### Flow

```
curl / Python script
↓
ModelManager
↓
QwenAdapter
↓
Local Qwen (Ollama / llama.cpp)
↓
Response ke terminal
```

### ✅ Success Criteria

Jalankan script berikut dari terminal:

```
python test_model.py --prompt "Halo siapa kamu?"
```

Model menjawab dan token muncul secara streaming di terminal. Tidak ada crash, tidak ada timeout.

---

## Sprint 1b — Core Chat End-to-End

**⏱ Estimasi: 4–5 hari**
**🔗 Dependensi: Sprint 1a (Qwen Connector berjalan)**

Sambungkan model ke gateway. Sprint ini menghasilkan produk pertama yang bisa dipakai manusia — bukan hanya developer.

### Scope

- `AgentLoop` sederhana: terima input → kirim ke model → kembalikan respons (belum ada tool, belum ada memori)
- `POST /chat` endpoint di FastAPI terhubung ke AgentLoop
- WebSocket streaming endpoint terhubung ke Desktop
- Desktop gateway: user bisa mengetik pesan dan melihat jawaban streaming
- Mobile gateway: validasi mobile bisa melakukan hal yang sama seperti desktop (streaming end-to-end)

### Flow

```
Desktop / Mobile
↓
POST /chat atau WebSocket
↓
AgentLoop (sederhana)
↓
ModelManager
↓
QwenAdapter
↓
Response streaming ke gateway
```

### ✅ Success Criteria

**Desktop:** User membuka aplikasi desktop, mengetik "Halo siapa kamu?", model menjawab dan teks muncul token per token.

**Mobile:** User membuka aplikasi mobile di device nyata (Android atau iOS), mengirim pesan yang sama, mendapat respons streaming yang identik.

---

## Sprint 2 — ReAct Loop

**⏱ Estimasi: 5–7 hari**
**🔗 Dependensi: Sprint 1b (AgentLoop sederhana berjalan)**

ReAct Loop adalah fondasi cara agent berpikir. Sprint ini harus selesai sebelum memory dan tool calling dibangun, karena keduanya bergantung pada loop ini.

### Komponen

- `Planner` — menerima input, memutuskan langkah berikutnya
- `Executor` — menjalankan aksi (untuk sekarang: memanggil model saja)
- `Observer` — memproses hasil aksi menjadi observasi
- `Reflector` — mengevaluasi apakah task sudah selesai; jika belum, kembali ke Planner

### Loop

```
Think (Planner)
↓
Act (Executor)
↓
Observe (Observer)
↓
Reflect (Reflector)
↓
[loop kembali ke Think jika belum selesai]
↓
Respond
```

### ✅ Success Criteria

Prompt yang membutuhkan lebih dari satu langkah berpikir:

```
"Jelaskan perbedaan antara list dan tuple di Python,
 lalu berikan contoh kapan menggunakan masing-masing."
```

Agent melakukan minimal dua iterasi loop (Think → Act → Observe → Reflect → Think lagi) sebelum merespons. Trace loop terlihat di log dengan `trace_id`.

---

## Sprint 3 — Tool Calling

**⏱ Estimasi: 5–7 hari**
**🔗 Dependensi: Sprint 2 (ReAct Loop berjalan)**

Tool calling adalah aksi pertama yang nyata — agent mulai bisa melakukan sesuatu di dunia nyata, bukan hanya menghasilkan teks.

### Tools

| Tool | Fungsi |
|------|--------|
| `FileTool` | Buat, baca, tulis, hapus file |
| `ShellTool` | Jalankan perintah shell (sandboxed) |
| `HttpTool` | HTTP GET/POST ke URL eksternal |

### Flow dalam ReAct Loop

```
Think → memutuskan tool yang diperlukan
↓
Act → Executor memanggil tool.execute()
↓
Observe → hasil tool masuk sebagai observasi
↓
Reflect → apakah task selesai?
↓
Respond
```

### ✅ Success Criteria

Prompt:

```
"Buat file hello.py yang berisi fungsi untuk mencetak Hello World."
```

Agent benar-benar membuat file `hello.py` di filesystem. File dapat dibuka dan isinya sesuai instruksi.

---

## Sprint 4 — Memory System

**⏱ Estimasi: 6–8 hari**
**🔗 Dependensi: Sprint 2 (ReAct Loop), Sprint 3 (Tool Calling untuk operasi file ke memory)**

Memory dibangun setelah loop ada, karena loop yang menentukan kapan memory dibaca dan ditulis.

### Komponen

**Short-Term Memory**
- Sliding window context
- Menyimpan N pesan terakhir dalam satu sesi
- Otomatis di-trim ketika mendekati batas context length model

**Long-Term Memory**
- Vector database (Qdrant lokal)
- Menyimpan ringkasan percakapan penting
- Retrieval semantik berdasarkan relevansi

**Episodic Memory**
- Catatan pengalaman lintas sesi
- Agent dapat "mengingat" bahwa user pernah menanyakan sesuatu di sesi sebelumnya

**Memory Manager**
- Orkestrasi ketiga layer di atas
- Menentukan kapan harus retrieval, kapan harus menyimpan

### ✅ Success Criteria

1. Dalam satu sesi, agent mengingat konteks dari awal percakapan meskipun sudah 20+ pesan.
2. Di sesi berbeda (aplikasi ditutup lalu dibuka lagi), agent masih bisa menjawab: "Kemarin kamu tanya tentang apa?"

---

## Sprint 5 — Plugin SDK

**⏱ Estimasi: 4–5 hari**
**🔗 Dependensi: Sprint 3 (Tool Calling pattern sudah established)**

Plugin SDK dibangun sebelum agent-agent spesifik dibuat, agar semua agent di sprint berikutnya menggunakan plugin system — bukan hardcoded tools.

### Interface

```python
class BasePlugin:
    name: str
    description: str

    def execute(self, input: PluginInput) -> PluginOutput:
        ...
```

### Contoh Plugin Awal

- `BrowserPlugin` — fetch halaman web
- `OcrPlugin` — ekstrak teks dari gambar
- `EmailPlugin` — kirim/baca email
- `WhatsAppPlugin` — notifikasi via WhatsApp

### ✅ Success Criteria

- Plugin baru dapat ditambahkan dengan membuat satu file Python baru.
- Tidak ada perubahan pada core framework.
- Plugin ter-register otomatis dan tersedia untuk semua agent.
- Tool Calling dari Sprint 3 di-refactor menggunakan Plugin SDK ini.

---

## Sprint 6 — RAG (Retrieval-Augmented Generation)

**⏱ Estimasi: 5–6 hari**
**🔗 Dependensi: Sprint 4 (Qdrant sudah berjalan dari Long-Term Memory), Sprint 5 (Plugin SDK untuk upload pipeline)**

RAG memanfaatkan infrastruktur Qdrant yang sudah ada dari Sprint 4 — tidak perlu setup ulang.

### Pipeline

```
Upload PDF / Dokumen
↓
Chunking (split menjadi potongan kecil)
↓
Embedding (nomic-embed-text / mxbai-embed)
↓
Simpan ke Qdrant
↓
[saat ada query]
↓
Retrieval — ambil chunk paling relevan
↓
Inject ke context LLM
↓
Response berbasis dokumen
```

### ✅ Success Criteria

1. User upload file `product_manual.pdf` via desktop atau mobile.
2. User bertanya: "Apa langkah pertama untuk menginstal produk ini?"
3. Agent menjawab berdasarkan isi dokumen, bukan pengetahuan umum model.

---

## Sprint 7 — Supervisor Agent

**⏱ Estimasi: 6–8 hari**
**🔗 Dependensi: Sprint 5 (Plugin SDK), Sprint 6 (RAG aktif)**

Supervisor agent memungkinkan satu endpoint untuk menangani berbagai jenis permintaan — user tidak perlu memilih agent secara manual.

### Agent yang Dibangun

| Agent | Spesialisasi |
|-------|-------------|
| `ChatAgent` | Percakapan umum |
| `CodingAgent` | Tugas pemrograman, debug, review |
| `ResearchAgent` | Riset dengan RAG + web search |
| `FileAgent` | Operasi file dan dokumen |

### Flow

```
User input
↓
SupervisorAgent (klasifikasi intent)
↓
Delegasi ke agent yang tepat
↓
Agent spesifik menjalankan task
↓
Response ke user
```

### ✅ Success Criteria

User hanya berinteraksi dengan satu endpoint. Supervisor secara otomatis mendelegasikan:
- "Buatkan fungsi sorting di Python" → `CodingAgent`
- "Cari informasi tentang transformer architecture" → `ResearchAgent`
- "Rename semua file di folder ini" → `FileAgent`

---

## Sprint 8 — Workflow Engine

**⏱ Estimasi: 7–10 hari**
**🔗 Dependensi: Sprint 7 (Supervisor Agent dan agent spesifik tersedia)**

Workflow Engine memungkinkan task panjang berjalan secara otonom tanpa intervensi user di setiap langkah.

### Komponen

```
Planner (buat task graph)
↓
Task Queue (antrian task dengan dependensi)
↓
Executor (jalankan task secara paralel jika memungkinkan)
↓
Observer (pantau hasil)
↓
Reflector (putuskan langkah berikutnya)
```

### ✅ Success Criteria

Prompt:

```
"Buat aplikasi todo list sederhana: buat struktur folder,
 tulis kode, buat README, dan jalankan test."
```

Agent menyelesaikan semua langkah secara otonom tanpa konfirmasi manual di setiap step. Hasilnya adalah folder proyek lengkap yang bisa langsung dijalankan.

---

## Sprint 9 — Multi-Agent

**⏱ Estimasi: 7–10 hari**
**🔗 Dependensi: Sprint 7 (Supervisor), Sprint 8 (Workflow Engine)**

Ekstensi dari Supervisor Agent ke arsitektur multi-agent yang lebih kompleks, di mana agent dapat mendelegasikan sub-task ke agent lain secara dinamis.

### Arsitektur

```
SupervisorAgent
├── ResearchAgent
├── CodingAgent
├── FileAgent
└── MemoryAgent
```

Setiap agent dapat menjadi supervisor untuk sub-agent-nya sendiri (hierarki bertingkat).

### ✅ Success Criteria

Prompt:

```
"Riset tentang teknik RAG terbaru, rangkum temuan,
 tulis kode contoh implementasi, dan simpan hasilnya."
```

Supervisor mendelegasikan riset ke `ResearchAgent`, penulisan kode ke `CodingAgent`, dan penyimpanan ke `FileAgent`. Hasilnya diagregasi oleh Supervisor sebelum disampaikan ke user.

---

## Future Features

Belum menjadi prioritas di roadmap ini:

- Voice input/output
- OCR advanced
- Browser Automation
- Scheduler (cron-like task)
- Plugin Marketplace
- Swarm Agent (agen dalam skala besar)

---

## Ringkasan Roadmap

| Sprint | Nama | Estimasi | Dependensi |
|--------|------|----------|------------|
| Sprint 0 | Foundation Contracts | 3–5 hari | — |
| Sprint 1a | Qwen Connector | 3–4 hari | Sprint 0 |
| Sprint 1b | Core Chat End-to-End | 4–5 hari | Sprint 1a |
| Sprint 2 | ReAct Loop | 5–7 hari | Sprint 1b |
| Sprint 3 | Tool Calling | 5–7 hari | Sprint 2 |
| Sprint 4 | Memory System | 6–8 hari | Sprint 2, 3 |
| Sprint 5 | Plugin SDK | 4–5 hari | Sprint 3 |
| Sprint 6 | RAG | 5–6 hari | Sprint 4, 5 |
| Sprint 7 | Supervisor Agent | 6–8 hari | Sprint 5, 6 |
| Sprint 8 | Workflow Engine | 7–10 hari | Sprint 7 |
| Sprint 9 | Multi-Agent | 7–10 hari | Sprint 7, 8 |
| **Total** | | **~55–75 hari** | |

---

## Definition of Done

Framework dianggap berhasil apabila:

1. Chat berjalan end-to-end di desktop **dan** mobile.
2. Tool dapat dipanggil dan menghasilkan aksi nyata di filesystem.
3. Memory bekerja dalam satu sesi dan lintas sesi.
4. ReAct Loop berjalan dengan trace yang dapat ditelusuri.
5. RAG dapat menjawab berdasarkan dokumen yang diunggah.
6. Supervisor Agent mendelegasikan task ke agent yang tepat secara otomatis.
7. Plugin dapat ditambahkan tanpa mengubah core.
8. Framework stabil, modular, dan setiap komponen dapat diganti secara independen.
