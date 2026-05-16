import { describe, expect, it } from "vitest";
import type { ApiProduct } from "../types";
import { normalizeProduct, normalizeProducts } from "./productUtils";

describe("normalizeProduct", () => {
  it("maps API fields to Product with defaults", () => {
    const api: ApiProduct = {
      id: 1,
      name: "Áo",
      description: "Mô tả",
      price: "99000",
      category: { id: 1, name: "Áo" },
      promotion: null,
    };

    const p = normalizeProduct(api);
    expect(p.id).toBe(1);
    expect(p.name).toBe("Áo");
    expect(p.stock).toBe(0);
    expect(p.variants).toEqual([]);
    expect(p.image).toMatch(/^https?:\/\//);
  });

  it("normalizeProducts maps list", () => {
    const list = normalizeProducts([]);
    expect(list).toEqual([]);
  });
});
