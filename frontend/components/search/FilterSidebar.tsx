"use client";

import { useState, useMemo } from "react";
import { useSearchStore, type ActiveFilter } from "@/store/search";

const HERITAGE_TYPE_LABELS: Record<string, string> = {
  patrimonio_inmueble: "Patrimonio Inmueble",
  patrimonio_mueble: "Patrimonio Mueble",
  patrimonio_inmaterial: "Patrimonio Inmaterial",
  paisaje_cultural: "Paisaje Cultural",
};

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`h-4 w-4 text-stone-400 transition-transform ${open ? "rotate-90" : ""}`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}

function ColorDot({ color }: { color: string }) {
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />;
}

function FilterCheckbox({
  type,
  value,
  label,
  checked,
  onToggle,
}: {
  type: ActiveFilter["type"];
  value: string;
  label: string;
  checked: boolean;
  onToggle: (filter: ActiveFilter, checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 py-1 px-1 rounded hover:bg-stone-50 cursor-pointer text-sm text-stone-700">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) =>
          onToggle({ type, value, label, matchedText: "" }, e.target.checked)
        }
        className="h-3.5 w-3.5 rounded border-stone-300 text-amber-600 focus:ring-amber-500"
      />
      <span className="truncate">{label}</span>
    </label>
  );
}

export function FilterSidebar() {
  const activeFilters = useSearchStore((s) => s.activeFilters);
  const filterValues = useSearchStore((s) => s.filterValues);
  const addFilter = useSearchStore((s) => s.addFilter);
  const removeFilter = useSearchStore((s) => s.removeFilter);
  const clearFilters = useSearchStore((s) => s.clearFilters);

  const [openSections, setOpenSections] = useState({
    heritage: true,
    province: true,
    municipality: true,
  });

  const [municipalitySearch, setMunicipalitySearch] = useState("");

  const activeProvinces = activeFilters.filter((f) => f.type === "province");

  const filteredMunicipalities = useMemo(() => {
    if (!filterValues?.municipalities) return [];
    if (!municipalitySearch.trim()) return filterValues.municipalities;
    const term = municipalitySearch.toLowerCase();
    return filterValues.municipalities.filter((m) =>
      m.toLowerCase().includes(term)
    );
  }, [filterValues?.municipalities, municipalitySearch]);

  function isChecked(type: ActiveFilter["type"], value: string): boolean {
    return activeFilters.some((f) => f.type === type && f.value === value);
  }

  function handleToggle(filter: ActiveFilter, checked: boolean) {
    if (checked) {
      addFilter(filter);
    } else {
      removeFilter(filter);
    }
  }

  function sortCheckedFirst<T>(items: T[], getValue: (item: T) => { type: ActiveFilter["type"]; value: string }): T[] {
    return [...items].sort((a, b) => {
      const aChecked = isChecked(getValue(a).type, getValue(a).value);
      const bChecked = isChecked(getValue(b).type, getValue(b).value);
      if (aChecked === bChecked) return 0;
      return aChecked ? -1 : 1;
    });
  }

  const sortedHeritageTypes = useMemo(
    () => sortCheckedFirst(
      Object.entries(HERITAGE_TYPE_LABELS),
      ([value]) => ({ type: "heritage_type" as const, value }),
    ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [activeFilters],
  );

  const sortedProvinces = useMemo(
    () => sortCheckedFirst(
      filterValues?.provinces ?? [],
      (p) => ({ type: "province" as const, value: p }),
    ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [filterValues?.provinces, activeFilters],
  );

  const sortedMunicipalities = useMemo(
    () => sortCheckedFirst(
      filteredMunicipalities,
      (m) => ({ type: "municipality" as const, value: m }),
    ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [filteredMunicipalities, activeFilters],
  );

  function toggleSection(key: keyof typeof openSections) {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className="p-4 space-y-4 text-sm">
      {/* Header + clear */}
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-stone-800">Filtros</h2>
        {activeFilters.length > 0 && (
          <button
            onClick={clearFilters}
            className="text-xs text-amber-600 hover:text-amber-700 font-medium"
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {/* Heritage type section */}
      <div>
        <button
          onClick={() => toggleSection("heritage")}
          className="flex w-full items-center gap-2 py-1.5 font-medium text-stone-700 hover:text-stone-900"
        >
          <ChevronIcon open={openSections.heritage} />
          <ColorDot color="bg-amber-400" />
          <span>Tipo de patrimonio</span>
        </button>
        {openSections.heritage && (
          <div className="ml-6 mt-1 space-y-0.5">
            {sortedHeritageTypes.map(([value, label]) => (
              <FilterCheckbox
                key={value}
                type="heritage_type"
                value={value}
                label={label}
                checked={isChecked("heritage_type", value)}
                onToggle={handleToggle}
              />
            ))}
          </div>
        )}
      </div>

      {/* Province section */}
      <div>
        <button
          onClick={() => toggleSection("province")}
          className="flex w-full items-center gap-2 py-1.5 font-medium text-stone-700 hover:text-stone-900"
        >
          <ChevronIcon open={openSections.province} />
          <ColorDot color="bg-blue-400" />
          <span>Provincia</span>
        </button>
        {openSections.province && (
          <div className="ml-6 mt-1 space-y-0.5 max-h-64 overflow-y-auto">
            {sortedProvinces.map((province) => (
              <FilterCheckbox
                key={province}
                type="province"
                value={province}
                label={province}
                checked={isChecked("province", province)}
                onToggle={handleToggle}
              />
            ))}
            {sortedProvinces.length === 0 && (
              <p className="text-xs text-stone-400 py-1">Sin provincias disponibles</p>
            )}
          </div>
        )}
      </div>

      {/* Municipality section */}
      <div>
          <button
            onClick={() => toggleSection("municipality")}
            className="flex w-full items-center gap-2 py-1.5 font-medium text-stone-700 hover:text-stone-900"
          >
            <ChevronIcon open={openSections.municipality} />
            <ColorDot color="bg-emerald-400" />
            <span>Municipio</span>
          </button>
          {openSections.municipality && (
            <div className="ml-6 mt-1 space-y-1">
              <input
                type="text"
                placeholder="Buscar municipio..."
                value={municipalitySearch}
                onChange={(e) => setMunicipalitySearch(e.target.value)}
                className="w-full rounded border border-stone-200 px-2 py-1 text-xs text-stone-700 placeholder:text-stone-400 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400"
              />
              <div className="max-h-64 overflow-y-auto space-y-0.5">
                {sortedMunicipalities.map((municipality) => (
                  <FilterCheckbox
                    key={municipality}
                    type="municipality"
                    value={municipality}
                    label={municipality}
                    checked={isChecked("municipality", municipality)}
                    onToggle={handleToggle}
                  />
                ))}
                {sortedMunicipalities.length === 0 && (
                  <p className="text-xs text-stone-400 py-1">Sin resultados</p>
                )}
              </div>
            </div>
          )}
      </div>
    </div>
  );
}
