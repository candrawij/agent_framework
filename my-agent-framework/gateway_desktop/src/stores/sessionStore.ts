import { create } from "zustand";

export interface Session {
  id: string;
  name: string;
  createdAt: Date;
  lastMessage?: string;
  lastMessageAt?: Date;
}

interface SessionState {
  sessions: Session[];
  activeSessionId: string | null;

  createSession: (name?: string) => Session;
  deleteSession: (id: string) => void;
  setActiveSession: (id: string | null) => void;
  updateSessionPreview: (id: string, lastMessage: string) => void;
  renameSession: (id: string, name: string) => void;
}

function genId() {
  return Math.random().toString(36).slice(2, 10);
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  activeSessionId: null,

  createSession: (name) => {
    const session: Session = {
      id: genId(),
      name: name ?? `Sesi ${get().sessions.length + 1}`,
      createdAt: new Date(),
    };
    set((s) => ({
      sessions: [session, ...s.sessions],
      activeSessionId: session.id,
    }));
    return session;
  },

  deleteSession: (id) => {
    set((s) => {
      const remaining = s.sessions.filter((sess) => sess.id !== id);
      const newActive =
        s.activeSessionId === id
          ? remaining[0]?.id ?? null
          : s.activeSessionId;
      return { sessions: remaining, activeSessionId: newActive };
    });
  },

  setActiveSession: (id) => set({ activeSessionId: id }),

  updateSessionPreview: (id, lastMessage) => {
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id
          ? { ...sess, lastMessage: lastMessage.slice(0, 60), lastMessageAt: new Date() }
          : sess
      ),
    }));
  },

  renameSession: (id, name) => {
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id ? { ...sess, name } : sess
      ),
    }));
  },
}));
