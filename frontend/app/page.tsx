import Link from "next/link";

const features = [
  {
    href: "/search",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
    ),
    title: "Busqueda",
    description: "Encuentra bienes patrimoniales mediante busqueda semantica. Filtra por provincia, municipio y tipo de patrimonio.",
    cta: "Buscar patrimonio",
    gradient: "from-green-600 to-emerald-600",
  },
  {
    href: "/routes",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z" />
      </svg>
    ),
    title: "Rutas Virtuales",
    description: "Genera rutas culturales personalizadas por provincia, tipo de patrimonio e intereses. Incluye narrativa y guia interactivo.",
    cta: "Crear mi ruta",
    gradient: "from-emerald-500 to-teal-500",
  },
];

export default function Home() {
  return (
    <div className="mx-auto max-w-6xl px-6">
      {/* Hero */}
      <div className="py-20 text-center">
        <div className="inline-flex items-center gap-2 rounded-full bg-green-50 border border-green-200/60 px-4 py-1.5 text-sm text-green-700 mb-6">
          <span className="h-1.5 w-1.5 rounded-full bg-green-600" />
          Universidad de Jaén · Patrimonio de Andalucía
        </div>
        <h1 className="text-5xl font-bold tracking-tight text-stone-900 sm:text-6xl">
          Patrimonio Histórico
          <span className="block bg-gradient-to-r from-green-700 via-emerald-600 to-teal-600 bg-clip-text text-transparent">
            Andaluz
          </span>
        </h1>
        <p className="mt-6 text-lg text-stone-500 max-w-2xl mx-auto leading-relaxed">
          Asistente inteligente de Patrimonio de Andalucía.
          Explora, pregunta y descubre el rico patrimonio cultural de Andalucía.
        </p>
      </div>

      {/* Feature cards */}
      <div className="grid gap-6 md:grid-cols-2 max-w-3xl mx-auto pb-16">
        {features.map((f) => (
          <Link
            key={f.href}
            href={f.href}
            className="group relative overflow-hidden rounded-2xl border border-stone-200/60 bg-white p-7 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300"
          >
            <div className={`inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${f.gradient} text-white shadow-sm mb-5`}>
              {f.icon}
            </div>
            <h2 className="text-lg font-semibold text-stone-900 mb-2">
              {f.title}
            </h2>
            <p className="text-stone-500 text-sm leading-relaxed mb-6">
              {f.description}
            </p>
            <span className="inline-flex items-center gap-1.5 text-sm font-medium text-green-700 group-hover:gap-2.5 transition-all">
              {f.cta}
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </span>
            <div className={`absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r ${f.gradient} opacity-0 group-hover:opacity-100 transition-opacity`} />
          </Link>
        ))}
      </div>

      {/* Stats bar */}
      <div className="rounded-2xl bg-gradient-to-r from-stone-800 to-stone-900 p-8 mb-16 text-center">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[
            { value: "134K+", label: "Bienes catalogados" },
            { value: "30K", label: "Patrimonio Inmueble" },
            { value: "100K", label: "Patrimonio Mueble" },
            { value: "8", label: "Provincias andaluzas" },
          ].map((stat) => (
            <div key={stat.label}>
              <p className="text-2xl font-bold text-white">{stat.value}</p>
              <p className="text-sm text-stone-400 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
