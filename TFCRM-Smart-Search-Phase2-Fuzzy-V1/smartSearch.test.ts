import { describe, expect, it } from "vitest";
import {
  damerauLevenshteinDistance,
  isFuzzySearchEligible,
  normalizeSearchText,
  scoreFuzzySearchRecord,
  smartSearchMatches,
} from "./smartSearch";

describe("Smart Search Phase 2 fuzzy fallback", () => {
  it("keeps Phase 1 Arabic alef normalization", () => {
    expect(normalizeSearchText("أحمد إبراهيم")).toBe("احمد ابراهيم");
  });

  it("keeps Phase 1 tashkeel/tatweel normalization", () => {
    expect(normalizeSearchText("مُـحَمَّد")).toBe("محمد");
  });

  it("keeps exact/contains matching behavior", () => {
    expect(smartSearchMatches("Modern Furniture House", "furn")).toBe(true);
  });

  it("supports a missing English character", () => {
    expect(scoreFuzzySearchRecord(["Furniture House"], "furnture")).not.toBeNull();
  });

  it("supports an extra English character", () => {
    expect(scoreFuzzySearchRecord(["marketing"], "markeeting")).not.toBeNull();
  });

  it("supports an English substitution", () => {
    expect(scoreFuzzySearchRecord(["Mohamed"], "Mohamfd")).not.toBeNull();
  });

  it("supports adjacent transposition", () => {
    expect(damerauLevenshteinDistance("furniture", "furntiure")).toBe(1);
    expect(scoreFuzzySearchRecord(["furniture"], "furntiure")).not.toBeNull();
  });

  it("supports Arabic typo after normalization", () => {
    expect(scoreFuzzySearchRecord(["احمد للتجارة"], "احمد للتجارهه")).not.toBeNull();
  });

  it("requires every multi-word query token to match a field", () => {
    expect(scoreFuzzySearchRecord(["Modern Furniture", "Cairo"], "modren cairo")).not.toBeNull();
    expect(scoreFuzzySearchRecord(["Modern Furniture", "Alexandria"], "modren cairo")).toBeNull();
  });

  it("does not enable fuzzy for numeric-only phone queries", () => {
    expect(isFuzzySearchEligible("01012345678")).toBe(false);
    expect(scoreFuzzySearchRecord(["01012345678"], "01012345679")).toBeNull();
  });

  it("does not fuzzy-match very short queries", () => {
    expect(isFuzzySearchEligible("ab")).toBe(false);
    expect(scoreFuzzySearchRecord(["ac"], "ab")).toBeNull();
  });

  it("rejects distant unrelated words", () => {
    expect(scoreFuzzySearchRecord(["furniture"], "marketing")).toBeNull();
  });
});
