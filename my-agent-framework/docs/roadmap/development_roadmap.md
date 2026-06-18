# Development Roadmap & Testing Plan v0.2
## Custom Multi-Agent Framework

**Tanggal:** 18 Juni 2026
**Versi Sebelumnya:** v0.1

> **Changelog dari v0.1:**
> Penomoran sprint dikonsistenkan (Sprint 1–5 = bagian yang sudah selesai, Sprint 6 dst = yang akan dikerjakan). Sprint 7 (Memory) dan Sprint 8 (Tool Calling) dibalik — Tool Calling lebih dulu karena merupakan kemampuan bertindak sebelum kemampuan mengingat. Sprint 12 (Background Task) digabung ke Sprint 13 (Workflow Engine) karena merupakan prasyarat, bukan fitur terpisah. Sprint 15 (Production) dipecah menjadi 15a dan 15b. Estimasi durasi ditambahkan. Dependency chain antar sprint ditulis eksplisit. Testing criteria diperluas di setiap sprint.

---

## Konvensi Dokumen

| Simbol | Arti |
|--------|------|
| ⏱ | Estimasi durasi sprint |
| 🔗 | Dependensi dari sprint sebelumnya |
| ✅ | Success criteria — PASS jika semua terpenuhi |
| ⚠️ | Failure case yang harus ditangani |

---

# 1. Status Saat Ini (Sprint 1–5 Selesai)

Sprint 1–5 mencakup semua pekerjaan yang sudah berhasil di bawah ini.

## Foundation (Sprint 1)
- Struktur project
- Dependency management
- Config management

## Model Layer (Sprint 2)
- Ollama Adapter
- ModelManager
- Qwen2.5 integration

## API Layer (Sprint 3)
- FastAPI server
- Swagger / OpenAPI docs
- Health endpoint
- Session endpoint
- Chat endpoint

## Agent Core (Sprint 4)
- Planner
- Executor
- Observer
- Reflector
- AgentLoop

## Chat End-to-End via Swagger (Sprint 5)

Flow yang sudah berhasil:

```
Swagger
 ↓
POST /api/v1/chat
 ↓
FastAPI
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

# 2. Metode Pengembangan

Setiap sprint mengikuti urutan berikut:

```
1. Implementasi
2. Testing via Swagger (unit & API level)
3. Stabilization — perbaiki edge case & error handling
4. Integrasi ke Desktop Gateway
5. Integrasi ke Mobile Gateway
```

Selama Desktop Gateway belum stabil, Swagger menjadi alat pengujian utama. Mobile Gateway divalidasi setelah Desktop stabil di setiap sprint.

---

# 3. Sprint Aktif

---

## Sprint 6 — Desktop Gateway

**⏱ Estimasi: 5–7 hari**
**🔗 Dependensi: Sprint 5 (Chat end-to-end via API berjalan)**

### Tujuan

Membangun aplikasi desktop sebagai gateway utama. Setelah sprint ini selesai, Swagger tidak lagi dibutuhkan untuk testing manual — desktop menjadi antarmuka utama.

### Arsitektur

```
Desktop App (Electron / Tauri)
 ↓
WebSocket + REST
 ↓
FastAPI
 ↓
AgentLoop
 ↓
Qwen
```

### Struktur

```
desktop/
    src/
        components/
            ChatBubble/
            MessageInput/
            SessionItem/
        pages/
            ChatPage/
            SettingsPage/
        services/
            api.ts          ← REST client
            websocket.ts    ← streaming handler
            auth.ts
        store/
            sessionStore.ts
            chatStore.ts
