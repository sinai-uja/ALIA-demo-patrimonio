"use client";

import { useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import type { VirtualRoute } from "@/lib/api";
import { useRoutesStore } from "@/store/routes";
import { FeedbackButtons } from "@/components/shared/FeedbackButtons";

function DeleteConfirmModal({
  routeTitle,
  onConfirm,
  onCancel,
  deleting,
}: {
  routeTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
  deleting: boolean;
}) {
  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center shrink-0">
            <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-stone-900 text-sm">Eliminar ruta</h3>
            <p className="text-xs text-stone-500 mt-0.5">Esta acción no se puede deshacer</p>
          </div>
        </div>

        <p className="text-sm text-stone-600 mb-6 line-clamp-2">
          ¿Seguro que quieres eliminar <span className="font-medium text-stone-800">&quot;{routeTitle}&quot;</span>?
        </p>

        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={deleting}
            className="px-4 py-2 text-sm font-medium text-stone-600 bg-stone-100 hover:bg-stone-200 rounded-xl transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={deleting}
            className="px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-xl transition-colors flex items-center gap-2"
          >
            {deleting && (
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            Eliminar
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export function RouteCard({ route }: { route: VirtualRoute }) {
  const deleteRoute = useRoutesStore((s) => s.deleteRoute);
  const [showConfirm, setShowConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const hours = Math.floor(route.total_duration_minutes / 60);
  const mins = route.total_duration_minutes % 60;
  const duration = hours > 0 ? `${hours}h ${mins}min` : `${mins}min`;
  const thumbnail = route.stops.find((s) => s.image_url)?.image_url;
  const summary = route.introduction || route.narrative;

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowConfirm(true);
  };

  const handleConfirm = async () => {
    setDeleting(true);
    try {
      await deleteRoute(route.id);
    } catch {
      setDeleting(false);
      setShowConfirm(false);
    }
  };

  return (
    <>
      <Link
        href={`/routes/${route.id}`}
        className="group relative flex rounded-xl border border-stone-200/60 bg-white shadow-sm hover:shadow-md transition-shadow overflow-hidden"
      >
        {/* Thumbnail — flush left */}
        {thumbnail ? (
          <div className="w-28 shrink-0 bg-stone-100">
            <img
              src={thumbnail}
              alt={route.title}
              className="w-full h-full object-cover"
            />
          </div>
        ) : (
          <div className="w-28 shrink-0 bg-gradient-to-br from-stone-50 to-stone-100 flex items-center justify-center">
            <svg className="w-8 h-8 text-stone-300" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z" />
            </svg>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 min-w-0 p-4 pr-10">
          <h3 className="font-semibold text-stone-900 text-sm leading-snug mb-1.5 group-hover:text-green-700 transition-colors line-clamp-1">
            {route.title}
          </h3>

          <div className="flex items-center gap-3 text-xs text-stone-400 mb-2">
            <span className="flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" />
              </svg>
              {route.province}
            </span>
            <span>{route.stops.length} paradas</span>
            <span className="flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
              {duration}
            </span>
          </div>

          {summary && (
            <p
              className="text-xs text-stone-500 leading-relaxed"
              style={{
                overflow: "hidden",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
              }}
            >
              {summary}
            </p>
          )}

          <div
            className="mt-2"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}
          >
            <FeedbackButtons targetType="route" targetId={route.id} size="sm" />
          </div>
        </div>

        {/* Delete button */}
        <button
          onClick={handleDeleteClick}
          className="absolute top-3 right-3 w-7 h-7 rounded-full flex items-center justify-center text-stone-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100 z-10"
          aria-label="Eliminar ruta"
          title="Eliminar ruta"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
          </svg>
        </button>
      </Link>

      {showConfirm && (
        <DeleteConfirmModal
          routeTitle={route.title}
          onConfirm={handleConfirm}
          onCancel={() => setShowConfirm(false)}
          deleting={deleting}
        />
      )}
    </>
  );
}
