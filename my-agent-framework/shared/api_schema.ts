// API Schema Types — TypeScript types for REST API
export interface ChatMessage {
  role: "user" | "assistant" | "system" | "tool";
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  session_id?: string;
  stream?: boolean;
  agent_name?: string;
  temperature?: number;
}

export interface ChatResponse {
  content: string;
  session_id: string;
  model: string;
  agent_used?: string;
}

export interface Agent {
  name: string;
  description: string;
  enabled: boolean;
  tools: string[];
}

export interface ModelInfo {
  adapter: string;
  model: string;
  available: boolean;
}

export interface HealthResponse {
  status: "ok" | "degraded" | "error";
  version: string;
}
