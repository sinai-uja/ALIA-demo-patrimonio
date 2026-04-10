export function Footer() {
  return (
    <footer className="bg-white border-t border-stone-200/60">
      <div className="mx-auto max-w-6xl px-6 py-6">
        {/* Logos row */}
        <div className="flex flex-wrap items-center justify-center gap-8 sm:gap-12">
          <a
            href="https://sinai.ujaen.es/"
            target="_blank"
            rel="noopener noreferrer"
            className="opacity-80 hover:opacity-100 transition-opacity"
          >
            <img src="/images/sinai.png" alt="Departamento SINAI - Universidad de Jaén" className="h-8 sm:h-10 w-auto" />
          </a>
          <a
            href="https://www.ujaen.es/"
            target="_blank"
            rel="noopener noreferrer"
            className="opacity-80 hover:opacity-100 transition-opacity"
          >
            <img src="/images/uja.png" alt="Universidad de Jaén" className="h-6 sm:h-7 w-auto" />
          </a>
          <a
            href="https://www.iaph.es/"
            target="_blank"
            rel="noopener noreferrer"
            className="opacity-80 hover:opacity-100 transition-opacity"
          >
            <img src="/images/iaph.png" alt="Instituto Andaluz de Patrimonio Histórico" className="h-8 sm:h-10 w-auto" />
          </a>
          <a
            href="https://alia.gob.es/"
            target="_blank"
            rel="noopener noreferrer"
            className="opacity-80 hover:opacity-100 transition-opacity"
          >
            <img src="/images/alia.png" alt="Proyecto ALIA" className="h-8 sm:h-10 w-auto" />
          </a>
          <a
            href="https://www.innovasur.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="opacity-80 hover:opacity-100 transition-opacity"
          >
            <img src="/images/innovasur.png" alt="Innovasur" className="h-6 sm:h-7 w-auto" />
          </a>
        </div>

        <div className="mt-4 pt-4 border-t border-stone-100 space-y-1">
          <p className="text-[11px] text-stone-400 text-center">
            Funded by: Ministerio para la Transformación Digital y de la Función Pública — EU NextGenerationEU, within the project Desarrollo de Modelos ALIA
          </p>
          <p className="text-[11px] text-stone-300 text-center">
            © {new Date().getFullYear()} Instituto Andaluz de Patrimonio Histórico · Universidad de Jaén
          </p>
        </div>
      </div>
    </footer>
  );
}
