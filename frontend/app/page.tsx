import Link from "next/link";

const features = [
  {
    href: "/chat",
    icon: "💬",
    title: "Chatbot Patrimonial",
    description: "Conversa con el asistente sobre el patrimonio histórico andaluz. Consulta bienes inmuebles, inmateriales, muebles y paisajes culturales.",
    cta: "Iniciar conversación",
  },
  {
    href: "/routes",
    icon: "🗺️",
    title: "Rutas Virtuales",
    description: "Genera rutas culturales personalizadas según provincia, tipo de patrimonio e intereses. El sistema selecciona los mejores elementos para ti.",
    cta: "Crear mi ruta",
  },
  {
    href: "/accessibility",
    icon: "📖",
    title: "Lectura Fácil",
    description: "Transforma textos patrimoniales complejos en versiones accesibles siguiendo las directrices de Lectura Fácil para personas con discapacidad cognitiva.",
    cta: "Simplificar texto",
  },
];

export default function Home() {
  return (
    <div className="space-y-12">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-amber-900">
          Patrimonio Histórico Andaluz
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Asistente inteligente del Instituto Andaluz de Patrimonio Histórico (IAPH).
          Explora, pregunta y descubre el rico patrimonio cultural de Andalucía.
        </p>
        <p className="text-xs text-gray-400">
          Universidad de Jaén · RAG con MrBERT + Salamandra-7B
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {features.map((f) => (
          <Link
            key={f.href}
            href={f.href}
            className="group rounded-2xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-lg hover:border-amber-300 transition-all"
          >
            <div className="text-4xl mb-4">{f.icon}</div>
            <h2 className="text-xl font-semibold text-gray-900 group-hover:text-amber-700 transition-colors mb-2">
              {f.title}
            </h2>
            <p className="text-gray-600 text-sm leading-relaxed mb-6">
              {f.description}
            </p>
            <span className="inline-flex items-center gap-1 text-sm font-medium text-amber-700 group-hover:gap-2 transition-all">
              {f.cta} →
            </span>
          </Link>
        ))}
      </div>

      <div className="rounded-xl bg-amber-50 border border-amber-100 p-6 text-center">
        <p className="text-sm text-amber-800">
          <strong>Corpus:</strong> más de 134.000 bienes del patrimonio andaluz —
          Paisajes Culturales · Patrimonio Inmaterial · Patrimonio Inmueble · Patrimonio Mueble
        </p>
      </div>
    </div>
  );
}
