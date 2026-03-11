"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useRoutesStore } from "@/store/routes";
import { routes as routesApi, type RagSource } from "@/lib/api";
import { ChatInput } from "@/components/chat/ChatInput";

export default function RouteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { activeRoute, selectRoute, loading } = useRoutesStore();
  const [guideMessages, setGuideMessages] = useState<
    { role: "user" | "assistant"; content: string; sources?: RagSource[] }[]
  >([]);
  const [guiding, setGuiding] = useState(false);

  useEffect(() => { if (id) selectRoute(id); }, [id, selectRoute]);

  const handleGuideQuestion = async (question: string) => {
    if (!id) return;
    setGuideMessages((m) => [...m, { role: "user", content: question }]);
    setGuiding(true);
    try {
      const resp = await routesApi.guide(id, question);
      setGuideMessages((m) => [...m, { role: "assistant", content: resp.answer, sources: resp.sources }]);
    } finally {
      setGuiding(false);
    }
  };

  if (loading) return <p className="text-center text-gray-400 py-12">Cargando ruta…</p>;
  if (!activeRoute) return <p className="text-center text-gray-400 py-12">Ruta no encontrada.</p>;

  const hours = Math.floor(activeRoute.total_duration_minutes / 60);
  const mins = activeRoute.total_duration_minutes % 60;

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      <div>
        <Link href="/routes" className="text-sm text-amber-700 hover:underline">← Todas las rutas</Link>
        <h1 className="mt-2 text-3xl font-bold text-gray-900">{activeRoute.title}</h1>
        <p className="text-gray-500 mt-1">
          {activeRoute.province} · {activeRoute.stops.length} paradas ·{" "}
          {hours > 0 ? `${hours}h ` : ""}{mins}min
        </p>
      </div>

      <p className="text-gray-700 leading-relaxed">{activeRoute.narrative}</p>

      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Paradas de la ruta</h2>
        <div className="space-y-4">
          {activeRoute.stops.map((stop) => (
            <div key={stop.order} className="flex gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-800 font-semibold text-sm">
                {stop.order}
              </div>
              <div className="flex-1 min-w-0">
                <a
                  href={stop.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-gray-900 hover:text-amber-700 transition-colors"
                >
                  {stop.title}
                </a>
                <p className="text-xs text-gray-500 mt-0.5">
                  {stop.heritage_type} · {stop.municipality ?? stop.province} · {stop.visit_duration_minutes}min
                </p>
                <p className="text-sm text-gray-600 mt-1 line-clamp-3">{stop.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-amber-100 bg-amber-50 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-amber-900">Guía interactivo</h2>
        <p className="text-sm text-amber-700">Pregunta al guía sobre esta ruta o cualquiera de sus elementos</p>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {guideMessages.map((m, i) => (
            <div key={i} className={`text-sm ${m.role === "user" ? "text-right" : "text-left"}`}>
              <span
                className={`inline-block rounded-xl px-3 py-2 ${
                  m.role === "user"
                    ? "bg-amber-700 text-white"
                    : "bg-white border border-amber-200 text-gray-800"
                }`}
              >
                {m.content}
              </span>
            </div>
          ))}
          {guiding && (
            <div className="text-sm text-left">
              <span className="inline-block rounded-xl px-3 py-2 bg-white border border-amber-200 text-gray-400">
                Consultando…
              </span>
            </div>
          )}
        </div>
        <ChatInput onSend={handleGuideQuestion} disabled={guiding} placeholder="Pregunta sobre la ruta…" />
      </div>
    </div>
  );
}