```

### Fitur

**Chat**
- Input message dengan keyboard shortcut (Enter kirim, Shift+Enter newline)
- Output message dengan markdown rendering (bold, italic, code block)
- Streaming token per token — teks muncul secara real-time

**Session Sidebar**
- Daftar session aktif
- Buat session baru
- Hapus session

**Settings**
- API URL (koneksi ke framework)
- Pilih model aktif

**Indikator Status**
- Thinking (agen sedang memproses)
- Responding (teks sedang di-stream)
- Error state dengan pesan yang informatif

### Testing

#### Test 1 — Basic Chat

Input:
```
Halo
```

Expected:
```
Halo! Apa yang bisa saya bantu?
```

✅ PASS: Response muncul dalam chat bubble.
⚠️ FAIL case: Pesan error ditampilkan jika API tidak dapat dijangkau, bukan aplikasi freeze.

---

#### Test 2 — Streaming

Kirim prompt yang menghasilkan respons panjang:
```
Jelaskan cara kerja neural network dalam 5 paragraf.
```

✅ PASS: Teks muncul token per token, UI tidak freeze selama streaming berlangsung.
✅ PASS: Tombol "Stop" dapat menghentikan streaming di tengah jalan.

---

#### Test 3 — Multi-Session

1. Buat Session A, tanya "Halo dari session A".
2. Buat Session B, tanya "Halo dari session B".
3. Kembali ke Session A, tanya "Apa yang baru saja saya katakan?".

✅ PASS: Riwayat Session A dan Session B tidak bercampur.
✅ PASS: Model menjawab berdasarkan konteks session yang benar.

---

#### Test 4 — Settings

1. Ubah API URL ke URL yang salah.
2. Kirim pesan.

✅ PASS: Error ditampilkan dengan pesan yang jelas ("Tidak dapat terhubung ke server").
✅ PASS: Ubah kembali ke URL benar — chat kembali berfungsi tanpa restart aplikasi.

---

## Sprint 7 — Tool Calling

**⏱ Estimasi: 5–7 hari**
**🔗 Dependensi: Sprint 6 (Desktop Gateway stabil untuk testing visual)**

> **Catatan v0.2:** Tool Calling dimajukan sebelum Memory System. Agent harus bisa *bertindak* sebelum bisa *mengingat*. Memory System di Sprint 8 akan bergantung pada pola tool execution yang dibangun di sprint ini.

### Tujuan

Agent dapat memanggil tools untuk menghasilkan aksi nyata — bukan hanya menghasilkan teks.

### Struktur

```
tools/
    base_tool.py        ← abstract interface
    datetime_tool.py
    calculator_tool.py
    file_tool.py
    http_tool.py
    tool_registry.py    ← registrasi & discovery
```

### Interface

```python
class BaseTool:
    name: str
    description: str
    parameters: dict  # JSON Schema

    def execute(self, **kwargs) -> ToolResult:
        ...
```

### Tool Catalog

| Tool | Fungsi | Input | Output |
|------|--------|-------|--------|
| `DatetimeTool` | Waktu & tanggal sekarang | — | string datetime |
| `CalculatorTool` | Kalkulasi matematis | ekspresi string | angka |
| `FileTool` | Baca/tulis/list file | path, content | string |
| `HttpTool` | HTTP GET/POST | url, method, body | response body |

### Testing

#### Test 1 — Calculator

Input:
```
15 dikali 27 berapa?
```

✅ PASS: Log menunjukkan `calculator_tool` dipanggil dengan input `15 * 27`.
✅ PASS: Response yang ditampilkan ke user adalah `405`.
⚠️ FAIL case: Agent menjawab dari "pengetahuan" sendiri tanpa memanggil tool — ini FAIL.

---

#### Test 2 — Datetime

Input:
```
Jam berapa sekarang?
```

✅ PASS: Log menunjukkan `datetime_tool` dipanggil.
✅ PASS: Response berisi waktu aktual, bukan estimasi dari model.

---

#### Test 3 — File Tool

Input:
```
Buat file bernama hello.py yang berisi fungsi untuk mencetak Hello World.
```

✅ PASS: File `hello.py` benar-benar terbuat di filesystem.
✅ PASS: Isi file sesuai instruksi.
✅ PASS: Agent mengkonfirmasi file sudah dibuat dalam responnya.

---

#### Test 4 — Multi-Tool dalam Satu Prompt

Input:
```
Simpan waktu sekarang ke file log.txt
```

✅ PASS: `datetime_tool` dipanggil terlebih dahulu.
✅ PASS: `file_tool` dipanggil dengan hasil dari datetime_tool.
✅ PASS: File `log.txt` berisi timestamp yang benar.

---

#### Test 5 — Tool Error Handling

Input:
```
Baca file yang_tidak_ada.txt
```

✅ PASS: Agent menginformasikan bahwa file tidak ditemukan, bukan crash atau silent fail.

---

## Sprint 8 — Memory System

**⏱ Estimasi: 6–8 hari**
**🔗 Dependensi: Sprint 7 (Tool Calling — karena FileTool digunakan untuk episodic memory I/O)**

### Tujuan

Agent dapat mengingat konteks dalam satu sesi dan lintas sesi.

### Arsitektur

```
User Input
 ↓
