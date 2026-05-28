import { create } from "zustand";
import {
  heritage as heritageApi,
  search as searchApi,
  type HeritageAsset,
  type SearchResult,
  type SuggestionResponse,
  type DetectedEntity,
  type FilterValues,
} from "@/lib/api";
import { type ActiveFilter, collectFilters } from "@/lib/filterUtils";
import { minDelay } from "@/lib/minDelay";
import { useFeedbackStore } from "@/store/feedback";

interface SearchState {
  query: string;
  results: SearchResult[];
  totalResults: number;
  page: number;
  pageSize: number;
  totalPages: number;
  activeFilters: ActiveFilter[];
  /** Cosine distance cutoff sent to the backend. Lower = stricter. */
  scoreThreshold: number;
  /** Lexical weight in [0, 1] for hybrid search. Semantic weight = 1 - lexicalWeight. */
  lexicalWeight: number;
  /** Full suggestion response (for dropdown). Cleared when dropdown closes. */
  suggestions: SuggestionResponse | null;
  /** Detected entities persisted for overlay highlights. Only cleared on new query. */
  detectedEntities: DetectedEntity[];
  filterValues: FilterValues | null;
  loading: boolean;
  suggestionsLoading: boolean;
  hasSearched: boolean;

  // Search ID returned by backend
  searchId: string | null;

  // Detail panel
  selectedAssetId: string | null;
  selectedAsset: HeritageAsset | null;
  detailLoading: boolean;

  setQuery: (q: string) => void;
  setScoreThreshold: (value: number) => void;
  setLexicalWeight: (value: number) => void;
  syncFiltersWithQuery: (q: string) => void;
  performSearch: (page?: number) => Promise<void>;
  goToPage: (page: number) => Promise<void>;
  fetchSuggestions: (q: string) => Promise<void>;
  loadFilterValues: (provinces?: string[]) => Promise<void>;
  addFilter: (filter: ActiveFilter) => void;
  addFilters: (filters: ActiveFilter[]) => void;
  removeFilter: (filter: ActiveFilter) => void;
  clearFilters: () => void;
  clearSuggestions: () => void;
  openDetail: (documentId: string) => Promise<void>;
  closeDetail: () => void;
}

const SEARCH_THRESHOLD_STORAGE_KEY = "search:scoreThreshold";
const DEFAULT_SEARCH_THRESHOLD = 0.5;

const SEARCH_LEXICAL_WEIGHT_STORAGE_KEY = "search:lexicalWeight";
const DEFAULT_LEXICAL_WEIGHT = (() => {
  const raw = process.env.NEXT_PUBLIC_DEFAULT_LEXICAL_WEIGHT;
  const parsed = Number(raw ?? "0.7");
  if (!Number.isFinite(parsed)) return 0.7;
  if (parsed < 0 || parsed > 1) return 0.7;
  return parsed;
})();

function loadInitialThreshold(): number {
  if (typeof window === "undefined") return DEFAULT_SEARCH_THRESHOLD;
  try {
    const raw = window.localStorage.getItem(SEARCH_THRESHOLD_STORAGE_KEY);
    if (raw === null) return DEFAULT_SEARCH_THRESHOLD;
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) return DEFAULT_SEARCH_THRESHOLD;
    if (parsed < 0.1 || parsed > 1.0) return DEFAULT_SEARCH_THRESHOLD;
    return parsed;
  } catch {
    return DEFAULT_SEARCH_THRESHOLD;
  }
}

function loadInitialLexicalWeight(): number {
  if (typeof window === "undefined") return DEFAULT_LEXICAL_WEIGHT;
  try {
    const raw = window.localStorage.getItem(SEARCH_LEXICAL_WEIGHT_STORAGE_KEY);
    if (raw === null) return DEFAULT_LEXICAL_WEIGHT;
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) return DEFAULT_LEXICAL_WEIGHT;
    if (parsed < 0 || parsed > 1) return DEFAULT_LEXICAL_WEIGHT;
    return parsed;
  } catch {
    return DEFAULT_LEXICAL_WEIGHT;
  }
}

/** Extract numeric asset ID from document_id (e.g. "ficha-inmueble-20831" → "20831"). */
function extractAssetId(documentId: string): string {
  return documentId.replace(/^ficha-\w+-/, "");
}

/** Clean query whitespace for API submission. */
function buildCleanQuery(query: string): string {
  return query.replace(/\s{2,}/g, " ").trim();
}

let _searchController: AbortController | null = null;
let _searchDebounce: ReturnType<typeof setTimeout> | null = null;

