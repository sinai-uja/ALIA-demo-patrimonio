"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { routes, type VirtualRoute } from "@/lib/api";

interface AddToRouteModalProps {
  documentId: string;
  assetTitle: string;
  onClose: () => void;
}

export default function AddToRouteModal({
  documentId,
  assetTitle,
  onClose,
}: AddToRouteModalProps) {
  const [routeList, setRouteList] = useState<VirtualRoute[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addingTo, setAddingTo] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    routes
      .list()
      .then((data) => {
        if (!cancelled) setRouteList(data);
      })
      .catch(() => {
        if (!cancelled) setError("No se pudieron cargar las rutas.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Close on Escape (only when not in progress)
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !addingTo) onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [addingTo, onClose]);

  async function handleAdd(route: VirtualRoute) {
    setError(null);
    try {
      await routes.addStopBackground(route.id, documentId);
      setSuccess(route.title);
      setTimeout(() => onClose(), 1200);
    } catch {
      setError("Error al enviar la solicitud. Inténtalo de nuevo.");
    }
  }

  const busy = false; // never blocks — background request

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={busy ? undefined : onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 animate-in fade-in zoom-in-95 duration-200 max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-green-50 flex items-center justify-center shrink-0">
            <svg
              className="w-5 h-5 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z"
              />
            </svg>
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold text-stone-900 text-sm">
              Añadir a ruta
            </h3>
            <p className="text-xs text-stone-500 mt-0.5 truncate">
              {assetTitle}
            </p>
          </div>
        </div>

        {/* Success message */}
        {success && (
          <div className="mb-4 rounded-lg bg-green-50 border border-green-100 px-3 py-2 text-xs text-green-700 flex items-center gap-2">
            <svg
              className="w-4 h-4 shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m4.5 12.75 6 6 9-13.5"
              />
            </svg>
            Parada añadiendose a &quot;{success}&quot;. La narrativa se genera en segundo plano.
          </div>
        )}

        {/* Error message */}
        {error && !success && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-100 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}

        {/* Body */}
        <div className="overflow-y-auto flex-1 -mx-1 px-1">
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <svg
                className="w-6 h-6 animate-spin text-green-600"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            </div>
          ) : routeList.length === 0 && !error ? (
            <div className="text-center py-8">
              <p className="text-sm text-stone-500 mb-3">
                No tienes rutas. Crea una en la sección Rutas.
              </p>
              <Link
                href="/routes"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-green-700 hover:text-green-800 transition-colors"
              >
                Ir a Rutas
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
                  />
                </svg>
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {routeList.map((route) => {
                const isAdding = addingTo === route.id;
                return (
                  <button
                    key={route.id}
                    onClick={() => handleAdd(route)}
                    disabled={busy}
                    className={`w-full text-left rounded-xl border p-3 transition-all ${
                      isAdding
                        ? "border-green-300 bg-green-50"
                        : busy
                          ? "border-stone-100 bg-stone-50 opacity-50 cursor-not-allowed"
                          : "border-stone-200 bg-white hover:border-green-300 hover:bg-green-50/50 cursor-pointer"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-stone-800 truncate">
                          {route.title}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-stone-400">
                            {route.province}
                          </span>
                          <span className="text-xs text-stone-300">·</span>
                          <span className="text-xs text-stone-400">
                            {route.stops.length}{" "}
                            {route.stops.length === 1 ? "parada" : "paradas"}
                          </span>
                        </div>
                      </div>
                      {isAdding && (
                        <svg
                          className="w-4 h-4 animate-spin text-green-600 shrink-0"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          />
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                          />
                        </svg>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        {!success && (
          <div className="mt-4 flex justify-end">
            <button
              onClick={onClose}
              disabled={busy}
              className="px-4 py-2 text-sm font-medium text-stone-600 bg-stone-100 hover:bg-stone-200 rounded-xl transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
