// API Client for Agent Framework — Sprint 6 upgrade
export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatResponse {
  content: string;
  session_id: string;
  model: string;
  agent_used?: string;
}

export interface SessionInfo {
  session_id: string;
  created_at?: string;
  message_count?: number;
}

export class ApiClient {
  private baseUrl: string;
  private authToken: string | null;

  constructor(baseUrl: string, authToken: string | null = null) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.authToken = authToken;
  }

  private get headers(): Record<string, string> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this.authToken) headers["Authorization"] = `Bearer ${this.authToken}`;
    return headers;
  }

  /** Non-streaming chat */
  async chat(
    messages: ChatMessage[],
    options: { sessionId?: string; temperature?: number } = {}
  ): Promise<ChatResponse> {
    const res = await fetch(`${this.baseUrl}/api/v1/chat`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({
        messages,
        session_id: options.sessionId,
        temperature: options.temperature ?? 0.7,
        stream: false,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return res.json();
  }

  /**
   * SSE Streaming chat — memanggil /api/v1/chat/stream
   * Memanggil onToken setiap ada token baru, onDone saat selesai.
   */
  async chatStream(
    messages: ChatMessage[],
    options: {
      sessionId?: string;
      temperature?: number;
      signal?: AbortSignal;
      onToken: (token: string) => void;
      onToolCall?: (toolCall: any) => void;
      onDone: (fullContent: string, sessionId: string, toolTrace?: any[]) => void;
      onError: (err: string) => void;
    }
  ): Promise<void> {
    let res: Response;
    try {
      res = await fetch(`${this.baseUrl}/api/v1/chat/stream`, {
        method: "POST",
        headers: this.headers,
        signal: options.signal,
        body: JSON.stringify({
          messages,
          session_id: options.sessionId,
          temperature: options.temperature ?? 0.7,
          stream: true,
        }),
      });
    } catch (e: any) {
      if (e.name === "AbortError") return;
      options.onError(e.message ?? "Koneksi gagal");
      return;
    }

    if (!res.ok) {
      options.onError(`HTTP ${res.status}: ${await res.text()}`);
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      options.onError("Streaming tidak tersedia");
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let fullContent = "";
    let finalSessionId = options.sessionId ?? "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw || raw === "[DONE]") continue;

          try {
            const event = JSON.parse(raw);
            if (event.type === "token" && event.content) {
              fullContent += event.content;
              options.onToken(event.content);
            } else if (event.type === "tool_call") {
              options.onToolCall?.(event);
            } else if (event.type === "done") {
              finalSessionId = event.session_id ?? finalSessionId;
              options.onDone(event.full_content ?? fullContent, finalSessionId, event.tool_trace);
            } else if (event.type === "error") {
              options.onError(event.message ?? "Stream error");
            } else if (event.type === "start" && event.session_id) {
              finalSessionId = event.session_id;
            }
          } catch {
            // skip invalid JSON
          }
        }
      }
    } catch (e: any) {
      if (e.name !== "AbortError") {
        options.onError(e.message ?? "Stream interrupted");
      }
    } finally {
      reader.releaseLock();
    }
  }

  async getSessions(): Promise<SessionInfo[]> {
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/sessions`, { headers: this.headers });
      if (!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data) ? data : data.sessions ?? [];
    } catch {
      return [];
    }
  }

  async deleteSession(sessionId: string): Promise<void> {
    await fetch(`${this.baseUrl}/api/v1/sessions/${sessionId}`, {
      method: "DELETE",
      headers: this.headers,
    });
  }

  async getModels(): Promise<string[]> {
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/models`, { headers: this.headers });
      if (!res.ok) return [];
      const data = await res.json();
      return data.models ?? [];
    } catch {
      return [];
    }
  }

  async getAgents() {
    const res = await fetch(`${this.baseUrl}/api/v1/agents`, { headers: this.headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async checkHealth(): Promise<{ ok: boolean; model?: string }> {
    try {
      const res = await fetch(`${this.baseUrl}/health`, {
        signal: AbortSignal.timeout(5000),
      });
      if (!res.ok) return { ok: false };
      const data = await res.json();
      return { ok: true, model: data.model };
    } catch {
      return { ok: false };
    }
  }

  connectWebSocket(sessionId: string): WebSocket {
    const wsUrl = this.baseUrl
      .replace("http://", "ws://")
      .replace("https://", "wss://");
    return new WebSocket(`${wsUrl}/ws/chat/${sessionId}`);
  }
}
