"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useRoutesStore } from "@/store/routes";
import { routes as routesApi, type RagSource } from "@/lib/api";
import { ChatInput } from "@/components/chat/ChatInput";
import { RouteStopCard } from "@/components/routes/RouteStopCard";
import { RouteDetailPanel } from "@/components/routes/RouteDetailPanel";
import { CollapsibleDrawer } from "@/components/shared/CollapsibleDrawer";
import { FeedbackButtons } from "@/components/shared/FeedbackButtons";
import { useFeedbackStore } from "@/store/feedback";
import ReactMarkdown from "react-markdown";

const HERITAGE_TYPE_COLORS: Record<string, string> = {
  patrimonio_inmueble: "bg-green-100 text-green-700",
  patrimonio_mueble: "bg-purple-100 text-purple-700",
  patrimonio_inmaterial: "bg-teal-100 text-teal-700",
  paisaje_cultural: "bg-sky-100 text-sky-700",
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
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-green-600 to-emerald-700 text-white font-semibold text-sm shadow-sm">
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
                    className="font-semibold text-stone-900 hover:text-green-700 transition-colors"
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

/** New layout with introduction, alternating card/narrative roadmap, and conclusion */
function InterleavedStopsLayout({
  route,
}: {
  route: NonNullable<ReturnType<typeof useRoutesStore.getState>["activeRoute"]>;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [twoCol, setTwoCol] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      setTwoCol(entry.contentRect.width >= 700);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      {/* Introduction */}
      {route.introduction && (
        <p className="text-stone-600 leading-relaxed">{route.introduction}</p>
      )}

      {/* Roadmap: alternating card / narrative */}
      <div ref={containerRef}>
        <h2 className="text-xl font-semibold text-stone-900 mb-5">Paradas</h2>
        <div className="flex flex-col">
          {route.stops.map((stop, i) => (
            <div key={stop.order}>
              {twoCol ? (
                <div
                  className={`flex gap-6 items-center ${
                    i % 2 !== 0 ? "flex-row-reverse" : ""
                  }`}
                >
                  <div className="w-1/2">
                    <RouteStopCard stop={stop} showNarrative={false} />
                  </div>
                  {stop.narrative_segment && (
                    <div className="w-1/2">
                      <p className="text-sm text-stone-600 leading-relaxed">
                        {stop.narrative_segment}
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  <RouteStopCard stop={stop} showNarrative={false} />
                  {stop.narrative_segment && (
                    <p className="text-sm text-stone-600 leading-relaxed px-1">
                      {stop.narrative_segment}
                    </p>
                  )}
                </div>
              )}

              {i < route.stops.length - 1 && (
                <div className="flex justify-center py-1">
                  <div className="w-px h-8 bg-stone-200" />
                </div>
              )}
            </div>
          ))}
        </div>
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
  const [guideOpen, setGuideOpen] = useState(false);

  useEffect(() => {
    if (id) {
      selectRoute(id);
      useFeedbackStore.getState().loadFeedback("route", id);
    }
  }, [id, selectRoute]);

  // Close detail panel on unmount
  useEffect(() => {
    return () => closeStopDetail();
  }, [closeStopDetail]);

  const handleGuideQuestion = async (question: string) => {
    if (!id) return;
    const currentHistory = guideMessages.map((m) => ({
      role: m.role,
      content: m.content,
    }));
    setGuideMessages((m) => [...m, { role: "user", content: question }]);
    setGuiding(true);
    try {
      const resp = await routesApi.guide(id, question, currentHistory);
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
          <span className="typing-dot h-2 w-2 rounded-full bg-green-500" />
          <span className="typing-dot h-2 w-2 rounded-full bg-green-500" />
          <span className="typing-dot h-2 w-2 rounded-full bg-green-500" />
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
      {/* Guide chat drawer */}
      <CollapsibleDrawer open={guideOpen} width="w-80">
        <div className="flex flex-col h-full">
          <div className="px-4 py-4 border-b border-stone-200/60 shrink-0">
            <h2 className="text-sm font-semibold text-stone-900">
              Guia interactivo
            </h2>
            <p className="text-xs text-stone-400 mt-0.5">
              Pregunta sobre esta ruta
            </p>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
            {guideMessages.length === 0 && !guiding && (
              <div className="flex flex-col items-center justify-center h-full text-center px-4">
                <svg className="w-10 h-10 text-stone-200 mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
                </svg>
                <p className="text-xs text-stone-400">
                  Pregunta sobre las paradas, historia o cualquier detalle de esta ruta
                </p>
              </div>
            )}
            {guideMessages.map((m, i) => (
              <div
                key={i}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <span
                  className={`inline-block rounded-2xl px-3 py-2 text-xs leading-relaxed max-w-[90%] ${
                    m.role === "user"
                      ? "bg-gradient-to-br from-green-700 to-emerald-700 text-white rounded-br-md"
                      : "bg-stone-50 border border-stone-200 text-stone-700 rounded-bl-md"
                  }`}
                >
                  {m.role === "assistant" ? (
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="mb-1.5 last:mb-0">{children}</p>,
                        ol: ({ children }) => <ol className="list-decimal pl-3.5 mb-1.5 last:mb-0 space-y-0.5">{children}</ol>,
                        ul: ({ children }) => <ul className="list-disc pl-3.5 mb-1.5 last:mb-0 space-y-0.5">{children}</ul>,
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
                <span className="inline-block rounded-2xl rounded-bl-md bg-stone-50 border border-stone-200 px-3 py-2">
                  <span className="flex gap-1">
                    <span className="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" />
                    <span className="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" />
                    <span className="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" />
                  </span>
                </span>
              </div>
            )}
          </div>

          {/* Input — pinned to bottom */}
          <div className="px-3 py-3 border-t border-stone-200/60 shrink-0">
            <ChatInput
              onSend={handleGuideQuestion}
              disabled={guiding}
              placeholder="Pregunta sobre la ruta..."
            />
          </div>
        </div>
      </CollapsibleDrawer>

      {/* Main content */}
      <div
        className={`absolute top-0 bottom-0 overflow-y-auto transition-all duration-300 ${
          guideOpen ? "left-80" : "left-0"
        } ${hasDetail ? "right-[560px]" : "right-0"}`}
      >
        <div className="mx-auto max-w-4xl px-6 py-8 space-y-10">
          {/* Header */}
          <div>
            <div className="flex items-center gap-3 mb-3">
              <button
                onClick={() => setGuideOpen((v) => !v)}
                className="shrink-0 relative flex h-9 w-9 items-center justify-center rounded-lg border border-stone-200 bg-white text-stone-500 hover:text-stone-700 hover:border-stone-300 transition-colors"
                aria-label={guideOpen ? "Cerrar guia" : "Abrir guia"}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
                </svg>
                {guideMessages.length > 0 && (
                  <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-green-600 text-[10px] font-bold text-white">
                    {guideMessages.length}
                  </span>
                )}
              </button>
              <Link
                href="/routes"
                className="inline-flex items-center gap-1 text-sm text-green-700 hover:text-green-700 transition-colors"
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
            </div>
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
              <FeedbackButtons targetType="route" targetId={activeRoute.id} />
            </div>
          </div>

          {/* Route content: new or legacy layout */}
          {hasNewFormat ? (
            <InterleavedStopsLayout route={activeRoute} />
          ) : (
            <LegacyStopsLayout route={activeRoute} />
          )}
        </div>
      </div>

      {/* Detail panel — slides in from right */}
      {hasDetail && (
        <aside className="absolute right-0 top-0 bottom-0 w-[560px] z-10 max-md:w-full">
          <RouteDetailPanel />
        </aside>
      )}
    </div>
  );
}
