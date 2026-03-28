export function Footer() {
  return (
    <footer className="bg-white border-t border-stone-200/60">
      <div className="mx-auto max-w-6xl px-6 py-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          {/* Left: branding */}
          <div>
            <p className="text-sm font-semibold text-stone-800">
              Patrimonio Histórico Andaluz
            </p>
            <p className="text-xs text-stone-400 mt-0.5">
              Asistente inteligente para el patrimonio cultural de Andalucía
            </p>
          </div>

          {/* Right: credits */}
          <div className="sm:text-right">
            <p className="text-xs text-stone-500">
              Desarrollado por{" "}
              <span className="font-semibold text-stone-700">Innovasur</span>
            </p>
            <p className="text-xs text-stone-400 mt-0.5">
              Departamento{" "}
              <span className="font-medium text-stone-600">SINAI</span>
              {" · "}Universidad de Jaén
            </p>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-stone-100">
          <p className="text-[11px] text-stone-300 text-center">
            © {new Date().getFullYear()} Instituto Andaluz de Patrimonio Histórico · Universidad de Jaén
          </p>
        </div>
      </div>
    </footer>
  );
}
