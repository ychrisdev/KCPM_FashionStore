export type CatalogSortKey =
  | "default"
  | "price-asc"
  | "price-desc"
  | "name-asc"
  | "popular"
  | "discount";

export const CATALOG_SORT_KEYS: readonly CatalogSortKey[] = [
  "default",
  "price-asc",
  "price-desc",
  "name-asc",
  "popular",
  "discount",
] as const;

export function parseCatalogSortKey(
  raw: string | null | undefined,
): CatalogSortKey {
  const v = raw ?? "default";
  return (CATALOG_SORT_KEYS as readonly string[]).includes(v)
    ? (v as CatalogSortKey)
    : "default";
}

export interface CatalogSortProduct {
  name: string;
  description?: string | null;
  price: string | number;
  old_price?: string | number | null;
  discount_percent_display?: number | null;
  promotion?: { discount_percent?: number } | null;
  sold_count?: number | null;
}

export function effectiveCatalogPrice(p: CatalogSortProduct): number {
  const base = Number(p.price);
  if (p.old_price && Number(p.old_price) > base) {
    return base;
  }
  const disc = p.promotion?.discount_percent ?? 0;
  return base * (1 - disc / 100);
}

export function compareCatalogByNameAsc(
  a: CatalogSortProduct,
  b: CatalogSortProduct,
): number {
  return a.name
    .trim()
    .localeCompare(b.name.trim(), "vi", { sensitivity: "base" });
}

export function compareCatalogByPopular(
  a: CatalogSortProduct,
  b: CatalogSortProduct,
): number {
  return (b.sold_count ?? 0) - (a.sold_count ?? 0);
}

export function getDiscountPercent(p: CatalogSortProduct): number {
  if (p.discount_percent_display != null && p.discount_percent_display > 0) {
    return p.discount_percent_display;
  }
  if (p.promotion?.discount_percent) {
    return p.promotion.discount_percent;
  }
  const current = Number(p.price);
  const original = Number(p.old_price ?? 0);
  if (original > current && current > 0) {
    return Math.round(((original - current) / original) * 100);
  }
  return 0;
}

export function filterAndSortCatalogProducts<T extends CatalogSortProduct>(
  products: readonly T[],
  query: string,
  sort: CatalogSortKey,
): T[] {
  let list = [...products];

  if (query.trim()) {
    const q = query.toLowerCase();
    list = list.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.description ?? "").toLowerCase().includes(q),
    );
  }

  const effectivePrice = (p: T) => effectiveCatalogPrice(p);

  if (sort === "price-asc") {
    list.sort((a, b) => effectivePrice(a) - effectivePrice(b));
  } else if (sort === "price-desc") {
    list.sort((a, b) => effectivePrice(b) - effectivePrice(a));
  } else if (sort === "name-asc") {
    list.sort((a, b) => compareCatalogByNameAsc(a, b));
  } else if (sort === "popular") {
    list.sort((a, b) => compareCatalogByPopular(a, b));
  } else if (sort === "discount") {
    list.sort((a, b) => getDiscountPercent(b) - getDiscountPercent(a));
  }

  return list;
}
