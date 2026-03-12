"use client";

import { useState } from "react";
import { accessibility } from "@/lib/api";

export default function AccessibilityPage() {
  const [text, setText] = useState("");
  const [level, setLevel] = useState<"basic" | "intermediate">("basic");
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleSimplify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await accessibility.simplify({ text, level });
      setResult(resp.simplified_text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al simplificar");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!result) return;
    navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-stone-900">Lectura Fácil</h1>
        <p className="text-stone-500 mt-1">
          Simplifica textos sobre patrimonio histórico para mayor accesibilidad
        </p>
      </div>

      <form onSubmit={handleSimplify} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-2">Nivel de simplificación</label>
          <div className="grid grid-cols-2 gap-3">
            {([
              { value: "basic", label: "Básico", desc: "Máxima simplicidad" },
              { value: "intermediate", label: "Intermedio", desc: "Público general" },
            ] as const).map((opt) => (
              <label key={opt.value} className="cursor-pointer">
                <input
                  type="radio"
                  name="level"
                  value={opt.value}
                  checked={level === opt.value}
                  onChange={() => setLevel(opt.value)}
                  className="sr-only"
                />
                <div
                  className={`rounded-xl border-2 p-4 transition-all ${
                    level === opt.value
                      ? "border-amber-400 bg-amber-50/50 shadow-sm"
                      : "border-stone-200 bg-white hover:border-stone-300"
                  }`}
                >
                  <p className="font-semibold text-sm text-stone-900">{opt.label}</p>
                  <p className="text-xs text-stone-500 mt-0.5">{opt.desc}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1.5">Texto original</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            placeholder="Pega aquí el texto patrimonial que quieres simplificar..."
            className="w-full rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm focus:border-amber-400 focus:ring-2 focus:ring-amber-100 outline-none resize-y transition-all"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !text.trim()}
          className="w-full rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 py-3 text-sm font-semibold text-white shadow-sm hover:shadow-md transition-all disabled:opacity-50"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Simplificando...
            </span>
          ) : (
            "Simplificar texto"
          )}
        </button>
      </form>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700 flex items-start gap-2">
          <svg className="w-5 h-5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-stone-900">Texto simplificado</h2>
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 text-xs text-stone-500 hover:text-amber-600 transition-colors"
            >
              {copied ? (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                  </svg>
                  Copiado
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9.75a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" />
                  </svg>
                  Copiar
                </>
              )}
            </button>
          </div>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 px-6 py-5 text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">
            {result}
          </div>
        </div>
      )}
    </div>
  );
}
