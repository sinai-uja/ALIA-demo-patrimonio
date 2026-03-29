import Link from "next/link";

const features = [
  {
    href: "/search",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
    ),
    title: "Busqueda Semantica",
    description: "Encuentra bienes patrimoniales por similitud semantica. Filtra por provincia, municipio y tipo.",
    cta: "Buscar patrimonio",
    gradient: "from-green-600 to-emerald-600",
  },
  {
    href: "/routes",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z" />
      </svg>
    ),
    title: "Rutas Virtuales",
    description: "Genera rutas culturales personalizadas con narrativa e incluye un guia interactivo.",
    cta: "Crear mi ruta",
    gradient: "from-emerald-500 to-teal-500",
  },
];

export default function Home() {
  return (
    <>
      {/* Hero — full-width background image */}
      <div
        className="relative overflow-hidden"
        style={{ marginLeft: "calc(-50vw + 50%)", marginRight: "calc(-50vw + 50%)" }}
      >
        <img
          src="/header.jpg"
          alt=""
          aria-hidden="true"
          className="absolute inset-0 w-full h-full object-cover object-center"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-stone-900/55 via-stone-900/50 to-stone-900/65" />
        <div className="relative mx-auto max-w-6xl px-6 py-12 text-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 border border-white/20 px-4 py-1.5 text-sm text-white/90 mb-4 backdrop-blur-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
            Universidad de Jaén · Patrimonio de Andalucía
          </div>
          <h1 className="text-5xl font-bold tracking-tight text-white sm:text-6xl drop-shadow-sm">
            Patrimonio Histórico
            <span className="block bg-gradient-to-r from-green-300 via-emerald-300 to-teal-300 bg-clip-text text-transparent">
              Andaluz
            </span>
          </h1>
          <p className="mt-4 text-lg text-white/75 max-w-2xl mx-auto leading-relaxed">
            Explora, pregunta y descubre el rico patrimonio cultural de Andalucía
            con ayuda de inteligencia artificial.
          </p>
        </div>
      </div>

      {/* Rest of page */}
      <div className="mx-auto max-w-6xl px-6">
        {/* Feature cards */}
        <div className="grid gap-4 sm:grid-cols-2 py-8">
          {features.map((f) => (
            <Link
              key={f.href}
              href={f.href}
              className="group relative overflow-hidden rounded-xl border border-stone-200/60 bg-white p-5 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
            >
              <div className={`inline-flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br ${f.gradient} text-white shadow-sm mb-3`}>
                {f.icon}
              </div>
              <h2 className="text-sm font-semibold text-stone-900 mb-1.5">{f.title}</h2>
              <p className="text-stone-500 text-xs leading-relaxed mb-4">{f.description}</p>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 group-hover:gap-1.5 transition-all">
                {f.cta}
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </span>
              <div className={`absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r ${f.gradient} opacity-0 group-hover:opacity-100 transition-opacity`} />
            </Link>
          ))}
        </div>

        {/* Stats bar */}
        <div className="rounded-2xl bg-gradient-to-r from-stone-800 to-stone-900 p-6 mb-8">
          <p className="text-xs text-stone-400 text-center mb-4">
            134K+ bienes catalogados en el catálogo oficial
          </p>
          <div className="grid grid-cols-4 gap-4 text-center">
            {[
              { value: "30K", label: "Patrimonio Inmueble", dot: "bg-green-500" },
              { value: "100K", label: "Patrimonio Mueble", dot: "bg-purple-500" },
              { value: "2K", label: "Patrimonio Inmaterial", dot: "bg-teal-500" },
              { value: "117", label: "Paisajes Culturales", dot: "bg-sky-500" },
            ].map((stat) => (
              <div key={stat.label} className="flex flex-col items-center gap-1">
                <span className={`h-2 w-2 rounded-full ${stat.dot}`} />
                <p className="text-xl font-bold text-white">{stat.value}</p>
                <p className="text-xs text-stone-400">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
