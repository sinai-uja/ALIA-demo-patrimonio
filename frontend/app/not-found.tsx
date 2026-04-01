import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center pt-32 gap-4 px-6">
      <p className="text-6xl font-bold text-stone-200">404</p>
      <h1 className="text-lg font-semibold text-stone-900">Pagina no encontrada</h1>
      <p className="text-sm text-stone-500 text-center max-w-md">
        La pagina que buscas no existe o ha sido movida.
      </p>
      <Link
        href="/"
        className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Volver al inicio
      </Link>
    </div>
  );
}