MemoryManager
 ├── ShortTermMemory  (sliding window, in-memory)
 ├── LongTermMemory   (Qdrant vector DB, lokal)
 └── EpisodicMemory   (SQLite, catatan lintas sesi)
 ↓
AgentLoop
 ↓
Model
```

### Komponen

**Short-Term Memory**
- Sliding window — simpan N pesan terakhir dalam satu sesi
- Auto-trim ketika mendekati batas context length model
- Di-reset saat session dihapus

**Long-Term Memory**
- Vector DB Qdrant (lokal, self-hosted)
- Simpan ringkasan percakapan penting
- Retrieval semantik berdasarkan relevansi query

**Episodic Memory**
- SQLite lokal
- Catatan pengalaman lintas sesi (siapa user, preferensi, konteks penting)
- Agent dapat "mengingat" interaksi dari sesi sebelumnya

**Memory Manager**
- Orkestrasi ketiga layer
- Menentukan kapan harus write, kapan harus retrieve

### Testing

#### Test 1 — Short-Term Memory

Dalam satu sesi, kirim berturut-turut:
```
Nama saya Candra.
```
Lalu:
```
Siapa nama saya?
```

✅ PASS: Agent menjawab "Nama Anda Candra" tanpa user perlu mengulang.

---

#### Test 2 — Context Window Handling

Kirim 30 pesan berturut-turut dalam satu sesi.

✅ PASS: Agent tetap bisa menjawab pertanyaan tentang pesan ke-5 secara akurat (konteks tidak hilang sepenuhnya meski sudah di-trim).
✅ PASS: Aplikasi tidak crash atau memory leak.

---

#### Test 3 — Long-Term Memory (Cross-Session)

Sesi 1:
```
Saya sedang mengerjakan proyek framework agent berbasis Python.
```

Tutup aplikasi. Buka lagi. Sesi baru:
```
Proyek apa yang sedang saya kerjakan?
```

✅ PASS: Agent menjawab berdasarkan informasi dari sesi sebelumnya.
✅ PASS: Sumber informasi ditandai sebagai "dari percakapan sebelumnya".

---

#### Test 4 — Memory Isolation

Buat dua user berbeda (dua session profile berbeda).

✅ PASS: Memory User A tidak bocor ke User B.

---

## Sprint 9 — Plugin SDK

**⏱ Estimasi: 4–5 hari**
**🔗 Dependensi: Sprint 7 (Tool Calling pattern sudah established sebagai dasar Plugin interface)**

### Tujuan

Menambahkan kemampuan baru ke framework tanpa menyentuh core — cukup dengan menambah satu file plugin.

### Struktur

```
plugins/
    base_plugin.py      ← abstract interface
    plugin_loader.py    ← auto-discovery & registry
    weather/
        __init__.py
        weather_plugin.py
    search/
        __init__.py
        search_plugin.py
```

### Interface

```python
class BasePlugin:
    name: str
    description: str
    version: str
    parameters: dict  # JSON Schema — sama seperti BaseTool

    def execute(self, **kwargs) -> PluginResult:
        ...

    def on_load(self):
        """Dipanggil saat plugin di-load — setup, validasi config, dll."""
        ...
