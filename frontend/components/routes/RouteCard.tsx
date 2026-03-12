"use client";

import Link from "next/link";
import type { VirtualRoute } from "@/lib/api";

export function RouteCard({ route }: { route: VirtualRoute }) {
  const hours = Math.floor(route.total_duration_minutes / 60);
  const mins = route.total_duration_minutes % 60;
  const duration = hours > 0 ? `${hours}h ${mins}min` : `${mins}min`;

  return (
    <Link
      href={`/routes/${route.id}`}
      className="group block rounded-2xl border border-stone-200/60 bg-white p-6 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="font-semibold text-stone-900 group-hover:text-amber-700 transition-colors line-clamp-2">
          {route.title}
        </h3>
        <svg className="w-4 h-4 shrink-0 text-stone-300 group-hover:text-amber-500 transition-colors mt-1" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 19.5 15-15m0 0H8.25m11.25 0v11.25" />
        </svg>
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
