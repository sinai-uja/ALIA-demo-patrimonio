"use client";

import { useState } from "react";
import Link from "next/link";
import type { VirtualRoute } from "@/lib/api";
import { useRoutesStore } from "@/store/routes";

export function RouteCard({ route }: { route: VirtualRoute }) {
  const deleteRoute = useRoutesStore((s) => s.deleteRoute);
  const [deleting, setDeleting] = useState(false);

  const hours = Math.floor(route.total_duration_minutes / 60);
  const mins = route.total_duration_minutes % 60;
  const duration = hours > 0 ? `${hours}h ${mins}min` : `${mins}min`;

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("¿Eliminar esta ruta?")) return;
    setDeleting(true);
    try {
      await deleteRoute(route.id);
    } catch {
      setDeleting(false);
    }
  };

  return (
    <Link
      href={`/routes/${route.id}`}
      className="group relative block rounded-2xl border border-stone-200/60 bg-white p-6 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300"
    >
      <button
        onClick={handleDelete}
        disabled={deleting}
        className="absolute top-3 right-3 w-7 h-7 rounded-full flex items-center justify-center text-stone-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100 z-10"
        aria-label="Eliminar ruta"
        title="Eliminar ruta"
      >
        {deleting ? (
          <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
          </svg>
        )}
      </button>

      <div className="flex items-start justify-between gap-3 mb-3 pr-8">
        <h3 className="font-semibold text-stone-900 group-hover:text-amber-700 transition-colors line-clamp-2">
          {route.title}
        </h3>
      </div>
      <p className="text-xs text-stone-400 line-clamp-3 leading-relaxed">{route.narrative}</p>
      <div className="mt-4 pt-4 border-t border-stone-100 flex items-center gap-4 text-xs text-stone-500">
        <span className="flex items-center gap-1">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" />
          </svg>
          {route.province}
        </span>
        <span>{route.stops.length} paradas</span>
        <span>{duration}</span>
      </div>
    </Link>
  );
}