```

### Mekanisme Auto-Discovery

`plugin_loader.py` membaca semua subfolder di `plugins/`, mencari file `*_plugin.py`, dan meregistrasi otomatis. Tidak perlu modifikasi file apapun di core.

### Testing

#### Test 1 — Auto-Discovery

Tambahkan file baru:
```
plugins/weather/weather_plugin.py
```

Restart framework.

✅ PASS: Plugin `weather` muncul di endpoint `GET /api/v1/tools`.
✅ PASS: Tidak ada perubahan di file core manapun.

---

#### Test 2 — Plugin Execution

Input:
```
Cuaca di Jakarta sekarang?
```

✅ PASS: Log menunjukkan `weather_plugin` dipanggil.
✅ PASS: Response berisi data cuaca, bukan jawaban generik dari model.
⚠️ FAIL case: Plugin crash — framework menampilkan error yang informatif, tidak ikut crash.

---

#### Test 3 — Plugin Disable

Disable `weather_plugin` via config tanpa menghapus file.

✅ PASS: Plugin tidak dipanggil meski prompt relevan.
✅ PASS: Re-enable — plugin aktif kembali setelah restart.

---

#### Test 4 — Backward Compatibility

Tools dari Sprint 7 (DatetimeTool, CalculatorTool, FileTool) direfactor menggunakan Plugin SDK.

✅ PASS: Semua test dari Sprint 7 masih lulus setelah refactor.

---

## Sprint 10 — Multi-Agent (Supervisor)

**⏱ Estimasi: 6–8 hari**
**🔗 Dependensi: Sprint 7 (Tool Calling), Sprint 8 (Memory), Sprint 9 (Plugin SDK)**

### Tujuan

Satu endpoint untuk semua jenis permintaan. Supervisor memilih dan mendelegasikan ke agent yang tepat secara otomatis.

### Arsitektur

```
User Input
 ↓
SupervisorAgent (intent classification)
 ├── GeneralAgent    ← percakapan umum
 ├── CodingAgent     ← tugas pemrograman
 ├── SearchAgent     ← riset & pencarian
 └── MemoryAgent     ← operasi memory eksplisit
 ↓
Response diagregasi oleh Supervisor
 ↓
User
```

### Testing

#### Test 1 — Routing ke CodingAgent

Input:
```
Buat program Python untuk mengurutkan list dengan bubble sort.
```

✅ PASS: Log menunjukkan Supervisor memilih `CodingAgent`.
✅ PASS: Response berisi kode Python yang valid dan bisa dijalankan.

---

#### Test 2 — Routing ke SearchAgent

Input:
```
Apa itu transformer architecture dalam machine learning?
```

✅ PASS: Log menunjukkan Supervisor memilih `SearchAgent`.
✅ PASS: Response berisi informasi yang akurat dan terstruktur.

---

#### Test 3 — Routing ke GeneralAgent

Input:
```
Halo, apa kabar?
```

✅ PASS: Supervisor memilih `GeneralAgent` (bukan CodingAgent atau SearchAgent).

---

#### Test 4 — Ambiguous Routing

Input:
```
Buat program Python sorting lalu jelaskan cara kerjanya.
```

✅ PASS: Supervisor mendelegasikan coding ke `CodingAgent` dan penjelasan bisa ditangani oleh agent yang sama atau diagregasi.
✅ PASS: Response berisi kode DAN penjelasan — tidak hanya salah satu.

---

#### Test 5 — Agent Failure Fallback

Simulasikan `CodingAgent` timeout.

✅ PASS: Supervisor memberikan respons fallback yang informatif, bukan silent fail.

---

## Sprint 11 — RAG (Retrieval-Augmented Generation)

**⏱ Estimasi: 5–7 hari**
**🔗 Dependensi: Sprint 8 (Qdrant sudah berjalan dari Long-Term Memory — tidak perlu setup ulang)**

### Tujuan

Agent dapat menjawab berdasarkan dokumen yang diunggah user — bukan hanya dari pengetahuan bawaan model.

### Pipeline

```
Upload Dokumen (PDF / TXT / MD)
 ↓
Document Loader (ekstrak teks)
 ↓
Chunking (split menjadi potongan kecil, ~512 token)
 ↓
Embedding (nomic-embed-text / mxbai-embed via Ollama)
 ↓
Simpan ke Qdrant (reuse dari Sprint 8)
 ↓
[saat ada query]
 ↓
Query Embedding
 ↓
Semantic Retrieval — ambil top-K chunk paling relevan
 ↓
Inject ke context prompt
 ↓
AgentLoop + Qwen
 ↓
