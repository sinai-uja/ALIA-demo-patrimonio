const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api/v1";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json() as Promise<T>;
}

// ── RAG ──────────────────────────────────────────────────────────────────────
export interface RagSource {
  title: string;
  url: string;
  score: number;
  heritage_type: string;
  province: string;
}

export interface RagResponse {
  answer: string;
  sources: RagSource[];
  query: string;
}

export const rag = {
  query: (params: {
    query: string;
    top_k?: number;
    heritage_type_filter?: string | null;
    province_filter?: string | null;
  }) =>
    apiFetch<RagResponse>("/rag/query", {
      method: "POST",
      body: JSON.stringify(params),
    }),
};

// ── Chat ──────────────────────────────────────────────────────────────────────
export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: RagSource[];
  created_at: string;
}

export const chat = {
  createSession: (title?: string) =>
    apiFetch<Session>("/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title: title ?? "Nueva conversación" }),
    }),

  listSessions: () => apiFetch<Session[]>("/chat/sessions"),

  deleteSession: (id: string) =>
    apiFetch<void>(`/chat/sessions/${id}`, { method: "DELETE" }),

  getMessages: (sessionId: string) =>
    apiFetch<Message[]>(`/chat/sessions/${sessionId}/messages`),

  sendMessage: (
    sessionId: string,
    params: {
      content: string;
      top_k?: number;
      heritage_type_filter?: string | null;
      province_filter?: string | null;
    }
  ) =>
    apiFetch<Message>(`/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify(params),
    }),
};

// ── Routes ────────────────────────────────────────────────────────────────────
export interface RouteStop {
  order: number;
  title: string;
  heritage_type: string;
  province: string;
  municipality: string | null;
  url: string;
  description: string;
  visit_duration_minutes: number;
}

export interface VirtualRoute {
  id: string;
  title: string;
  province: string;
  stops: RouteStop[];
  total_duration_minutes: number;
  narrative: string;
  created_at: string;
}

export const routes = {
  generate: (params: {
    province: string;
    num_stops?: number;
    heritage_types?: string[];
    user_interests?: string;
  }) =>
    apiFetch<VirtualRoute>("/routes/generate", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  list: (province?: string) =>
    apiFetch<VirtualRoute[]>(`/routes${province ? `?province=${province}` : ""}`),

  get: (id: string) => apiFetch<VirtualRoute>(`/routes/${id}`),

  guide: (routeId: string, question: string) =>
    apiFetch<{ answer: string; sources: RagSource[] }>(
      `/routes/${routeId}/guide`,
      { method: "POST", body: JSON.stringify({ question }) }
    ),
};

// ── Accessibility ─────────────────────────────────────────────────────────────
export interface SimplifyResponse {
  original_text: string;
  simplified_text: string;
  level: string;
  document_id: string | null;
}

export const accessibility = {
  simplify: (params: {
    text: string;
    level?: "basic" | "intermediate";
    document_id?: string | null;
  }) =>
    apiFetch<SimplifyResponse>("/accessibility/simplify", {
      method: "POST",
      body: JSON.stringify(params),
    }),
};
