export interface ActiveFilter {
  type: "province" | "municipality" | "heritage_type";
  value: string;
  label: string;
  matchedText: string;
}

export function collectFilters(filters: ActiveFilter[]) {
  const heritage: string[] = [];
  const provinces: string[] = [];
  const municipalities: string[] = [];
  for (const f of filters) {
    if (f.type === "heritage_type") heritage.push(f.value);
    if (f.type === "province") provinces.push(f.value);
    if (f.type === "municipality") municipalities.push(f.value);
  }
  return {
    heritage_type_filter: heritage.length ? heritage : null,
    province_filter: provinces.length ? provinces : null,
    municipality_filter: municipalities.length ? municipalities : null,
  };
}
