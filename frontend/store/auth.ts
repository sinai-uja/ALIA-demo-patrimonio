import { create } from "zustand";
import { auth as authApi } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api/v1";

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

function setCookie(name: string, value: string, days: number) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`;
}

function removeCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
  return match ? match[1] : null;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  hydrated: boolean;
  username: string | null;
  profileType: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<boolean>;
  hydrate: () => void;
  fetchUser: () => Promise<void>;
  setProfileType: (type: string) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  refreshToken: null,
  isAuthenticated: false,
  hydrated: false,
  username: null,
  profileType: null,

  login: async (username: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || res.statusText);
    }

    const data = (await res.json()) as LoginResponse;
    setCookie("token", data.access_token, 7);
    localStorage.setItem("refreshToken", data.refresh_token);
    set({
      token: data.access_token,
      refreshToken: data.refresh_token,
      isAuthenticated: true,
    });

    await get().fetchUser();
  },

  logout: () => {
    removeCookie("token");
    localStorage.removeItem("refreshToken");
    set({
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      username: null,
      profileType: null,
    });
    window.location.href = "/login";
  },

  refresh: async () => {
    const { refreshToken } = get();
    if (!refreshToken) return false;

    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) return false;

      const data = (await res.json()) as LoginResponse;
      setCookie("token", data.access_token, 7);
      localStorage.setItem("refreshToken", data.refresh_token);
      set({
        token: data.access_token,
        refreshToken: data.refresh_token,
        isAuthenticated: true,
      });
      return true;
    } catch {
      return false;
    }
  },

  hydrate: () => {
    const token = getCookie("token");
    const refreshToken =
      typeof localStorage !== "undefined"
        ? localStorage.getItem("refreshToken")
        : null;
    if (token) {
      set({ token, refreshToken, isAuthenticated: true });
      get().fetchUser();
    }
    set({ hydrated: true });
  },

  fetchUser: async () => {
    try {
      const user = await authApi.getMe();
      set({ username: user.username, profileType: user.profile_type });
    } catch {
      // If fetching user fails, keep existing auth state
    }
  },

  setProfileType: async (type: string) => {
    const user = await authApi.updateProfileType(type);
    set({ profileType: user.profile_type });
  },
}));
