// API Client for Agent Framework
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

export class ApiClient {
  private baseUrl: string;
  private authToken: string | null;

  constructor(baseUrl: string, authToken: string | null = null) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.authToken = authToken;
  }

  private get headers(): HeadersInit {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this.authToken) headers["Authorization"] = `Bearer ${this.authToken}`;
    return headers;
  }

  async chat(messages: ChatMessage[], options: {
    sessionId?: string;
    temperature?: number;
  } = {}): Promise<ChatResponse> {
    const res = await fetch(`${this.baseUrl}/api/v1/chat`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({
        messages,
        session_id: options.sessionId,
        temperature: options.temperature ?? 0.7,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return res.json();
  }

  async getAgents() {
    const res = await fetch(`${this.baseUrl}/api/v1/agents`, { headers: this.headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async checkHealth(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/health`, { signal: AbortSignal.timeout(5000) });
      return res.ok;
    } catch {
      return false;
    }
  }

  connectWebSocket(sessionId: string): WebSocket {
    const wsUrl = this.baseUrl
      .replace("http://", "ws://")
      .replace("https://", "wss://");
    return new WebSocket(`${wsUrl}/ws/chat/${sessionId}`);
  }
}
