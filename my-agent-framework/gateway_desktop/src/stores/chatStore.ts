import { create } from "zustand";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  isStreaming?: boolean;
  timestamp: Date;
}

// Map dari sessionId → daftar pesan
type SessionMessages = Record<string, Message[]>;

interface ChatState {
  // Per-session messages
  messagesBySession: SessionMessages;
  isLoading: boolean;
  isStreaming: boolean;
  status: "idle" | "thinking" | "responding" | "error";
  error: string | null;
  abortController: AbortController | null;

  // Actions
  getMessages: (sessionId: string) => Message[];
  addMessage: (sessionId: string, msg: Omit<Message, "id" | "timestamp">) => Message;
  updateMessage: (sessionId: string, id: string, updates: Partial<Message>) => void;
  appendToMessage: (sessionId: string, id: string, chunk: string) => void;
  clearSession: (sessionId: string) => void;
  setLoading: (v: boolean) => void;
  setStreaming: (v: boolean) => void;
  setStatus: (s: ChatState["status"]) => void;
  setError: (e: string | null) => void;
  setAbortController: (ctrl: AbortController | null) => void;
  stopStreaming: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messagesBySession: {},
  isLoading: false,
  isStreaming: false,
  status: "idle",
  error: null,
  abortController: null,

  getMessages: (sessionId) => get().messagesBySession[sessionId] ?? [],

  addMessage: (sessionId, msg) => {
    const message: Message = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      timestamp: new Date(),
      ...msg,
    };
    set((s) => ({
      messagesBySession: {
        ...s.messagesBySession,
        [sessionId]: [...(s.messagesBySession[sessionId] ?? []), message],
      },
    }));
    return message;
  },

  updateMessage: (sessionId, id, updates) =>
    set((s) => ({
      messagesBySession: {
        ...s.messagesBySession,
        [sessionId]: (s.messagesBySession[sessionId] ?? []).map((m) =>
          m.id === id ? { ...m, ...updates } : m
        ),
      },
    })),

  appendToMessage: (sessionId, id, chunk) =>
    set((s) => ({
      messagesBySession: {
        ...s.messagesBySession,
        [sessionId]: (s.messagesBySession[sessionId] ?? []).map((m) =>
          m.id === id ? { ...m, content: m.content + chunk } : m
        ),
      },
    })),

  clearSession: (sessionId) =>
    set((s) => {
      const next = { ...s.messagesBySession };
      delete next[sessionId];
      return { messagesBySession: next };
    }),

  setLoading: (isLoading) => set({ isLoading }),
  setStreaming: (isStreaming) => set({ isStreaming }),
  setStatus: (status) => set({ status }),
  setError: (error) => set({ error }),
  setAbortController: (abortController) => set({ abortController }),

  stopStreaming: () => {
    const { abortController } = get();
    abortController?.abort();
    set({ abortController: null, isLoading: false, isStreaming: false, status: "idle" });
  },
}));
