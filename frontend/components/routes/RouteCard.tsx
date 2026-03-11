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
      className="block rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md hover:border-amber-300 transition-all group"
    >
      <h3 className="font-semibold text-gray-900 group-hover:text-amber-700 transition-colors line-clamp-2">
        {route.title}
      </h3>
      <p className="mt-1 text-sm text-gray-500">{route.province}</p>
      <p className="mt-3 text-xs text-gray-400 line-clamp-3">{route.narrative}</p>
      <div className="mt-4 flex items-center gap-4 text-xs text-gray-500">
        <span>🗺️ {route.stops.length} paradas</span>
        <span>⏱️ {duration}</span>
      </div>
    </Link>
  );
}