Response berbasis dokumen
```

### Testing

#### Test 1 — Basic RAG

1. Upload `laporan.pdf`.
2. Input:
```
Apa isi bab 3?
```

✅ PASS: Jawaban berasal dari konten `laporan.pdf`, bukan pengetahuan umum model.
✅ PASS: Agent menyebutkan sumber ("Berdasarkan dokumen yang diunggah...").

---

#### Test 2 — Multi-Document

Upload dua dokumen berbeda: `doc_a.pdf` dan `doc_b.pdf`.

Input:
```
Apa perbedaan antara isi doc_a dan doc_b?
```

✅ PASS: Agent menggunakan informasi dari kedua dokumen sekaligus.
✅ PASS: Tidak ada cross-contamination (informasi doc_a tidak salah dikaitkan ke doc_b).

---

#### Test 3 — Pertanyaan di Luar Dokumen

Input:
```
Siapa presiden Indonesia?
```
(Setelah upload laporan teknis yang tidak membahas politik)

✅ PASS: Agent menjawab dari pengetahuan umum model, bukan mencoba "memaksa" menjawab dari dokumen.
✅ PASS: Tidak ada halusinasi yang mengklaim informasi berasal dari dokumen.

---

#### Test 4 — Delete Dokumen

Hapus `laporan.pdf` dari knowledge base.

Input pertanyaan yang sebelumnya berhasil dijawab dari PDF.

✅ PASS: Agent tidak lagi menjawab berdasarkan dokumen tersebut.

---

## Sprint 12 — Workflow Engine + Background Task

**⏱ Estimasi: 8–10 hari**
**🔗 Dependensi: Sprint 10 (Multi-Agent), Sprint 11 (RAG)**

> **Catatan v0.2:** Sprint 12 (Background Task) dari v0.1 digabung ke sini karena Background Task adalah prasyarat teknis Workflow Engine, bukan fitur yang berdiri sendiri.

### Tujuan

Task panjang dan kompleks berjalan secara otonom — agent menyelesaikan banyak langkah tanpa intervensi manual di setiap step.

### Arsitektur

```
Input (prompt atau workflow YAML)
 ↓
Planner (buat task graph dengan dependensi)
 ↓
Task Queue (async — background task runner)
 ↓
Executor (jalankan step, paralel jika tidak ada dependensi)
 ↓
Observer (pantau hasil setiap step)
 ↓
Reflector (putuskan langkah berikutnya atau stop)
 ↓
Notifikasi ke user saat selesai
```

### Background Task

- Task berjalan async tanpa memblokir UI
- User dapat menutup chat dan task tetap berjalan
- Notifikasi dikirim ke gateway saat task selesai
- Task dapat di-cancel

### Workflow YAML

```yaml
name: research_and_save
steps:
  search:
    agent: SearchAgent
    input: "{{ user_query }}"
  summarize:
    agent: GeneralAgent
    input: "{{ search.output }}"
    depends_on: [search]
  translate:
    agent: GeneralAgent
    input: "Terjemahkan ke Bahasa Indonesia: {{ summarize.output }}"
    depends_on: [summarize]
  save:
    tool: FileTool
    input:
      path: "output/{{ timestamp }}.md"
      content: "{{ translate.output }}"
    depends_on: [translate]
```

### Testing

#### Test 1 — Background Task

Input:
```
Ringkas file ini dan beri tahu jika selesai.
```

✅ PASS: Task berjalan di background.
✅ PASS: UI tetap responsif selama task berlangsung.
✅ PASS: Notifikasi muncul saat task selesai.
✅ PASS: Task dapat di-cancel dari UI.

---

#### Test 2 — Workflow dari YAML

Jalankan workflow `research_and_save.yaml`.

✅ PASS: Seluruh step berjalan sesuai urutan dependensi.
✅ PASS: File output tersimpan di lokasi yang benar.
✅ PASS: Log menunjukkan setiap step dengan status (started, completed, failed).

---

#### Test 3 — Workflow Error Recovery

Simulasikan satu step gagal (misal: step `translate` timeout).

✅ PASS: Workflow berhenti di step yang gagal, tidak silent skip.
✅ PASS: Error dilaporkan dengan jelas: step mana yang gagal dan kenapa.
✅ PASS: Step sebelum yang gagal tidak dijalankan ulang (idempotent).

---

## Sprint 13 — Mobile Gateway

**⏱ Estimasi: 6–8 hari**
**🔗 Dependensi: Sprint 6 (Desktop Gateway stabil sebagai referensi implementasi)**

### Tujuan

Semua fitur yang tersedia di Desktop Gateway juga tersedia di Mobile, dengan UX yang dioptimalkan untuk layar kecil.

### Arsitektur

```
Flutter App (Android & iOS)
 ↓
