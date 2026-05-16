import type { Product, ApiProduct } from "../types";

const PLACEHOLDER_IMAGE =
  "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop";

export function normalizeProduct(
  api: ApiProduct & { discount_percent_display?: number },
): Product {
  const priceStr =
    typeof api.price === "number" ? String(api.price) : (api.price ?? "0");
  return {
    id: api.id,
    name: api.name,
    description: api.description ?? "",
    price: priceStr,
    old_price: api.old_price ?? null,
    stock: api.stock ?? 0,
    image: api.image ?? PLACEHOLDER_IMAGE,
    category: api.category,
    promotion: api.promotion,
    variants: api.variants ?? [],
    rating: api.rating ?? 0,
    sold_count: api.sold_count ?? 0,
    discount_percent_display: api.discount_percent_display ?? 0,
  };
}

export function normalizeProducts(
  apiList: (ApiProduct & { discount_percent_display?: number })[],
): Product[] {
  return apiList.map(normalizeProduct);
}