export const useSearchStore = create<SearchState>((set, get) => ({
  query: "",
  results: [],
  totalResults: 0,
  page: 1,
  pageSize: 10,
  totalPages: 0,
  activeFilters: [],
  scoreThreshold: loadInitialThreshold(),
  lexicalWeight: loadInitialLexicalWeight(),
  suggestions: null,
  detectedEntities: [],
  filterValues: null,
  loading: false,
  suggestionsLoading: false,
  hasSearched: false,

  // Search ID returned by backend
  searchId: null,

  // Detail panel
  selectedAssetId: null,
  selectedAsset: null,
  detailLoading: false,

  setQuery: (q) => set({ query: q }),

  setScoreThreshold: (value) => {
    const clamped = Math.min(1.0, Math.max(0.1, Math.round(value * 100) / 100));
    set({ scoreThreshold: clamped });
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(SEARCH_THRESHOLD_STORAGE_KEY, String(clamped));
      } catch {
        /* ignore storage quota / disabled storage */
      }
    }
    if (get().query.trim() && get().hasSearched) {
      get().performSearch();
    }
  },

  setLexicalWeight: (value) => {
    const clamped = Math.min(1.0, Math.max(0.0, Math.round(value * 100) / 100));
    set({ lexicalWeight: clamped });
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(SEARCH_LEXICAL_WEIGHT_STORAGE_KEY, String(clamped));
      } catch {
        /* ignore storage quota / disabled storage */
      }
    }
    if (get().query.trim() && get().hasSearched) {
      get().performSearch();
    }
  },

  syncFiltersWithQuery: (q: string) => {
    const { activeFilters } = get();
    if (activeFilters.length === 0) return;
    const lower = q.toLowerCase();
    const remaining = activeFilters.filter((f) => {
      if (!f.matchedText) return true;
      return lower.includes(f.matchedText.toLowerCase());
    });
    if (remaining.length !== activeFilters.length) {
      set({ activeFilters: remaining });
    }
  },

  performSearch: async (page?: number) => {
    const { query, activeFilters, pageSize, scoreThreshold, lexicalWeight } = get();
    if (!query.trim()) return;

    const cleanQuery = buildCleanQuery(query);
    if (!cleanQuery) return;

    // Debounce to prevent duplicate requests from React strict mode
    if (_searchDebounce) clearTimeout(_searchDebounce);
    _searchController?.abort();
    const controller = new AbortController();
    _searchController = controller;

    const targetPage = page ?? 1;
    set({
      loading: true,
      hasSearched: true,
      selectedAssetId: null,
      selectedAsset: null,
    });

    // Wait one microtask to let any duplicate call abort this one first
    await new Promise((r) => { _searchDebounce = setTimeout(r, 50); });
    if (controller.signal.aborted) { set({ loading: false }); return; }

    try {
      const filters = collectFilters(activeFilters);
      const res = await minDelay(searchApi.similarity({
        query: cleanQuery,
        page: targetPage,
        page_size: pageSize,
        score_threshold: scoreThreshold,
        lexical_weight: lexicalWeight,
        ...filters,
      }, controller.signal));
      if (controller.signal.aborted) return;
      set({
        results: res.results,
        totalResults: res.total_results,
        page: res.page,
        totalPages: res.total_pages,
        searchId: res.search_id,
      });

      // Pre-load feedback state for all results on this page (composite key: searchId:documentId)
      const feedbackIds = res.results.map((r: SearchResult) => `${res.search_id}:${r.document_id}`);
      useFeedbackStore.getState().loadFeedbackBatch("search_result", feedbackIds);
    } catch (err) {
      if (controller.signal.aborted) return;
      set({ results: [], totalResults: 0, page: 1, totalPages: 0, searchId: null });
    } finally {
      if (_searchController === controller) {
        set({ loading: false });
      }
    }
  },

  goToPage: async (page: number) => {
    set({ selectedAssetId: null, selectedAsset: null });
    await get().performSearch(page);
  },

  fetchSuggestions: async (q) => {
    if (!q.trim() || q.trim().length < 2) {
      set({ suggestions: null, detectedEntities: [] });
      return;
    }
    set({ suggestionsLoading: true });
    try {
      const res = await searchApi.suggestions(q.trim());
      set({ suggestions: res, detectedEntities: res.detected_entities });
    } catch {
      set({ suggestions: null });
    } finally {
      set({ suggestionsLoading: false });
    }
  },

  loadFilterValues: async (provinces) => {
    try {
      const values = await searchApi.filters(provinces);
      set({ filterValues: values });
    } catch {
      /* ignore */
    }
  },

  addFilter: (filter) => {
    const { activeFilters } = get();
    const exists = activeFilters.some(
      (f) => f.type === filter.type && f.value === filter.value
    );
    if (exists) return;
    const updated = [...activeFilters, filter];
    set({ activeFilters: updated });
    if (filter.type === "province") {
      const provinces = updated.filter((f) => f.type === "province").map((f) => f.value);
      get().loadFilterValues(provinces);
    }
    if (get().query.trim()) {
      get().performSearch();
    }
  },

  addFilters: (filters) => {
    const { activeFilters } = get();
    const newFilters = filters.filter(
      (f) => !activeFilters.some((a) => a.type === f.type && a.value === f.value)
    );
    if (newFilters.length === 0) return;
    const updated = [...activeFilters, ...newFilters];
    set({ activeFilters: updated });
    const hasProvince = newFilters.some((f) => f.type === "province");
    if (hasProvince) {
      const provinces = updated.filter((f) => f.type === "province").map((f) => f.value);
      get().loadFilterValues(provinces);
    }
  },

  removeFilter: (filter) => {
    const { activeFilters } = get();
    const updated = activeFilters.filter(
      (f) => !(f.type === filter.type && f.value === filter.value)
    );
    set({ activeFilters: updated });
    if (filter.type === "province") {
      const provinces = updated.filter((f) => f.type === "province").map((f) => f.value);
      get().loadFilterValues(provinces.length ? provinces : undefined);
    }
    if (get().query.trim()) {
      get().performSearch();
    }
  },

  clearFilters: () => {
    set({ activeFilters: [] });
    get().loadFilterValues();
    if (get().query.trim()) {
      get().performSearch();
    }
  },

  clearSuggestions: () => set({ suggestions: null }),

  openDetail: async (documentId: string) => {
    const assetId = extractAssetId(documentId);
    set({ selectedAssetId: assetId, selectedAsset: null, detailLoading: true });
    try {
      const asset = await minDelay(heritageApi.get(assetId));
      set({ selectedAsset: asset, detailLoading: false });
    } catch {
      set({ detailLoading: false });
    }
  },

  closeDetail: () =>
    set({ selectedAssetId: null, selectedAsset: null, detailLoading: false }),
}));
