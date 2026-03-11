"use client";

import { useState } from "react";
import { accessibility } from "@/lib/api";

export default function AccessibilityPage() {
  const [text, setText] = useState("");
  const [level, setLevel] = useState<"basic" | "intermediate">("basic");
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Lectura Fácil</h1>
        <p className="text-gray-500 text-sm">
          Simplifica textos sobre patrimonio histórico para mayor accesibilidad
        </p>
      </div>

      <form onSubmit={handleSimplify} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Nivel de simplificación</label>
          <div className="flex gap-4">
            {([
              { value: "basic", label: "Básico", desc: "Máxima simplicidad — discapacidad cognitiva" },
              { value: "intermediate", label: "Intermedio", desc: "Accesible para público general" },
            ] as const).map((opt) => (
              <label key={opt.value} className="flex-1 cursor-pointer">
                <input
                  type="radio"
                  name="level"
                  value={opt.value}
                  checked={level === opt.value}
                  onChange={() => setLevel(opt.value)}
                  className="sr-only"
                />
                <div
                  className={`rounded-xl border-2 p-3 transition ${
                    level === opt.value
                      ? "border-amber-500 bg-amber-50"
                      : "border-gray-200 bg-white hover:border-gray-300"
                  }`}
                >
                  <p className="font-medium text-sm text-gray-900">{opt.label}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{opt.desc}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Texto original</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            placeholder="Pega aquí el texto patrimonial que quieres simplificar…"
            className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none resize-y"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !text.trim()}
          className="w-full rounded-xl bg-amber-700 py-2.5 text-sm font-medium text-white hover:bg-amber-800 transition disabled:opacity-50"
        >
          {loading ? "Simplificando…" : "Simplificar texto"}
        </button>
      </form>

      {error && (
        <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-3">
          <h2 className="font-semibold text-gray-900">Texto simplificado</h2>
          <div className="rounded-xl border border-green-200 bg-green-50 px-5 py-4 text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
            {result}
          </div>
          <button
            onClick={() => navigator.clipboard.writeText(result)}
            className="text-xs text-gray-500 hover:text-amber-700 transition"
          >
            Copiar al portapapeles
          </button>
        </div>
      )}
    </div>
  );
}
