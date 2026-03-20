"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useRoutesStore } from "@/store/routes";
import { routes as routesApi, type RagSource } from "@/lib/api";
import { ChatInput } from "@/components/chat/ChatInput";
import { RouteStopCard } from "@/components/routes/RouteStopCard";
import { RouteDetailPanel } from "@/components/routes/RouteDetailPanel";
import ReactMarkdown from "react-markdown";

const HERITAGE_TYPE_COLORS: Record<string, string> = {
  patrimonio_inmueble: "bg-amber-100 text-amber-700",
  patrimonio_mueble: "bg-purple-100 text-purple-700",
  patrimonio_inmaterial: "bg-rose-100 text-rose-700",
  paisaje_cultural: "bg-emerald-100 text-emerald-700",
};

function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours > 0 && mins > 0) return `${hours}h ${mins}min`;
  if (hours > 0) return `${hours}h`;
  return `${mins}min`;
}

/** Legacy layout for old routes without introduction/conclusion */
function LegacyStopsLayout({
  route,
}: {
  route: NonNullable<ReturnType<typeof useRoutesStore.getState>["activeRoute"]>;
}) {
  return (
    <>
      <p className="text-stone-600 leading-relaxed">{route.narrative}</p>

      <div>
        <h2 className="text-xl font-semibold text-stone-900 mb-5">Paradas</h2>
        <div className="space-y-3">
          {route.stops.map((stop, i) => {
            const typeColor =
              HERITAGE_TYPE_COLORS[stop.heritage_type] ??
              "bg-stone-100 text-stone-700";

            return (
              <div
                key={stop.order}
                className="group flex gap-4 rounded-xl border border-stone-200/60 bg-white p-5 shadow-sm hover:shadow-md transition-all"
              >
                <div className="flex flex-col items-center">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-amber-500 to-orange-600 text-white font-semibold text-sm shadow-sm">
                    {stop.order}
                  </div>
                  {i < route.stops.length - 1 && (
                    <div className="w-px flex-1 bg-stone-200 mt-2" />
                  )}
                </div>
                <div className="flex-1 min-w-0 pb-2">
                  <a
                    href={stop.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-stone-900 hover:text-amber-700 transition-colors"
                  >
                    {stop.title}
                  </a>
                  <div className="flex items-center gap-2 mt-1 text-xs text-stone-400">
                    <span
                      className={`rounded-full px-2 py-0.5 ${typeColor}`}
                    >
                      {stop.heritage_type}
                    </span>
                    <span>{stop.municipality ?? stop.province}</span>
                    <span>{stop.visit_duration_minutes}min</span>
                  </div>
                  <p className="text-sm text-stone-600 mt-2 leading-relaxed line-clamp-3">
                    {stop.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

/** New layout with introduction, interleaved RouteStopCards, and conclusion */
function InterleavedStopsLayout({
  route,
}: {
  route: NonNullable<ReturnType<typeof useRoutesStore.getState>["activeRoute"]>;
}) {
  return (
    <>
      {/* Introduction */}
      {route.introduction && (
        <p className="text-stone-600 leading-relaxed">{route.introduction}</p>
      )}

      {/* Interleaved stop cards */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-stone-900">Paradas</h2>
        {route.stops.map((stop) => (
          <RouteStopCard key={stop.order} stop={stop} />
        ))}
      </div>

      {/* Conclusion */}
      {route.conclusion && (
        <p className="text-stone-600 leading-relaxed italic">
          {route.conclusion}
        </p>
      )}
    </>
  );
}

export default function RouteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { activeRoute, selectRoute, loading } = useRoutesStore();
  const hasDetail = useRoutesStore((s) => s.selectedStopAssetId !== null);
  const closeStopDetail = useRoutesStore((s) => s.closeStopDetail);
  const [guideMessages, setGuideMessages] = useState<
    { role: "user" | "assistant"; content: string; sources?: RagSource[] }[]
  >([]);
  const [guiding, setGuiding] = useState(false);

  useEffect(() => {
    if (id) selectRoute(id);
  }, [id, selectRoute]);

  // Close detail panel on unmount
  useEffect(() => {
    return () => closeStopDetail();
  }, [closeStopDetail]);

  const handleGuideQuestion = async (question: string) => {
    if (!id) return;
    setGuideMessages((m) => [...m, { role: "user", content: question }]);
    setGuiding(true);
    try {
      const resp = await routesApi.guide(id, question);
      setGuideMessages((m) => [
        ...m,
        { role: "assistant", content: resp.answer, sources: resp.sources },
      ]);
    } finally {
      setGuiding(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="flex gap-1">
          <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
          <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
          <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
        </div>
      </div>
    );
  }

  if (!activeRoute) {
    return (
      <p className="text-center text-stone-400 py-20">
        Ruta no encontrada.
      </p>
    );
  }

  const hasNewFormat = !!activeRoute.introduction;

  return (
    <div className="relative h-[calc(100vh-3.625rem)] overflow-hidden">
      {/* Main content */}
      <div
        className={`absolute top-0 bottom-0 left-0 overflow-y-auto transition-all duration-300 ${
          hasDetail ? "right-[480px]" : "right-0"
        }`}
      >
        <div className="mx-auto max-w-3xl px-6 py-8 space-y-10">
          {/* Header */}
          <div>
            <Link
              href="/routes"
              className="inline-flex items-center gap-1 text-sm text-amber-600 hover:text-amber-700 transition-colors mb-3"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18"
                />
              </svg>
              Todas las rutas
            </Link>
            <h1 className="text-3xl font-bold text-stone-900">
              {activeRoute.title}
            </h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-stone-500">
              <span className="inline-flex items-center gap-1">
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z"
                  />
                </svg>
                {activeRoute.province}
              </span>
              <span>{activeRoute.stops.length} paradas</span>
              <span>{formatDuration(activeRoute.total_duration_minutes)}</span>
            </div>
          </div>

          {/* Route content: new or legacy layout */}
          {hasNewFormat ? (
            <InterleavedStopsLayout route={activeRoute} />
          ) : (
            <LegacyStopsLayout route={activeRoute} />
          )}

          {/* Guide chat section */}
          <div className="rounded-2xl border border-stone-200/60 bg-white p-6 shadow-sm space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-stone-900">
                Guia interactivo
              </h2>
              <p className="text-sm text-stone-500 mt-0.5">
                Pregunta sobre esta ruta o cualquiera de sus elementos
              </p>
            </div>
            {guideMessages.length > 0 && (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {guideMessages.map((m, i) => (
                  <div
                    key={i}
                    className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <span
                      className={`inline-block rounded-2xl px-4 py-2.5 text-sm max-w-[80%] ${
                        m.role === "user"
                          ? "bg-gradient-to-br from-amber-600 to-orange-600 text-white rounded-br-md"
                          : "bg-stone-50 border border-stone-200 text-stone-700 rounded-bl-md"
                      }`}
                    >
                      {m.role === "assistant" ? (
                        <ReactMarkdown
                          components={{
                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                            ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 last:mb-0 space-y-1">{children}</ol>,
                            ul: ({ children }) => <ul className="list-disc pl-4 mb-2 last:mb-0 space-y-1">{children}</ul>,
                            strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                            em: ({ children }) => <em className="italic">{children}</em>,
                          }}
                        >
                          {m.content}
                        </ReactMarkdown>
                      ) : (
                        m.content
                      )}
                    </span>
                  </div>
                ))}
                {guiding && (
                  <div className="flex justify-start">
                    <span className="inline-block rounded-2xl rounded-bl-md bg-stone-50 border border-stone-200 px-4 py-2.5">
                      <span className="flex gap-1">
                        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" />
                        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" />
                        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" />
                      </span>
                    </span>
                  </div>
                )}
              </div>
            )}
            <ChatInput
              onSend={handleGuideQuestion}
              disabled={guiding}
              placeholder="Pregunta sobre la ruta..."
            />
          </div>
        </div>
      </div>

      {/* Detail panel — slides in from right */}
      {hasDetail && (
        <aside className="absolute right-0 top-0 bottom-0 w-[480px] z-10 max-md:w-full">
          <RouteDetailPanel />
        </aside>
      )}
    </div>
  );
}
