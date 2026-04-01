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

    if (!username.trim()) { setError("Introduce tu usuario"); return; }
    if (!password.trim()) { setError("Introduce tu contraseña"); return; }

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

  const hasError = !!error;
  const isFieldError = error === "Introduce tu usuario" || error === "Introduce tu contraseña";
  const usernameError = error === "Introduce tu usuario";
  const passwordError = error === "Introduce tu contraseña";

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-gradient-to-br from-stone-50 to-green-50/30">
      <div className="w-full max-w-md rounded-2xl border border-stone-200/60 bg-white p-8 shadow-lg">
        {/* Logo + title */}
        <div className="mb-6 flex flex-col items-center gap-2.5">
          <img src="/images/alia-navbar.png" alt="ALIA" className="h-10 w-auto" />
          <span className="text-lg font-semibold text-stone-800">
            Patrimonio de Andalucía
          </span>
          <h1 className="text-2xl font-bold tracking-tight text-stone-900">
            Iniciar sesión
          </h1>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="username" className="block text-sm font-medium text-stone-700">
              Usuario
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => { setUsername(e.target.value); if (usernameError) setError(null); }}
              autoComplete="username"
              className={`w-full rounded-lg border px-4 py-2.5 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 transition-colors ${
                usernameError
                  ? "border-red-400 focus:border-red-500 focus:ring-red-500/20"
                  : "border-stone-300 focus:border-green-600 focus:ring-green-600/20"
              }`}
              placeholder="Tu usuario"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="block text-sm font-medium text-stone-700">
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); if (passwordError) setError(null); }}
              autoComplete="current-password"
              className={`w-full rounded-lg border px-4 py-2.5 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 transition-colors ${
                passwordError
                  ? "border-red-400 focus:border-red-500 focus:ring-red-500/20"
                  : "border-stone-300 focus:border-green-600 focus:ring-green-600/20"
              }`}
              placeholder="Tu contraseña"
            />
          </div>

          {/* Fixed-height error slot — always present to avoid layout shift */}
          <p className={`text-center text-sm min-h-5 transition-colors ${hasError ? "text-red-600" : "text-transparent"}`}>
            {error ?? "\u00A0"}
          </p>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>

        {/* Partner logos */}
        <div className="mt-6 pt-5 border-t border-stone-100 flex items-center justify-center gap-6">
          <a href="https://sinai.ujaen.es/" target="_blank" rel="noopener noreferrer" className="opacity-70 hover:opacity-100 transition-opacity">
            <img src="/images/sinai.png" alt="Departamento SINAI - Universidad de Jaén" className="h-7 w-auto" />
          </a>
          <a href="https://alia.gob.es/" target="_blank" rel="noopener noreferrer" className="opacity-70 hover:opacity-100 transition-opacity">
            <img src="/images/alia.png" alt="Proyecto ALIA" className="h-7 w-auto" />
          </a>
          <a href="https://www.innovasur.com/" target="_blank" rel="noopener noreferrer" className="opacity-70 hover:opacity-100 transition-opacity">
            <img src="/images/innovasur.png" alt="Innovasur" className="h-5 w-auto" />
          </a>
        </div>
      </div>
    </div>
  );
}
