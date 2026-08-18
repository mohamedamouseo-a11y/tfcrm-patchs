import { sql } from "drizzle-orm";

const ARABIC_DIACRITICS_RE = /[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g;
const TATWEEL_RE = /\u0640/g;
const MULTI_SPACE_RE = /\s+/g;

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
