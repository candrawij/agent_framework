// WebSocket Event Types — shared between backend and frontend
export interface WSMessage {
  type: WSEventType;
  session_id: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

export type WSEventType =
  | "token"          // Streaming token dari model
  | "tool_call"      // Agent memanggil tool
  | "tool_result"    // Hasil tool
  | "agent_start"    // Agent mulai bekerja
  | "agent_done"     // Agent selesai
  | "error"          // Error
  | "ping"           // Keepalive
  | "pong";

export interface TokenEvent {
  content: string;
  model: string;
  is_final: boolean;
}

export interface ToolCallEvent {
  tool_name: string;
  tool_input: Record<string, unknown>;
  iteration: number;
}

export interface ToolResultEvent {
  tool_name: string;
  success: boolean;
  output: string;
  duration_ms: number;
}
