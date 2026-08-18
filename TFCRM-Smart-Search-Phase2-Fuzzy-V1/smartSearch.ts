import { sql } from "drizzle-orm";

const ARABIC_DIACRITICS_RE = /[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g;
const TATWEEL_RE = /\u0640/g;
const MULTI_SPACE_RE = /\s+/g;
const SEARCH_WORD_SPLIT_RE = /[\s,;|/\\()[\]{}:_-]+/g;
const SEARCH_LETTER_RE = /[A-Za-z\u0600-\u06FF]/;

export function normalizeSearchText(value: unknown): string {
  return String(value ?? "")
    .normalize("NFKC")
    .replace(ARABIC_DIACRITICS_RE, "")
    .replace(TATWEEL_RE, "")
    .replace(/[أإآٱ]/g, "ا")
    .toLowerCase()
    .trim()
    .replace(MULTI_SPACE_RE, " ");
}

export function tokenizeSearchQuery(value: unknown): string[] {
  const normalized = normalizeSearchText(value);
  return normalized ? normalized.split(" ").filter(Boolean) : [];
}

export function smartSearchMatches(candidate: unknown, query: unknown): boolean {
  const normalizedCandidate = normalizeSearchText(candidate);
  const tokens = tokenizeSearchQuery(query);
  if (tokens.length === 0) return true;
  return tokens.every((token) => normalizedCandidate.includes(token));
}

export function mysqlNormalizeSearchExpression(column: any) {
  let expression: any = sql`LOWER(TRIM(COALESCE(${column}, '')))`;
  const replacements: Array<[string, string]> = [
    ["أ", "ا"], ["إ", "ا"], ["آ", "ا"], ["ٱ", "ا"], ["ـ", ""],
    ["َ", ""], ["ً", ""], ["ُ", ""], ["ٌ", ""], ["ِ", ""], ["ٍ", ""],
    ["ْ", ""], ["ّ", ""], ["ٰ", ""],
  ];
  for (const [from, to] of replacements) {
    expression = sql`REPLACE(${expression}, ${from}, ${to})`;
  }
  return expression;
}

export function buildMysqlSmartSearchCondition(columns: any[], query: unknown) {
  const tokens = tokenizeSearchQuery(query);
  if (tokens.length === 0 || columns.length === 0) return undefined;
  const perToken = tokens.map((token) => {
    const pattern = `%${token}%`;
    const perColumn = columns.map((column) => sql`${mysqlNormalizeSearchExpression(column)} LIKE ${pattern}`);
    if (perColumn.length === 1) return perColumn[0];
    return sql`(${sql.join(perColumn, sql` OR `)})`;
  });
  if (perToken.length === 1) return perToken[0];
  return sql`(${sql.join(perToken, sql` AND `)})`;
}

export function isFuzzySearchEligible(query: unknown): boolean {
  const normalized = normalizeSearchText(query);
  if (normalized.length < 3) return false;
  return SEARCH_LETTER_RE.test(normalized);
}

function fuzzyDistanceLimit(token: string): number {
  if (token.length <= 2) return 0;
  if (token.length <= 7) return 1;
  return 2;
}

function fuzzySimilarityThreshold(token: string): number {
  return token.length <= 4 ? 0.75 : 0.72;
}

export function damerauLevenshteinDistance(a: unknown, b: unknown): number {
  const left = normalizeSearchText(a);
  const right = normalizeSearchText(b);
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
        i > 1 &&
        j > 1 &&
        left[i - 1] === right[j - 2] &&
        left[i - 2] === right[j - 1]
      ) {
        matrix[i][j] = Math.min(matrix[i][j], matrix[i - 2][j - 2] + 1);
      }
    }
  }

  return matrix[left.length][right.length];
}

function tokenizeCandidateValue(value: unknown): string[] {
  const normalized = normalizeSearchText(value);
  if (!normalized) return [];
  return normalized.split(SEARCH_WORD_SPLIT_RE).map((token) => token.trim()).filter(Boolean);
}

function scoreFuzzyTokenAgainstValue(queryToken: string, rawValue: unknown): number | null {
  const normalizedValue = normalizeSearchText(rawValue);
  if (!normalizedValue) return null;

  if (normalizedValue.includes(queryToken)) return 1;

  const maxDistance = fuzzyDistanceLimit(queryToken);
  if (maxDistance <= 0) return null;

  const threshold = fuzzySimilarityThreshold(queryToken);
  let best: number | null = null;
  for (const candidateToken of tokenizeCandidateValue(normalizedValue)) {
    if (Math.abs(candidateToken.length - queryToken.length) > maxDistance) continue;
    const distance = damerauLevenshteinDistance(queryToken, candidateToken);
    if (distance > maxDistance) continue;
    const similarity = 1 - (distance / Math.max(queryToken.length, candidateToken.length, 1));
    if (similarity < threshold) continue;
    if (best === null || similarity > best) best = similarity;
  }
  return best;
}

export function scoreFuzzySearchRecord(values: unknown[], query: unknown): number | null {
  if (!isFuzzySearchEligible(query)) return null;
  const queryTokens = tokenizeSearchQuery(query);
  if (queryTokens.length === 0) return null;

  const tokenScores: number[] = [];
  for (const queryToken of queryTokens) {
    let best: number | null = null;
    for (const value of values) {
      const score = scoreFuzzyTokenAgainstValue(queryToken, value);
      if (score !== null && (best === null || score > best)) best = score;
      if (best === 1) break;
    }
    if (best === null) return null;
    tokenScores.push(best);
  }

  return tokenScores.reduce((sum, score) => sum + score, 0) / tokenScores.length;
}
