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

export interface ActiveFilter {
  type: "province" | "municipality" | "heritage_type";
  value: string;
  label: string;
  matchedText: string;
}

interface SearchState {
  query: string;
  results: SearchResult[];
  totalResults: number;
  page: number;
  pageSize: number;
  totalPages: number;
  activeFilters: ActiveFilter[];
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

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Extract numeric asset ID from document_id (e.g. "ficha-inmueble-20831" → "20831"). */
function extractAssetId(documentId: string): string {
  return documentId.replace(/^ficha-\w+-/, "");
}

/** Remove active filter matched texts from the query before sending to API.
 *  Heritage type matches are kept in the query — they carry semantic value
 *  for embedding search (e.g. "pintura" helps find paintings).
 *  Geographic filters (province, municipality) are removed since the
 *  backend filter already constrains the result set spatially. */
function buildCleanQuery(query: string, filters: ActiveFilter[]): string {
  let clean = query;
  for (const f of filters) {
    if (f.matchedText && f.type !== "heritage_type") {
      clean = clean.replace(new RegExp(escapeRegex(f.matchedText), "gi"), "");
    }
  }
  return clean.replace(/\s{2,}/g, " ").trim();
}

function collectFilters(filters: ActiveFilter[]) {
  const heritage: string[] = [];
  const provinces: string[] = [];
  const municipalities: string[] = [];
  for (const f of filters) {
    if (f.type === "heritage_type") heritage.push(f.value);
    if (f.type === "province") provinces.push(f.value);
    if (f.type === "municipality") municipalities.push(f.value);
  }
  return {
    heritage_type_filter: heritage.length ? heritage : null,
    province_filter: provinces.length ? provinces : null,
    municipality_filter: municipalities.length ? municipalities : null,
  };
}

export const useSearchStore = create<SearchState>((set, get) => ({
  query: "",
  results: [],
  totalResults: 0,
  page: 1,
  pageSize: 10,
  totalPages: 0,
  activeFilters: [],
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
    const { query, activeFilters, pageSize } = get();
    if (!query.trim()) return;

    const cleanQuery = buildCleanQuery(query, activeFilters);
    if (!cleanQuery) return;

    const targetPage = page ?? 1;
    set({
      loading: true,
      hasSearched: true,
      selectedAssetId: null,
      selectedAsset: null,
    });
    try {
      const filters = collectFilters(activeFilters);
      const res = await searchApi.similarity({
        query: cleanQuery,
        page: targetPage,
        page_size: pageSize,
        ...filters,
      });
      set({
        results: res.results,
        totalResults: res.total_results,
        page: res.page,
        totalPages: res.total_pages,
        searchId: res.search_id,
      });
    } catch {
      set({ results: [], totalResults: 0, page: 1, totalPages: 0, searchId: null });
    } finally {
      set({ loading: false });
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
      const asset = await heritageApi.get(assetId);
      set({ selectedAsset: asset, detailLoading: false });
    } catch {
      set({ detailLoading: false });
    }
  },

  closeDetail: () =>
    set({ selectedAssetId: null, selectedAsset: null, detailLoading: false }),
}));
