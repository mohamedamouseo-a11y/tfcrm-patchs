import {
  normalizeClientSearchText,
  smartSearchTextMatches,
  tokenizeClientSearch,
} from "./smartSearchClient";

// SMART_SEARCH_PHASE5B2_COLLECTION_V1
export function normalizedCollectionContainsAll(candidate: unknown, query: unknown): boolean {
  const tokens = tokenizeClientSearch(query);
  if (tokens.length === 0) return true;
  const normalizedCandidate = normalizeClientSearchText(candidate);
  if (!normalizedCandidate) return false;
  return tokens.every((token) => normalizedCandidate.includes(token));
}

/**
 * P1 remains authoritative: return normalized contains matches whenever any exist.
 * Only when P1 returns zero rows do we allow the P2 typo-tolerant matcher to run.
 */
export function smartFilterCollection<T>(
  items: T[],
  query: unknown,
  getSearchText: (item: T) => unknown,
): T[] {
  const normalizedQuery = normalizeClientSearchText(query);
  if (!normalizedQuery) return items;

  const exact = items.filter((item) =>
    normalizedCollectionContainsAll(getSearchText(item), normalizedQuery),
  );
  if (exact.length > 0) return exact;

  return items.filter((item) =>
    smartSearchTextMatches(getSearchText(item), normalizedQuery),
  );
}
