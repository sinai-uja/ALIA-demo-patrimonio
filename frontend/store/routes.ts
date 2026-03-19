import { create } from "zustand";
import {
  routes as routesApi,
  type VirtualRoute,
  type SuggestionResponse,
  type FilterValues,
  type DetectedEntity,
} from "@/lib/api";

export interface ActiveFilter {
  type: "province" | "municipality" | "heritage_type";
  value: string;
  label: string;
  matchedText: string;
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Remove active filter matched texts from the query before sending to API.
 *  Heritage type matches are kept — they carry semantic value for embeddings.
 *  Geographic filters (province, municipality) are removed. */
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

interface RoutesState {
  // Smart input
  query: string;
  activeFilters: ActiveFilter[];
  detectedEntities: DetectedEntity[];
  suggestions: SuggestionResponse | null;
  filterValues: FilterValues | null;
  numStops: number;
  suggestionsLoading: boolean;

  // Generation
  generating: boolean;
  generatedRoute: VirtualRoute | null;

  // Route list
  routes: VirtualRoute[];
  activeRoute: VirtualRoute | null;
  loading: boolean;

  // Actions
  setQuery: (q: string) => void;
  setNumStops: (n: number) => void;
  syncFiltersWithQuery: (q: string) => void;
  fetchSuggestions: (q: string) => Promise<void>;
  loadFilterValues: (provinces?: string[]) => Promise<void>;
  addFilter: (filter: ActiveFilter) => void;
  removeFilter: (filter: ActiveFilter) => void;
  clearFilters: () => void;
  clearSuggestions: () => void;
  generateRoute: () => Promise<VirtualRoute>;
  loadRoutes: () => Promise<void>;
  selectRoute: (id: string) => Promise<void>;
}

export const useRoutesStore = create<RoutesState>((set, get) => ({
  // Smart input
  query: "",
  activeFilters: [],
  detectedEntities: [],
  suggestions: null,
  filterValues: null,
  numStops: 5,
  suggestionsLoading: false,

  // Generation
  generating: false,
  generatedRoute: null,

  // Route list
  routes: [],
  activeRoute: null,
  loading: false,

  setQuery: (q) => set({ query: q }),

  setNumStops: (n) => set({ numStops: n }),

  syncFiltersWithQuery: (q: string) => {
    const { activeFilters } = get();
    if (activeFilters.length === 0) return;
    const lower = q.toLowerCase();
    const remaining = activeFilters.filter((f) => {
      if (!f.matchedText) return true;
      // Heritage type filters stay regardless of query text
      if (f.type === "heritage_type") return true;
      return lower.includes(f.matchedText.toLowerCase());
    });
    if (remaining.length !== activeFilters.length) {
      set({ activeFilters: remaining });
    }
  },

  fetchSuggestions: async (q) => {
    if (!q.trim() || q.trim().length < 2) {
      set({ suggestions: null, detectedEntities: [] });
      return;
    }
    set({ suggestionsLoading: true });
    try {
      const res = await routesApi.suggestions(q.trim());
      set({ suggestions: res, detectedEntities: res.detected_entities });
    } catch {
      set({ suggestions: null });
    } finally {
      set({ suggestionsLoading: false });
    }
  },

  loadFilterValues: async (provinces) => {
    try {
      const values = await routesApi.filters(provinces);
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
  },

  clearFilters: () => {
    set({ activeFilters: [] });
    get().loadFilterValues();
  },

  clearSuggestions: () => set({ suggestions: null }),

  generateRoute: async () => {
    const { query, activeFilters, numStops } = get();
    if (!query.trim()) throw new Error("La consulta no puede estar vacia");

    set({ generating: true });
    try {
      const filters = collectFilters(activeFilters);
      const route = await routesApi.generate({
        query: query.trim(),
        num_stops: numStops,
        ...filters,
      });
      set((s) => ({
        routes: [route, ...s.routes],
        generatedRoute: route,
        activeRoute: route,
      }));
      return route;
    } finally {
      set({ generating: false });
    }
  },

  loadRoutes: async () => {
    set({ loading: true });
    try {
      const routes = await routesApi.list();
      set({ routes });
    } finally {
      set({ loading: false });
    }
  },

  selectRoute: async (id) => {
    set({ loading: true });
    try {
      const route = await routesApi.get(id);
      set({ activeRoute: route });
    } finally {
      set({ loading: false });
    }
  },
}));
