const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18080/api/v1";

function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)token=([^;]*)/);
  return match ? match[1] : null;
}

export class ValidationError extends Error {
  fields: Record<string, string>;
  constructor(fields: Record<string, string>) {
    super(Object.values(fields).join("; "));
    this.fields = fields;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (res.status === 401) {
    if (typeof document !== "undefined") {
      document.cookie = "token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
      localStorage.removeItem("refreshToken");
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const text = await res.text();
    if (res.status === 422) {
      try {
        const json = JSON.parse(text);
        if (Array.isArray(json.detail)) {
          const fields: Record<string, string> = {};
          for (const e of json.detail as { loc: string[]; msg: string }[]) {
            const field = e.loc[e.loc.length - 1] ?? "general";
            // Strip Pydantic v2 "Value error, " prefix if present
            const msg = e.msg.replace(/^Value error,\s*/i, "");
            fields[field] = msg;
          }
          throw new ValidationError(fields);
        }
      } catch (e) {
        if (e instanceof ValidationError) throw e;
      }
    }
    try {
      const json = JSON.parse(text);
      if (Array.isArray(json.detail)) {
        throw new Error(json.detail.map((e: { msg: string }) => e.msg.replace(/^Value error,\s*/i, "")).join("; "));
      }
      if (typeof json.detail === "string") throw new Error(json.detail);
    } catch (e) {
      if (e instanceof Error && e.message !== text) throw e;
    }
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── RAG ──────────────────────────────────────────────────────────────────────
export interface RagSource {
  title: string;
  url: string;
  score: number;
  heritage_type: string;
  province: string;
  municipality?: string | null;
  metadata?: Record<string, unknown> | null;
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

  updateSession: (id: string, title: string) =>
    apiFetch<Session>(`/chat/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),

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
  heritage_asset_id?: string | null;
  narrative_segment?: string;
  image_url?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface VirtualRoute {
  id: string;
  title: string;
  province: string;
  stops: RouteStop[];
  narrative: string;
  introduction?: string | null;
  conclusion?: string | null;
  created_at: string;
}

export type GenerateRouteParams = {
  query: string;
  num_stops?: number;
  heritage_type_filter?: string[] | null;
  province_filter?: string[] | null;
  municipality_filter?: string[] | null;
};

export const routes = {
  generate: (params: GenerateRouteParams, signal?: AbortSignal) =>
    apiFetch<VirtualRoute>("/routes/generate", {
      method: "POST",
      body: JSON.stringify(params),
      signal,
    }),

  generateStream: async (
    params: GenerateRouteParams,
    signal: AbortSignal | undefined,
    onEvent: (event: { event: string; data: Record<string, unknown> }) => void,
  ): Promise<void> => {
    const token = getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}/routes/generate/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify(params),
      signal,
    });

    if (res.status === 401) {
      if (typeof document !== "undefined") {
        document.cookie = "token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
        localStorage.removeItem("refreshToken");
        window.location.href = "/login";
      }
      throw new Error("Unauthorized");
    }

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || res.statusText);
    }

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop()!; // keep incomplete line in buffer

        let currentEvent = "message";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent({ event: currentEvent, data });
            } catch {
              // ignore malformed JSON
            }
            currentEvent = "message";
          }
          // empty lines reset event type per SSE spec
          if (line === "") {
            currentEvent = "message";
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  suggestions: (query: string) =>
    apiFetch<SuggestionResponse>(
      `/routes/suggestions?query=${encodeURIComponent(query)}`,
    ),

  filters: (provinces?: string[]) => {
    const params = new URLSearchParams();
    if (provinces?.length) {
      for (const p of provinces) params.append("province", p);
    }
    const qs = params.toString();
    return apiFetch<FilterValues>(`/routes/filters${qs ? `?${qs}` : ""}`);
  },

  list: (province?: string) =>
    apiFetch<VirtualRoute[]>(`/routes${province ? `?province=${province}` : ""}`),

  get: (id: string) => apiFetch<VirtualRoute>(`/routes/${id}`),

  delete: (id: string) => apiFetch<void>(`/routes/${id}`, { method: "DELETE" }),

  guide: (
    routeId: string,
    question: string,
    history?: { role: string; content: string }[],
  ) =>
    apiFetch<{ answer: string; sources: RagSource[] }>(
      `/routes/${routeId}/guide`,
      { method: "POST", body: JSON.stringify({ question, history: history ?? [] }) }
    ),

  removeStop: (routeId: string, stopOrder: number) =>
    apiFetch<VirtualRoute>(`/routes/${routeId}/stops/${stopOrder}`, {
      method: "DELETE",
    }),

  addStop: (routeId: string, documentId: string, position?: number) =>
    apiFetch<VirtualRoute>(`/routes/${routeId}/stops`, {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, position }),
    }),

  addStopBackground: (routeId: string, documentId: string) =>
    apiFetch<{ status: string; message: string }>(`/routes/${routeId}/stops`, {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, background: true }),
    }),
};

// ── Heritage Assets ──────────────────────────────────────────────────────────
export interface ImageInfo {
  id?: string | null;
  title?: string | null;
  author?: string | null;
  date?: string | null;
  url?: string | null;
}

export interface BibliographyEntry {
  title?: string | null;
  author?: string | null;
  publisher?: string | null;
  year?: string | null;
  isbn?: string | null;
  pages?: string | null;
  location?: string | null;
}

export interface TypologyInfo {
  typology?: string | null;
  style?: string | null;
  period?: string | null;
  chrono_start?: string | null;
  chrono_end?: string | null;
}

export interface RelatedAsset {
  code?: string | null;
  denomination?: string | null;
  relation_type?: string | null;
}

export interface InmuebleDetails {
  type: "inmueble";
  code?: string | null;
  other_denominations?: string | null;
  characterisation?: string | null;
  postal_address?: string | null;
  historical_data?: string | null;
  description?: string | null;
  protection?: string | null;
  typologies: TypologyInfo[];
  images: ImageInfo[];
  bibliography: BibliographyEntry[];
  related_assets: RelatedAsset[];
  historical_periods: string[];
}

export interface MuebleDetails {
  type: "mueble";
  code?: string | null;
  other_denominations?: string | null;
  characterisation?: string | null;
  measurements?: string | null;
  chronology?: string | null;
  description?: string | null;
  protection?: string | null;
  typologies: TypologyInfo[];
  images: ImageInfo[];
  bibliography: BibliographyEntry[];
  related_assets: RelatedAsset[];
}

export interface InmaterialDetails {
  type: "inmaterial";
  code?: string | null;
  other_denominations?: string | null;
  scope?: string | null;
  framework_activities?: string | null;
  activity_dates?: string | null;
  periodicity?: string | null;
  typologies_text?: string | null;
  district?: string | null;
  local_entity?: string | null;
  description?: string | null;
  development?: string | null;
  spatial_description?: string | null;
  agents_description?: string | null;
  evolution?: string | null;
  origins?: string | null;
  preparations?: string | null;
  clothing?: string | null;
  instruments?: string | null;
  transmission_mode?: string | null;
  transformations?: string | null;
  protection?: string | null;
  typologies: TypologyInfo[];
  images: ImageInfo[];
  bibliography: BibliographyEntry[];
  related_assets: RelatedAsset[];
}

export interface PaisajeDetails {
  type: "paisaje";
  pdf_url?: string | null;
  search_terms: string[];
}

export type HeritageDetails =
  | InmuebleDetails
  | MuebleDetails
  | InmaterialDetails
  | PaisajeDetails;

export interface HeritageAsset {
  id: string;
  heritage_type: string;
  denomination?: string | null;
  province?: string | null;
  municipality?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  image_url?: string | null;
  image_ids: string[];
  protection?: string | null;
  details?: HeritageDetails | null;
}

export interface HeritageAssetSummary {
  id: string;
  heritage_type: string;
  denomination?: string | null;
  province?: string | null;
  municipality?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  image_url?: string | null;
  protection?: string | null;
}

export interface HeritageAssetList {
  items: HeritageAssetSummary[];
  total: number;
  limit: number;
  offset: number;
}

export const heritage = {
  list: (params?: {
    heritage_type?: string;
    province?: string;
    municipality?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.heritage_type) searchParams.set("heritage_type", params.heritage_type);
    if (params?.province) searchParams.set("province", params.province);
    if (params?.municipality) searchParams.set("municipality", params.municipality);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    const qs = searchParams.toString();
    return apiFetch<HeritageAssetList>(`/heritage${qs ? `?${qs}` : ""}`);
  },

  get: (id: string) => apiFetch<HeritageAsset>(`/heritage/${id}`),
};

// ── Search ───────────────────────────────────────────────────────────────────
export interface ChunkHit {
  chunk_id: string;
  content: string;
  score: number;
}

export interface SearchResult {
  document_id: string;
  title: string;
  heritage_type: string;
  province: string;
  municipality: string | null;
  url: string;
  best_score: number;
  chunks: ChunkHit[];
  denomination: string | null;
  description: string | null;
  latitude: number | null;
  longitude: number | null;
  image_url: string | null;
  protection: string | null;
}

export interface SimilaritySearchResponse {
  results: SearchResult[];
  query: string;
  total_results: number;
  page: number;
  page_size: number;
  total_pages: number;
  search_id: string;
}

export interface DetectedEntity {
  entity_type: "province" | "municipality" | "heritage_type";
  value: string;
  display_label: string;
  matched_text: string;
}

export interface SuggestionResponse {
  query: string;
  search_label: string;
  detected_entities: DetectedEntity[];
}

export interface FilterValues {
  heritage_types: string[];
  provinces: string[];
  municipalities: string[];
}

export const search = {
  similarity: (params: {
    query: string;
    page?: number;
    page_size?: number;
    heritage_type_filter?: string[] | null;
    province_filter?: string[] | null;
    municipality_filter?: string[] | null;
  }, signal?: AbortSignal) =>
    apiFetch<SimilaritySearchResponse>("/search/similarity", {
      method: "POST",
      body: JSON.stringify(params),
      signal,
    }),

  suggestions: (query: string) =>
    apiFetch<SuggestionResponse>(
      `/search/suggestions?query=${encodeURIComponent(query)}`
    ),

  filters: (provinces?: string[]) => {
    const params = new URLSearchParams();
    if (provinces?.length) {
      for (const p of provinces) params.append("province", p);
    }
    const qs = params.toString();
    return apiFetch<FilterValues>(`/search/filters${qs ? `?${qs}` : ""}`);
  },
};

// ── Feedback ──────────────────────────────────────────────────────────────────
export interface FeedbackResponse {
  id: string;
  target_type: string;
  target_id: string;
  value: number;
  created_at: string;
}

export interface FeedbackBatchResponse {
  feedbacks: Record<string, number>;
}

export const feedback = {
  submit: (params: {
    target_type: "route" | "search" | "search_result";
    target_id: string;
    value: 1 | -1;
    metadata?: Record<string, unknown>;
  }) =>
    apiFetch<FeedbackResponse>("/feedback", {
      method: "PUT",
      body: JSON.stringify(params),
    }),

  delete: (targetType: string, targetId: string) =>
    apiFetch<void>(`/feedback/${targetType}/${targetId}`, { method: "DELETE" }),

  get: (targetType: string, targetId: string) =>
    apiFetch<FeedbackResponse>(`/feedback/${targetType}/${targetId}`),

  batch: (targetType: string, targetIds: string[]) => {
    const params = new URLSearchParams();
    params.set("target_type", targetType);
    for (const id of targetIds) params.append("target_ids", id);
    return apiFetch<FeedbackBatchResponse>(`/feedback/batch?${params}`);
  },
};

// ── Health ────────────────────────────────────────────────────────────────────
export interface ServiceStatus {
  embedding: { status: "ok" | "warming" | "down" | "local" | "unknown"; is_cloud_run: boolean };
  llm: { status: "ok" | "warming" | "down" | "local" | "external" | "unknown"; is_cloud_run: boolean };
  provider: string;
  last_check: string | null;
}

export const health = {
  status: () => apiFetch<ServiceStatus>("/health/services"),
  keepalive: () => apiFetch<ServiceStatus>("/health/keepalive", { method: "POST" }),
};

// ── Auth ──────────────────────────────────────────────────────────────────────
export interface UserInfo {
  id: string;
  username: string;
  profile_type: string | null;
  is_root_admin: boolean;
}

export interface ProfileType {
  name: string;
}

export const auth = {
  getMe: () => apiFetch<UserInfo>("/auth/me"),

  updateProfileType: (profileType: string) =>
    apiFetch<UserInfo>("/auth/profile-type", {
      method: "PUT",
      body: JSON.stringify({ profile_type: profileType }),
    }),

  getProfileTypes: () => apiFetch<ProfileType[]>("/auth/profile-types"),
};

// ── Admin ────────────────────────────────────────────────────────────────────
export interface AdminUser {
  id: string;
  username: string;
  profile_type: string | null;
  created_at: string;
}

export interface AdminProfileType {
  id: string;
  name: string;
  user_count: number;
}

export const admin = {
  listUsers: () => apiFetch<AdminUser[]>("/admin/users"),
  createUser: (data: { username: string; password: string; profile_type?: string | null }) =>
    apiFetch<AdminUser>("/admin/users", { method: "POST", body: JSON.stringify(data) }),
  updateUser: (id: string, data: { password?: string | null; profile_type?: string | null }) =>
    apiFetch<AdminUser>(`/admin/users/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteUser: (id: string) =>
    apiFetch<void>(`/admin/users/${id}`, { method: "DELETE" }),
  profileTypes: {
    list: () => apiFetch<AdminProfileType[]>("/admin/profile-types"),
    create: (name: string) =>
      apiFetch<AdminProfileType>("/admin/profile-types", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    rename: (id: string, name: string) =>
      apiFetch<AdminProfileType>(`/admin/profile-types/${id}`, {
        method: "PUT",
        body: JSON.stringify({ name }),
      }),
    delete: (id: string) =>
      apiFetch<void>(`/admin/profile-types/${id}`, { method: "DELETE" }),
  },
};

// ── Admin Traces ──────────────────────────────────────────────────────────────
export interface TraceResultItem {
  rank: number;
  score: number;
  title: string;
  heritage_type: string;
  province: string;
  document_id?: string;
}

export interface TracePipelineStep {
  step: string;
  elapsed_ms?: number | null;
  input?: Record<string, unknown> | null;
  output?: Record<string, unknown> | null;
  results?: TraceResultItem[] | null;
}

export interface TraceSummary {
  id: string;
  execution_type: string;
  user_id: string;
  username: string;
  user_profile_type: string | null;
  query: string;
  pipeline_mode: string | null;
  status: string;
  created_at: string;
  total_results: number;
  top_score: number | null;
  elapsed_ms: number | null;
  feedback_value: number | null;
}

export interface TraceDetail extends TraceSummary {
  filters: Record<string, unknown> | null;
  steps: TracePipelineStep[];
  llm_response: string | null;
  result_feedbacks: Record<string, number> | null;
}

export interface TraceListResponse {
  traces: TraceSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TraceListParams {
  type?: string;
  since?: string;
  until?: string;
  user_id?: string;
  query?: string;
  page?: number;
  page_size?: number;
}

export const traces = {
  list: (params: TraceListParams) => {
    const searchParams = new URLSearchParams();
    if (params.type) searchParams.set("type", params.type);
    if (params.since) searchParams.set("since", params.since);
    if (params.until) searchParams.set("until", params.until);
    if (params.user_id) searchParams.set("user_id", params.user_id);
    if (params.query) searchParams.set("query", params.query);
    if (params.page) searchParams.set("page", String(params.page));
    if (params.page_size) searchParams.set("page_size", String(params.page_size));
    const qs = searchParams.toString();
    return apiFetch<TraceListResponse>(`/admin/traces${qs ? `?${qs}` : ""}`);
  },

  get: (traceId: string) => apiFetch<TraceDetail>(`/admin/traces/${traceId}`),
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