WebSocket + REST
 ↓
FastAPI
 ↓
AgentLoop
 ↓
Qwen
```

### Fitur

- Chat dengan streaming token per token
- Session management
- Tool trace — lihat tool yang dipanggil agent
- Settings: API URL, model, tema
- Notifikasi saat background task selesai

### Testing

#### Test 1 — Basic Chat (Android)

Input dari device Android nyata:
```
Halo
```

✅ PASS: Response muncul dalam 3 detik.
✅ PASS: Streaming berjalan mulus tanpa lag visual.

---

#### Test 2 — Basic Chat (iOS)

Input yang sama dari device iOS.

✅ PASS: Behavior identik dengan Android.

---

#### Test 3 — Koneksi via LAN

Framework berjalan di komputer, mobile terhubung via WiFi yang sama.

✅ PASS: Chat berjalan tanpa perlu internet — murni lokal.

---

#### Test 4 — Reconnect Otomatis

Matikan WiFi sebentar lalu nyalakan kembali saat chat sedang aktif.

✅ PASS: Aplikasi reconnect otomatis tanpa perlu restart.
✅ PASS: Pesan yang dikirim saat offline di-queue dan terkirim setelah reconnect.

---

#### Test 5 — Feature Parity dengan Desktop

Jalankan semua test dari Sprint 6 (Desktop) di mobile.

✅ PASS: Semua skenario yang lulus di desktop juga lulus di mobile.

---

## Sprint 14 — Production Readiness

**⏱ Estimasi: 7–10 hari**
**🔗 Dependensi: Semua sprint sebelumnya stabil**

Sprint ini dibagi dua tahap agar tidak terlalu padat.

### Tahap A — Operasional Dasar (Prioritas Tinggi)

**Logging Terstruktur**
```
logs/
    app.log         ← structured JSON
    error.log
    access.log
```
Setiap log entry mengandung: `timestamp`, `request_id`, `session_id`, `trace_id`, `level`, `message`.

**Docker**
```yaml
# docker-compose.yml
services:
  framework:    # FastAPI + AgentLoop
  ollama:       # Model inference
  qdrant:       # Vector DB
  redis:        # Task queue (opsional)
```

**Backup**
- Memory database (Qdrant snapshots) — otomatis setiap 24 jam
- Session database (SQLite) — otomatis setiap 24 jam
- Backup disimpan di folder `backups/` dengan retention 7 hari

### Tahap B — Observability (Prioritas Menengah)

**Metrics (Prometheus)**
- Token per second
- Latency per request
- Tool call success rate
- Memory usage

**Monitoring Dashboard (Grafana)**
- Panel: active sessions, request rate, error rate
- Alert: error rate > 5%, latency > 10 detik

### Testing

#### Test 1 — Docker Compose

```bash
docker-compose up -d
```

✅ PASS: Semua service berjalan.
✅ PASS: Chat end-to-end berfungsi dari dalam container.
✅ PASS: `docker-compose down` dan `up` kembali — tidak ada data yang hilang.

---

#### Test 2 — Logging

Kirim request, simulasikan error.

✅ PASS: Setiap request memiliki `request_id` yang dapat ditelusuri di log.
✅ PASS: Error tercatat lengkap dengan stack trace dan konteks session.

---

#### Test 3 — Backup & Restore

Jalankan backup manual:
```bash
python scripts/backup.py
```

Hapus database, restore dari backup.

✅ PASS: Memory dan session ter-restore dengan benar.
✅ PASS: Percakapan sebelum backup masih bisa diakses.

---

#### Test 4 — Metrics

✅ PASS: Endpoint `GET /metrics` mengembalikan data Prometheus.
✅ PASS: Dashboard Grafana menampilkan data real-time.

---

# 4. Testing Strategy

## Urutan Testing per Sprint

Setiap sprint melewati 4 level testing sebelum dianggap selesai:

```
Level 1: Unit Test
 ↓
Level 2: API Test (Swagger)
 ↓
Level 3: Desktop Integration Test
 ↓
