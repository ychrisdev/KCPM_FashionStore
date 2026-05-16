import { describe, expect, it } from "vitest";
import { isStaffRole } from "./staff";

describe("isStaffRole", () => {
  it("returns true for staff and admin", () => {
    expect(isStaffRole("staff")).toBe(true);
    expect(isStaffRole("admin")).toBe(true);
  });

  it("returns false for customer and empty", () => {
    expect(isStaffRole("customer")).toBe(false);
    expect(isStaffRole(null)).toBe(false);
    expect(isStaffRole(undefined)).toBe(false);
  });
});
