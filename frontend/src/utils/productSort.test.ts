import { describe, expect, it } from "vitest";
import {
  compareCatalogByNameAsc,
  compareCatalogByPopular,
  effectiveCatalogPrice,
  filterAndSortCatalogProducts,
  parseCatalogSortKey,
} from "./productSort";

describe("parseCatalogSortKey", () => {
  it("returns default for unknown", () => {
    expect(parseCatalogSortKey("nope")).toBe("default");
  });
  it("accepts valid keys", () => {
    expect(parseCatalogSortKey("popular")).toBe("popular");
  });
});

describe("effectiveCatalogPrice", () => {
  it("applies promotion percent", () => {
    expect(
      effectiveCatalogPrice({
        name: "A",
        price: 100,
        promotion: { discount_percent: 10 },
      }),
    ).toBe(90);
  });
});

describe("compareCatalogByNameAsc", () => {
  it("sorts full string not only first character", () => {
    expect(
      compareCatalogByNameAsc(
        { name: "Item B", price: 1 },
        { name: "Item A", price: 1 },
      ),
    ).toBeGreaterThan(0);
  });
});

describe("compareCatalogByPopular", () => {
  it("uses sold_count", () => {
    expect(
      compareCatalogByPopular(
        { name: "a", price: 1, sold_count: 1 },
        { name: "b", price: 1, sold_count: 5 },
      ),
    ).toBeGreaterThan(0);
  });
});

describe("filterAndSortCatalogProducts", () => {
  const items = [
    { id: 1, name: "B", description: "", price: 100, sold_count: 2 },
    { id: 2, name: "A", description: "", price: 200, sold_count: 10 },
  ] as const;

  it("sorts by name-asc", () => {
    const out = filterAndSortCatalogProducts([...items], "", "name-asc");
    expect(out.map((x) => x.id)).toEqual([2, 1]);
  });

  it("sorts by popular", () => {
    const out = filterAndSortCatalogProducts([...items], "", "popular");
    expect(out.map((x) => x.id)).toEqual([2, 1]);
  });
});
