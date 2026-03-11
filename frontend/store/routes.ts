import { create } from "zustand";
import { routes as routesApi, type VirtualRoute } from "@/lib/api";

interface RoutesState {
  routes: VirtualRoute[];
  activeRoute: VirtualRoute | null;
  loading: boolean;
  generating: boolean;

  loadRoutes: (province?: string) => Promise<void>;
  generateRoute: (params: {
    province: string;
    num_stops?: number;
    heritage_types?: string[];
    user_interests?: string;
  }) => Promise<VirtualRoute>;
  selectRoute: (id: string) => Promise<void>;
}

export const useRoutesStore = create<RoutesState>((set) => ({
  routes: [],
  activeRoute: null,
  loading: false,
  generating: false,

  loadRoutes: async (province) => {
    set({ loading: true });
    try {
      const routes = await routesApi.list(province);
      set({ routes });
    } finally {
      set({ loading: false });
    }
  },

  generateRoute: async (params) => {
    set({ generating: true });
    try {
      const route = await routesApi.generate(params);
      set((s) => ({ routes: [route, ...s.routes], activeRoute: route }));
      return route;
    } finally {
      set({ generating: false });
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