Level 4: Mobile Integration Test
```

## Unit Test

```bash
pytest tests/ -v --tb=short
```

Target komponen:

| Komponen | Test File |
|----------|-----------|
| Planner | `tests/test_planner.py` |
| Executor | `tests/test_executor.py` |
| Observer | `tests/test_observer.py` |
| Reflector | `tests/test_reflector.py` |
| ModelManager | `tests/test_model_manager.py` |
| MemoryManager | `tests/test_memory.py` |
| ToolRegistry | `tests/test_tools.py` |
| PluginLoader | `tests/test_plugins.py` |

Target coverage minimum: **70%** per modul inti.

## API Test

Via Swagger:
```
http://localhost:8000/api/docs
```

Endpoint yang ditest per sprint:

| Endpoint | Sprint |
|----------|--------|
| `POST /chat` | Sprint 5 |
| `GET /stream` | Sprint 6 |
| `POST /upload` | Sprint 11 |
| `GET /sessions` | Sprint 6 |
| `DELETE /sessions/:id` | Sprint 6 |
| `GET /tools` | Sprint 7 |
| `GET /agents` | Sprint 10 |
| `POST /workflow` | Sprint 12 |

## Desktop Integration Test

Electron / Tauri

Target:
- Chat UI + streaming
- Session management
- Tool trace display
- Error state handling

## Mobile Integration Test

Flutter — device nyata, bukan emulator.

Target:
- API connection via LAN
- Session management
- Streaming performance
- Reconnect behavior

## End-to-End Test

Flow lengkap dari gateway ke model:

```
Desktop / Mobile
 ↓
Gateway (WebSocket / REST)
 ↓
FastAPI
 ↓
AgentLoop (Plan → Act → Observe → Reflect)
 ↓
ModelManager
 ↓
OllamaAdapter
 ↓
Qwen2.5
 ↓
Response streaming kembali ke Gateway
```

---

# 5. Ringkasan Roadmap

| Sprint | Nama | Estimasi | Dependensi Utama |
|--------|------|----------|-----------------|
| ✅ 1–5 | Foundation s.d. Chat via Swagger | Selesai | — |
| 6 | Desktop Gateway | 5–7 hari | Sprint 5 |
| 7 | Tool Calling | 5–7 hari | Sprint 6 |
| 8 | Memory System | 6–8 hari | Sprint 7 |
| 9 | Plugin SDK | 4–5 hari | Sprint 7 |
| 10 | Multi-Agent (Supervisor) | 6–8 hari | Sprint 7, 8, 9 |
| 11 | RAG | 5–7 hari | Sprint 8 |
| 12 | Workflow Engine + Background Task | 8–10 hari | Sprint 10, 11 |
| 13 | Mobile Gateway | 6–8 hari | Sprint 6 |
| 14 | Production Readiness | 7–10 hari | Semua sprint |
| **Total sisa** | | **~58–80 hari** | |

> **Catatan:** Sprint 13 (Mobile Gateway) dapat dikerjakan paralel dengan Sprint 9–12 jika ada developer terpisah yang menangani mobile.

---

# 6. Definisi Project Selesai

Framework dianggap matang apabila semua kondisi berikut terpenuhi:

- [ ] Chat stabil end-to-end di Desktop dan Mobile.
- [ ] Streaming berjalan tanpa freeze atau data loss.
- [ ] Tool calling menghasilkan aksi nyata (bukan hanya teks).
- [ ] Memory berfungsi dalam satu sesi dan lintas sesi.
- [ ] Plugin dapat ditambahkan tanpa menyentuh core.
- [ ] Multi-agent routing bekerja dengan akurasi > 90% pada test suite.
- [ ] RAG menjawab berdasarkan dokumen yang diunggah.
- [ ] Background task berjalan tanpa memblokir UI.
- [ ] Workflow engine menyelesaikan task multi-step secara otonom.
- [ ] Semua service berjalan via Docker Compose.
- [ ] Logging terstruktur — setiap error dapat ditelusuri.
- [ ] End-to-end test lulus di Desktop dan Mobile.

**Target Akhir:**

Membangun framework agent lokal yang setara konsep OpenClaw, menggunakan Desktop dan Mobile gateway milik sendiri, berjalan sepenuhnya di infrastruktur lokal tanpa ketergantungan cloud.
