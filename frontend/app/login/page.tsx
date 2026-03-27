"use client";

import { useState } from "react";
import { useAuthStore } from "@/store/auth";

export default function LoginPage() {
  const login = useAuthStore((s) => s.login);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(username, password);
      window.location.href = "/";
    } catch {
      setError("Credenciales incorrectas");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-gradient-to-br from-stone-50 to-green-50/30">
      <div className="w-full max-w-md rounded-2xl border border-stone-200/60 bg-white p-8 shadow-lg">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-green-600 to-emerald-700 text-lg font-bold text-white shadow-sm">
            PA
          </div>
          <span className="text-lg font-semibold text-stone-800">
            Patrimonio de Andalucía
          </span>
        </div>

        <h1 className="mb-6 text-center text-2xl font-bold tracking-tight text-stone-900">
          Iniciar sesión
        </h1>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label
              htmlFor="username"
              className="block text-sm font-medium text-stone-700"
            >
              Usuario
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              className="w-full rounded-lg border border-stone-300 px-4 py-2.5 text-stone-900 placeholder:text-stone-400 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20"
              placeholder="Tu usuario"
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="password"
              className="block text-sm font-medium text-stone-700"
            >
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full rounded-lg border border-stone-300 px-4 py-2.5 text-stone-900 placeholder:text-stone-400 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20"
              placeholder="Tu contraseña"
            />
          </div>

          {error && (
            <p className="text-center text-sm text-red-600">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
