"use client";

import { useEffect, useState } from "react";
import { useRoutesStore } from "@/store/routes";
import { RouteCard } from "@/components/routes/RouteCard";

const PROVINCES = ["Almería", "Cádiz", "Córdoba", "Granada", "Huelva", "Jaén", "Málaga", "Sevilla"];
const HERITAGE_TYPES = [
  { value: "ALL", label: "Todo" },
  { value: "PATRIMONIO_INMUEBLE", label: "Inmueble" },
  { value: "PATRIMONIO_INMATERIAL", label: "Inmaterial" },
  { value: "PAISAJE_CULTURAL", label: "Paisaje" },
  { value: "PATRIMONIO_MUEBLE", label: "Mueble" },
];

export default function RoutesPage() {
  const { routes, loading, generating, loadRoutes, generateRoute } = useRoutesStore();
  const [form, setForm] = useState({
    province: "Jaén",
    num_stops: 5,
    heritage_types: ["ALL"],
    user_interests: "",
  });

  useEffect(() => { loadRoutes(); }, [loadRoutes]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    await generateRoute(form);
  };

  const toggleType = (value: string) => {
    setForm((f) => ({
      ...f,
      heritage_types: f.heritage_types.includes(value)
        ? f.heritage_types.filter((x) => x !== value)
        : [...f.heritage_types.filter((x) => x !== "ALL"), value],
    }));
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-8 space-y-10">
      <div>
        <h1 className="text-3xl font-bold text-stone-900">Rutas Virtuales</h1>
        <p className="text-stone-500 mt-1">Genera una ruta patrimonial personalizada por Andalucía</p>
      </div>

      <form
        onSubmit={handleGenerate}
        className="rounded-2xl border border-stone-200/60 bg-white p-8 space-y-6 shadow-sm"
      >
        <div className="grid gap-6 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1.5">Provincia</label>
            <select
              value={form.province}
              onChange={(e) => setForm((f) => ({ ...f, province: e.target.value }))}
              className="w-full rounded-xl border border-stone-200 bg-stone-50 px-4 py-2.5 text-sm focus:border-amber-400 focus:ring-2 focus:ring-amber-100 outline-none transition-all"
            >
              {PROVINCES.map((p) => <option key={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1.5">Paradas</label>
            <input
              type="number"
              min={2}
              max={10}
              value={form.num_stops}
              onChange={(e) => setForm((f) => ({ ...f, num_stops: Number(e.target.value) }))}
              className="w-full rounded-xl border border-stone-200 bg-stone-50 px-4 py-2.5 text-sm focus:border-amber-400 focus:ring-2 focus:ring-amber-100 outline-none transition-all"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-stone-700 mb-2">Tipo de patrimonio</label>
          <div className="flex flex-wrap gap-2">
            {HERITAGE_TYPES.map((ht) => {
              const selected = form.heritage_types.includes(ht.value);
              return (
                <button
                  key={ht.value}
                  type="button"
                  onClick={() => toggleType(ht.value)}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium transition-all ${
                    selected
                      ? "bg-amber-100 text-amber-800 border border-amber-300"
                      : "bg-stone-100 text-stone-500 border border-transparent hover:bg-stone-200"
                  }`}
                >
                  {ht.label}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1.5">
            Intereses (opcional)
          </label>
          <input
            type="text"
            value={form.user_interests}
            onChange={(e) => setForm((f) => ({ ...f, user_interests: e.target.value }))}
            placeholder="ej. arquitectura medieval, artesanía, naturaleza..."
            className="w-full rounded-xl border border-stone-200 bg-stone-50 px-4 py-2.5 text-sm focus:border-amber-400 focus:ring-2 focus:ring-amber-100 outline-none transition-all"
          />
        </div>

        <button
          type="submit"
          disabled={generating}
          className="w-full rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 py-3 text-sm font-semibold text-white shadow-sm hover:shadow-md transition-all disabled:opacity-50"
        >
          {generating ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Generando ruta...
            </span>
          ) : (
            "Generar ruta personalizada"
          )}
        </button>
      </form>

      {loading && (
        <div className="flex justify-center py-8">
          <div className="flex gap-1">
            <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
            <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
            <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
          </div>
        </div>
      )}

      {routes.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-stone-800 mb-5">Rutas generadas</h2>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {routes.map((r) => <RouteCard key={r.id} route={r} />)}
          </div>
        </div>
      )}
    </div>
  );
}
