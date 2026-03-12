import { create } from "zustand";
import { chat as chatApi, type Session, type Message } from "@/lib/api";

function defaultTitle(): string {
  return new Date().toLocaleString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface ChatState {
  sessions: Session[];
  activeSessionId: string | null;
  messages: Message[];
  loading: boolean;
  sending: boolean;

  loadSessions: () => Promise<void>;
  createSession: (title?: string) => Promise<Session>;
  selectSession: (id: string) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
  sendMessage: (content: string, filters?: { heritage_type?: string; province?: string }) => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  loading: false,
  sending: false,

  loadSessions: async () => {
    set({ loading: true });
    try {
      const sessions = await chatApi.listSessions();
      set({ sessions });
    } finally {
      set({ loading: false });
    }
  },

  createSession: async (title) => {
    const session = await chatApi.createSession(title ?? defaultTitle());
    set((s) => ({ sessions: [session, ...s.sessions], activeSessionId: session.id, messages: [] }));
    return session;
  },

  selectSession: async (id) => {
    set({ loading: true, activeSessionId: id });
    try {
      const messages = await chatApi.getMessages(id);
      set({ messages });
    } finally {
      set({ loading: false });
    }
  },

  deleteSession: async (id) => {
    await chatApi.deleteSession(id);
    set((s) => {
      const sessions = s.sessions.filter((x) => x.id !== id);
      const activeSessionId = s.activeSessionId === id ? (sessions[0]?.id ?? null) : s.activeSessionId;
      return { sessions, activeSessionId, messages: activeSessionId !== id ? s.messages : [] };
    });
  },

  renameSession: async (id, title) => {
    const updated = await chatApi.updateSession(id, title);
    set((s) => ({
      sessions: s.sessions.map((x) => (x.id === id ? updated : x)),
    }));
  },

  sendMessage: async (content, filters) => {
    const { activeSessionId } = get();
    if (!activeSessionId) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      sources: [],
      created_at: new Date().toISOString(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], sending: true }));

    try {
      const reply = await chatApi.sendMessage(activeSessionId, {
        content,
        heritage_type_filter: filters?.heritage_type ?? null,
        province_filter: filters?.province ?? null,
      });
      set((s) => ({ messages: [...s.messages, reply] }));
    } finally {
      set({ sending: false });
    }
  },
}));
