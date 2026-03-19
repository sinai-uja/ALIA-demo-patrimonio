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
    query: string;
    num_stops?: number;
    heritage_type_filter?: string[] | null;
    province_filter?: string[] | null;
    municipality_filter?: string[] | null;
  }) =>
    apiFetch<VirtualRoute>("/routes/generate", {
      method: "POST",
      body: JSON.stringify(params),
    }),

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

  guide: (routeId: string, question: string) =>
    apiFetch<{ answer: string; sources: RagSource[] }>(
      `/routes/${routeId}/guide`,
      { method: "POST", body: JSON.stringify({ question }) }
    ),
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
  }) =>
    apiFetch<SimilaritySearchResponse>("/search/similarity", {
      method: "POST",
      body: JSON.stringify(params),
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
