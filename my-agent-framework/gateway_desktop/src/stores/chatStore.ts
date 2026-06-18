import { create } from "zustand";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  isStreaming?: boolean;
  timestamp: Date;
}

interface ChatState {
  messages: Message[];
  sessionId: string | null;
  isLoading: boolean;
  error: string | null;
  addMessage: (msg: Omit<Message, "id" | "timestamp">) => Message;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  clearSession: () => void;
  setLoading: (v: boolean) => void;
  setError: (e: string | null) => void;
  setSessionId: (id: string | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  sessionId: null,
  isLoading: false,
  error: null,

  addMessage: (msg) => {
    const message: Message = {
      id: Date.now().toString(),
      timestamp: new Date(),
      ...msg,
    };
    set((s) => ({ messages: [...s.messages, message] }));
    return message;
  },

  updateMessage: (id, updates) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    })),

  clearSession: () =>
    set({ messages: [], sessionId: null, error: null, isLoading: false }),

  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  setSessionId: (sessionId) => set({ sessionId }),
}));
