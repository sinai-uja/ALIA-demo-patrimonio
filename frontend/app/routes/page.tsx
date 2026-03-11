"use client";

import { useEffect, useState } from "react";
import { useRoutesStore } from "@/store/routes";
import { RouteCard } from "@/components/routes/RouteCard";

const PROVINCES = ["Almería", "Cádiz", "Córdoba", "Granada", "Huelva", "Jaén", "Málaga", "Sevilla"];
const HERITAGE_TYPES = [
  { value: "ALL", label: "Todo el patrimonio" },
  { value: "PATRIMONIO_INMUEBLE", label: "Patrimonio Inmueble" },
  { value: "PATRIMONIO_INMATERIAL", label: "Patrimonio Inmaterial" },
  { value: "PAISAJE_CULTURAL", label: "Paisaje Cultural" },
  { value: "PATRIMONIO_MUEBLE", label: "Patrimonio Mueble" },
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

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Rutas Virtuales</h1>
        <p className="text-gray-500 text-sm">Genera una ruta patrimonial personalizada</p>
      </div>

      <form
        onSubmit={handleGenerate}
        className="rounded-2xl border border-gray-200 bg-white p-6 space-y-4 shadow-sm"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provincia</label>
            <select
              value={form.province}
              onChange={(e) => setForm((f) => ({ ...f, province: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none"
            >
              {PROVINCES.map((p) => <option key={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Número de paradas</label>
            <input
              type="number"
              min={2}
              max={10}
              value={form.num_stops}
              onChange={(e) => setForm((f) => ({ ...f, num_stops: Number(e.target.value) }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Tipos de patrimonio</label>
          <div className="flex flex-wrap gap-2">
            {HERITAGE_TYPES.map((ht) => (
              <label key={ht.value} className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.heritage_types.includes(ht.value)}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      heritage_types: e.target.checked
                        ? [...f.heritage_types.filter((x) => x !== "ALL"), ht.value]
                        : f.heritage_types.filter((x) => x !== ht.value),
                    }))
                  }
                  className="accent-amber-700"
                />
                <span className="text-sm text-gray-700">{ht.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Intereses o preferencias (opcional)
          </label>
          <input
            type="text"
            value={form.user_interests}
            onChange={(e) => setForm((f) => ({ ...f, user_interests: e.target.value }))}
            placeholder="ej. arquitectura medieval, artesanía, naturaleza…"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={generating}
          className="w-full rounded-xl bg-amber-700 py-2.5 text-sm font-medium text-white hover:bg-amber-800 transition disabled:opacity-50"
        >
          {generating ? "Generando ruta…" : "Generar ruta personalizada"}
        </button>
      </form>

      {loading && <p className="text-center text-gray-400 text-sm">Cargando rutas…</p>}

      {routes.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Rutas generadas</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {routes.map((r) => <RouteCard key={r.id} route={r} />)}
          </div>
        </div>
      )}
    </div>
  );
}
