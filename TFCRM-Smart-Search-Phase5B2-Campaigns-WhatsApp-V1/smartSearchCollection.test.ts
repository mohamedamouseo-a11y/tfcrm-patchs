import { describe, expect, it } from "vitest";
import { normalizedCollectionContainsAll, smartFilterCollection } from "./smartSearchCollection";

const rows = [
  { id: 1, text: "أحمد للأثاث" },
  { id: 2, text: "Modern Furniture Campaign" },
  { id: 3, text: "Marketing Campaign" },
];

describe("Smart Search Phase 5B2 collection fallback", () => {
  it("normalizes Arabic alef and tashkeel for exact contains", () => {
    expect(normalizedCollectionContainsAll("أَحْمَد للأثاث", "احمد")).toBe(true);
  });

  it("keeps English case-insensitive contains", () => {
    expect(normalizedCollectionContainsAll("Modern Furniture", "FURN")).toBe(true);
  });

  it("returns exact results before fuzzy alternatives", () => {
    const result = smartFilterCollection(rows, "campaign", (row) => row.text);
    expect(result.map((row) => row.id)).toEqual([2, 3]);
  });

  it("uses fuzzy only when exact results are empty", () => {
    const result = smartFilterCollection(rows, "furnture", (row) => row.text);
    expect(result.map((row) => row.id)).toEqual([2]);
  });

  it("does not fuzzy-match numeric-only identifiers", () => {
    const numericRows = [{ id: 1, text: "01012345678" }];
    expect(smartFilterCollection(numericRows, "01012345679", (row) => row.text)).toEqual([]);
  });
});
