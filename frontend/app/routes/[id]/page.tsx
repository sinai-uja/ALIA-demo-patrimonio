"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useRoutesStore } from "@/store/routes";
import { routes as routesApi, type RagSource } from "@/lib/api";
import { ChatInput } from "@/components/chat/ChatInput";
import { RouteStopCard } from "@/components/routes/RouteStopCard";
import { RouteDetailPanel } from "@/components/routes/RouteDetailPanel";
import { FeedbackButtons } from "@/components/shared/FeedbackButtons";
import { useFeedbackStore } from "@/store/feedback";
import { SearchStopModal } from "@/components/routes/SearchStopModal";
import DeleteConfirmModal from "@/components/shared/DeleteConfirmModal";
import ReactMarkdown from "react-markdown";

const HERITAGE_TYPE_COLORS: Record<string, string> = {
  patrimonio_inmueble: "bg-green-100 text-green-700",
  patrimonio_mueble: "bg-purple-100 text-purple-700",
  patrimonio_inmaterial: "bg-teal-100 text-teal-700",
  paisaje_cultural: "bg-sky-100 text-sky-700",
};

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

/** "+" button rendered between stops (and at the end) in edit mode */
function AddStopButton({ onClick }: { onClick: () => void }) {
  return (
    <div className="py-2">
      <button
        onClick={onClick}
        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border-2 border-dashed border-stone-300 text-stone-400 hover:border-green-500 hover:text-green-600 hover:bg-green-50 transition-all text-sm font-medium"
        aria-label="Añadir nueva parada a la ruta"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Añadir nueva parada a la ruta
      </button>
    </div>
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
  const editing = useRoutesStore((s) => s.editing);
  const editLoading = useRoutesStore((s) => s.editLoading);
  const removeStop = useRoutesStore((s) => s.removeStop);
  const addStop = useRoutesStore((s) => s.addStop);

  // Delete confirmation state
  const [deleteTarget, setDeleteTarget] = useState<{ order: number; title: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Search modal state
  const [searchPosition, setSearchPosition] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      setTwoCol(entry.contentRect.width >= 700);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await removeStop(route.id, deleteTarget.order);
      setDeleteTarget(null);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Error al eliminar la parada");
    } finally {
      setDeleting(false);
    }
  };

  const handleAddStop = async (documentId: string) => {
    if (searchPosition === null) return;
    setAdding(true);
    try {
      await addStop(route.id, documentId, searchPosition);
      setSearchPosition(null);
    } catch {
      // keep modal open on error
    } finally {
      setAdding(false);
    }
  };

  return (
    <>
      {/* Introduction */}
      {route.introduction && (
        <p className="text-stone-600 leading-relaxed">{route.introduction}</p>
      )}

      {/* Roadmap: alternating card / narrative */}
      <div ref={containerRef} className="relative">
        {/* Edit loading overlay */}
        {editing && editLoading && (
          <div className="absolute inset-0 z-10 bg-white/60 backdrop-blur-[1px] rounded-xl flex items-center justify-center">
            <div className="flex items-center gap-2 bg-white/90 px-4 py-2 rounded-full shadow-sm border border-stone-200">
              <svg className="w-4 h-4 animate-spin text-green-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span className="text-sm text-stone-600">Actualizando ruta...</span>
            </div>
          </div>
        )}

        <h2 className="text-xl font-semibold text-stone-900 mb-5">Paradas</h2>

        {/* Add button at the very top in edit mode */}
        {editing && (
          <AddStopButton onClick={() => setSearchPosition(1)} />
        )}

        <div className="flex flex-col">
          {route.stops.map((stop, i) => (
            <div key={stop.order}>
              {twoCol ? (
                <div
                  className={`relative flex gap-6 items-center ${
                    i % 2 !== 0 ? "flex-row-reverse" : ""
                  }`}
                >
                  <div className="w-1/2 relative">
                    <RouteStopCard stop={stop} />
                    {editing && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleteTarget({ order: stop.order, title: stop.title }); }}
                        className="absolute top-2 right-2 w-7 h-7 rounded-full bg-red-500/90 text-white flex items-center justify-center shadow-md hover:bg-red-600 transition-colors z-10"
                        aria-label={`Eliminar ${stop.title}`}
                        title="Eliminar parada"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
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
                  <div className="relative">
                    <RouteStopCard stop={stop} />
                    {editing && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleteTarget({ order: stop.order, title: stop.title }); }}
                        className="absolute top-2 right-2 w-7 h-7 rounded-full bg-red-500/90 text-white flex items-center justify-center shadow-md hover:bg-red-600 transition-colors z-10"
                        aria-label={`Eliminar ${stop.title}`}
                        title="Eliminar parada"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                  {stop.narrative_segment && (
                    <p className="text-sm text-stone-600 leading-relaxed px-1">
                      {stop.narrative_segment}
                    </p>
                  )}
                </div>
              )}

              {/* Connector + add button between stops */}
              {i < route.stops.length - 1 && (
                editing ? (
                  <AddStopButton onClick={() => setSearchPosition(stop.order + 1)} />
                ) : (
                  <div className="flex justify-center py-1">
                    <div className="w-px h-8 bg-stone-200" />
                  </div>
                )
              )}

              {/* Add button after the last stop */}
              {editing && i === route.stops.length - 1 && (
                <AddStopButton onClick={() => setSearchPosition(stop.order + 1)} />
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

      {/* Delete confirmation modal */}
      {deleteTarget && (
        <DeleteConfirmModal
          title="Eliminar parada"
          entityName={deleteTarget.title}
          onConfirm={handleConfirmDelete}
          onCancel={() => { setDeleteTarget(null); setDeleteError(null); }}
          deleting={deleting}
          error={deleteError}
        />
      )}

      {/* Search stop modal */}
      {searchPosition !== null && (
        <SearchStopModal
          onSelect={handleAddStop}
          onClose={() => setSearchPosition(null)}
          adding={adding}
        />
      )}
    </>
  );
}

export default function RouteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { activeRoute, selectRoute, loading } = useRoutesStore();
  const editing = useRoutesStore((s) => s.editing);
  const setEditMode = useRoutesStore((s) => s.setEditMode);
  const hasDetail = useRoutesStore((s) => s.selectedStopAssetId !== null);
  const closeStopDetail = useRoutesStore((s) => s.closeStopDetail);
  const [guideMessages, setGuideMessages] = useState<
    { role: "user" | "assistant"; content: string; sources?: RagSource[] }[]
  >([]);
  const [guiding, setGuiding] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const [guideExpanded, setGuideExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  // Close chat when clicking outside
  useEffect(() => {
    if (!guideOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (chatRef.current && !chatRef.current.contains(e.target as Node)) {
        setGuideOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [guideOpen]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [guideMessages, guiding]);

  useEffect(() => {
    if (id) {
      selectRoute(id);
      useFeedbackStore.getState().loadFeedback("route", id);
    }
  }, [id, selectRoute]);

  // Close detail panel and exit edit mode on unmount
  useEffect(() => {
    return () => {
      closeStopDetail();
      setEditMode(false);
    };
  }, [closeStopDetail, setEditMode]);

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
      {/* Floating guide chat button — hidden when chat is open */}
      <button
        onClick={() => { setGuideOpen(true); if (window.innerWidth < 768) setGuideExpanded(true); }}
        className={`fixed bottom-6 left-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-green-600 to-emerald-700 text-white shadow-lg hover:scale-105 transition-all ${guideOpen ? "opacity-0 pointer-events-none scale-75" : "opacity-100 scale-100"}`}
        aria-label="Abrir guia"
      >
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
        </svg>
        {guideMessages.length > 0 && (
          <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {guideMessages.length}
          </span>
        )}
      </button>

      {/* Floating chat window */}
      <div
        ref={chatRef}
        className={`fixed bottom-0 left-0 z-40 rounded-t-2xl shadow-2xl border-t border-x border-stone-200 bg-white flex flex-col overflow-hidden origin-bottom transition-all duration-200 ${guideExpanded ? "w-[min(520px,100vw)] h-[min(600px,calc(100vh-4rem))]" : "w-[min(20rem,100vw)] h-[420px]"} ${
          guideOpen
            ? "opacity-100 scale-100"
            : "opacity-0 scale-95 pointer-events-none"
        }`}
      >
        {/* Header */}
        <div className="px-4 py-4 border-b border-stone-200/60 shrink-0 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-stone-900">
              Guia interactivo
            </h2>
            <p className="text-xs text-stone-400 mt-0.5">
              Pregunta sobre esta ruta
            </p>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setGuideExpanded((v) => !v)}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-stone-400 hover:text-stone-600 hover:bg-stone-100 transition-colors"
              aria-label={guideExpanded ? "Reducir ventana" : "Ampliar ventana"}
            >
              {guideExpanded ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 9V4.5M9 9H4.5M9 9 3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5 5.25 5.25" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
                </svg>
              )}
            </button>
            <button
              onClick={() => setGuideOpen(false)}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-stone-400 hover:text-stone-600 hover:bg-stone-100 transition-colors"
              aria-label="Cerrar guia"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
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
          <div ref={messagesEndRef} />
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

      {/* Main content */}
      <div
        className={`absolute top-0 bottom-0 left-0 overflow-y-scroll transition-all duration-300 ${
          hasDetail ? "right-[560px]" : "right-0"
        }`}
      >
        <div className="mx-auto max-w-4xl px-6 py-8 space-y-10">
          {/* Header */}
          <div>
            <div className="flex items-center justify-between mb-3">
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
              {hasNewFormat && (
                <button
                  onClick={() => setEditMode(!editing)}
                  className={`shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border transition-all ${
                    editing
                      ? "border-green-600 bg-green-50 text-green-700 hover:bg-green-100"
                      : "border-stone-300 text-stone-600 hover:border-green-600 hover:text-green-700"
                  }`}
                >
                  {editing ? (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                      </svg>
                      Dejar de editar
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                      </svg>
                      Editar ruta
                    </>
                  )}
                </button>
              )}
            </div>
            <div>
              <h1 className="text-3xl font-bold text-stone-900">
                {activeRoute.title}
              </h1>
            </div>
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
