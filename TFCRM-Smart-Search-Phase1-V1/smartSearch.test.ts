import { describe, expect, it } from "vitest";
import { normalizeSearchText, smartSearchMatches, tokenizeSearchQuery } from "./smartSearch";

describe("Smart Search Phase 1", () => {
  it("normalizes Arabic alef variants", () => {
    expect(normalizeSearchText("أمل إيمان آدم ٱلسلام")).toBe("امل ايمان ادم السلام");
  });
  it("removes tashkeel and tatweel", () => {
    expect(normalizeSearchText("صَيْدَلِيَّة الأَمــــل")).toBe("صيدلية الامل");
  });
  it("is case-insensitive and supports partial matching", () => {
    expect(smartSearchMatches("Medical Center", "MED")).toBe(true);
    expect(smartSearchMatches("Medical Center", "ical cen")).toBe(true);
  });
  it("normalizes whitespace and mixed language", () => {
    expect(normalizeSearchText("  صيدلية   El   Amal  ")).toBe("صيدلية el amal");
    expect(smartSearchMatches("صيدلية El Amal", "صيدلية el")).toBe(true);
  });
  it("requires all query tokens", () => {
    expect(tokenizeSearchQuery(" صيدلية AMAL ")).toEqual(["صيدلية", "amal"]);
    expect(smartSearchMatches("AMAL الجديدة - صيدلية", "صيدلية amal")).toBe(true);
    expect(smartSearchMatches("AMAL الجديدة", "صيدلية amal")).toBe(false);
  });
  it("treats empty search as no filter", () => {
    expect(smartSearchMatches("anything", "   ")).toBe(true);
  });
  it("does not add fuzzy or transliteration in Phase 1", () => {
    expect(smartSearchMatches("الأمل", "el amal")).toBe(false);
    expect(smartSearchMatches("Furniture", "furntiure")).toBe(false);
  });
});
