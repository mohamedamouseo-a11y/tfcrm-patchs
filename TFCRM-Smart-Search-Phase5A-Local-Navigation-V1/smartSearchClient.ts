const ARABIC_DIACRITICS_RE = /[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g;
const TATWEEL_RE = /\u0640/g;
const MULTI_SPACE_RE = /\s+/g;
const WORD_SPLIT_RE = /[\s,;|/\\()[\]{}:_-]+/g;
const LETTER_RE = /[A-Za-z\u0600-\u06FF]/;

export function normalizeClientSearchText(value: unknown): string {
  return String(value ?? "")
    .normalize("NFKC")
    .replace(ARABIC_DIACRITICS_RE, "")
    .replace(TATWEEL_RE, "")
    .replace(/[أإآٱ]/g, "ا")
    .toLowerCase()
    .trim()
    .replace(MULTI_SPACE_RE, " ");
}

export function tokenizeClientSearch(value: unknown): string[] {
  const normalized = normalizeClientSearchText(value);
  return normalized ? normalized.split(" ").filter(Boolean) : [];
}

function fuzzyDistanceLimit(token: string): number {
  if (token.length <= 2) return 0;
  if (token.length <= 7) return 1;
  return 2;
}

function fuzzyThreshold(token: string): number {
  return token.length <= 4 ? 0.75 : 0.72;
}

export function clientSearchDamerauDistance(a: unknown, b: unknown): number {
  const left = normalizeClientSearchText(a);
  const right = normalizeClientSearchText(b);
  if (left === right) return 0;
  if (!left.length) return right.length;
  if (!right.length) return left.length;

  const rows = left.length + 1;
  const cols = right.length + 1;
  const matrix: number[][] = Array.from({ length: rows }, () => Array(cols).fill(0));
  for (let i = 0; i < rows; i += 1) matrix[i][0] = i;
  for (let j = 0; j < cols; j += 1) matrix[0][j] = j;

  for (let i = 1; i < rows; i += 1) {
    for (let j = 1; j < cols; j += 1) {
      const cost = left[i - 1] === right[j - 1] ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost,
      );
      if (
        i > 1 && j > 1 &&
        left[i - 1] === right[j - 2] &&
        left[i - 2] === right[j - 1]
      ) {
        matrix[i][j] = Math.min(matrix[i][j], matrix[i - 2][j - 2] + 1);
      }
    }
  }
  return matrix[left.length][right.length];
}

function candidateWords(value: unknown): string[] {
  return normalizeClientSearchText(value).split(WORD_SPLIT_RE).map((v) => v.trim()).filter(Boolean);
}

function fuzzyTokenMatches(token: string, candidate: unknown): boolean {
  const normalizedCandidate = normalizeClientSearchText(candidate);
  if (!normalizedCandidate) return false;
  if (normalizedCandidate.includes(token)) return true;

  // Keep numeric-only searches strict. Phone/IDs must never fuzzy-match.
  if (!LETTER_RE.test(token)) return false;
  const maxDistance = fuzzyDistanceLimit(token);
  if (maxDistance <= 0) return false;

  for (const word of candidateWords(normalizedCandidate)) {
    if (Math.abs(word.length - token.length) > maxDistance) continue;
    const distance = clientSearchDamerauDistance(token, word);
    if (distance > maxDistance) continue;
    const similarity = 1 - distance / Math.max(token.length, word.length, 1);
    if (similarity >= fuzzyThreshold(token)) return true;
  }
  return false;
}

export function smartSearchTextMatches(candidate: unknown, query: unknown): boolean {
  const tokens = tokenizeClientSearch(query);
  if (tokens.length === 0) return true;
  const normalizedCandidate = normalizeClientSearchText(candidate);
  if (!normalizedCandidate) return false;

  // P1 exact/normalized/contains always wins. P2 is only a fallback per token.
  return tokens.every((token) => normalizedCandidate.includes(token) || fuzzyTokenMatches(token, normalizedCandidate));
}

export type SmartSearchSuggestion<T> = {
  item: T;
  label: string;
  secondary?: string;
};

export function buildSmartSearchSuggestions<T>(
  items: T[],
  query: unknown,
  getSearchText: (item: T) => unknown,
  getLabel: (item: T) => string,
  getSecondary?: (item: T) => string | undefined,
  limit = 6,
): SmartSearchSuggestion<T>[] {
  const normalizedQuery = normalizeClientSearchText(query);
  if (normalizedQuery.length < 2) return [];
  return items
    .filter((item) => smartSearchTextMatches(getSearchText(item), normalizedQuery))
    .slice(0, Math.max(1, limit))
    .map((item) => ({ item, label: getLabel(item), secondary: getSecondary?.(item) }));
}
