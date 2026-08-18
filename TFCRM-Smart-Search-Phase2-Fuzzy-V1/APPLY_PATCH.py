#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

PATCH_NAME = "TFCRM-Smart-Search-Phase2-Fuzzy-V1"
root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
db = root / "server/db.ts"
utils_dir = root / "server/utils"
patch_dir = Path(__file__).resolve().parent

if not db.exists():
    raise SystemExit("FAIL: server/db.ts not found")

text = db.read_text(encoding="utf-8")

phase1_import = 'import { buildMysqlSmartSearchCondition } from "./utils/smartSearch";'
phase2_import = 'import { buildMysqlSmartSearchCondition, isFuzzySearchEligible, scoreFuzzySearchRecord } from "./utils/smartSearch";'
phase1_block = '''  const smartSearch = buildMysqlSmartSearchCondition([
    clients.businessProfile,
    clients.leadName,
    clients.competentPerson,
    clients.group,
    clients.phone,
    clients.otherPhones,
    clients.contactPhone,
    clients.contactEmail,
    clients.servicesNeeded,
    clients.marketingObjective,
  ], filters.search);
  if (smartSearch) conditions.push(smartSearch);
'''
phase2_marker = "SMART_SEARCH_PHASE2_FUZZY_CANDIDATE_LIMIT"

if phase2_marker in text:
    print("PASS/FAIL: PASS")
    print("PATCH_APPLIED: ALREADY_APPLIED")
    print("FILES_CHANGED: NONE")
    print("DB_CHANGED: NO")
    raise SystemExit(0)

if phase1_import not in text or phase1_block not in text:
    raise SystemExit("FAIL: Smart Search Phase 1 markers are missing; apply Phase 1 first")

backup = db.with_suffix(".ts.smart-search-phase2-fuzzy.bak")
if not backup.exists():
    shutil.copy2(db, backup)

text = text.replace(phase1_import, phase2_import, 1)

signature_old = 'function buildClientListConditions(filters: ClientListFilters = {}) {'
signature_new = 'function buildClientListConditions(filters: ClientListFilters = {}, options: { includeSearch?: boolean } = {}) {'
if text.count(signature_old) != 1:
    raise SystemExit(f"FAIL: expected Client Pool condition builder exactly once, found {text.count(signature_old)}")
text = text.replace(signature_old, signature_new, 1)

search_old = phase1_block
search_new = '''  if (options.includeSearch !== false) {
    const smartSearch = buildMysqlSmartSearchCondition([
      clients.businessProfile,
      clients.leadName,
      clients.competentPerson,
      clients.group,
      clients.phone,
      clients.otherPhones,
      clients.contactPhone,
      clients.contactEmail,
      clients.servicesNeeded,
      clients.marketingObjective,
    ], filters.search);
    if (smartSearch) conditions.push(smartSearch);
  }
'''
text = text.replace(search_old, search_new, 1)

where_anchor = '''function buildClientWhere(conditions: any[], extra: any[] = []) {
  const allConditions = [...conditions, ...extra].filter(Boolean);
  return allConditions.length > 0 ? and(...allConditions) : undefined;
}
'''
helper_block = '''function buildClientWhere(conditions: any[], extra: any[] = []) {
  const allConditions = [...conditions, ...extra].filter(Boolean);
  return allConditions.length > 0 ? and(...allConditions) : undefined;
}

const SMART_SEARCH_PHASE2_FUZZY_CANDIDATE_LIMIT = 1000;

async function resolveClientSearchConditions(db: any, filters: ClientListFilters = {}) {
  const exactConditions = buildClientListConditions(filters);
  const query = filters.search?.trim();
  if (!query || !isFuzzySearchEligible(query)) {
    return { conditions: exactConditions, mode: "exact" as const, fuzzyIds: [] as number[] };
  }

  const exactCountRows = await db
    .select({ count: count() })
    .from(clients)
    .where(buildClientWhere(exactConditions));
  if (Number(exactCountRows[0]?.count ?? 0) > 0) {
    return { conditions: exactConditions, mode: "exact" as const, fuzzyIds: [] as number[] };
  }

  const baseConditions = buildClientListConditions(filters, { includeSearch: false });
  const candidates = await db
    .select({
      id: clients.id,
      businessProfile: clients.businessProfile,
      leadName: clients.leadName,
      competentPerson: clients.competentPerson,
      group: clients.group,
      phone: clients.phone,
      otherPhones: clients.otherPhones,
      contactPhone: clients.contactPhone,
      contactEmail: clients.contactEmail,
      servicesNeeded: clients.servicesNeeded,
      marketingObjective: clients.marketingObjective,
      createdAt: clients.createdAt,
    })
    .from(clients)
    .where(buildClientWhere(baseConditions))
    .orderBy(desc(clients.createdAt))
    .limit(SMART_SEARCH_PHASE2_FUZZY_CANDIDATE_LIMIT);

  const fuzzyIds = candidates
    .map((candidate: any) => ({
      id: Number(candidate.id),
      score: scoreFuzzySearchRecord([
        candidate.businessProfile,
        candidate.leadName,
        candidate.competentPerson,
        candidate.group,
        candidate.phone,
        candidate.otherPhones,
        candidate.contactPhone,
        candidate.contactEmail,
        candidate.servicesNeeded,
        candidate.marketingObjective,
      ], query),
    }))
    .filter((item: any) => item.score !== null)
    .sort((a: any, b: any) => Number(b.score) - Number(a.score))
    .map((item: any) => item.id);

  const conditions = [...baseConditions];
  conditions.push(fuzzyIds.length > 0 ? inArray(clients.id, fuzzyIds) : sql`1 = 0`);
  return { conditions, mode: "fuzzy" as const, fuzzyIds };
}
'''
if text.count(where_anchor) != 1:
    raise SystemExit(f"FAIL: expected buildClientWhere anchor once, found {text.count(where_anchor)}")
text = text.replace(where_anchor, helper_block, 1)

stats_old = '''  const conditions = buildClientListConditions(filters);
  const whereClause = buildClientWhere(conditions);
  const [totalResult, activeResult, awaitingResult, expiringResult, syncedResult] = await Promise.all([
'''
stats_new = '''  const resolvedSearch = await resolveClientSearchConditions(db, filters);
  const conditions = resolvedSearch.conditions;
  const whereClause = buildClientWhere(conditions);
  const [totalResult, activeResult, awaitingResult, expiringResult, syncedResult] = await Promise.all([
'''
if text.count(stats_old) != 1:
    raise SystemExit(f"FAIL: expected stats query anchor once, found {text.count(stats_old)}")
text = text.replace(stats_old, stats_new, 1)

clients_old = '''  const conditions = buildClientListConditions(filters);
  const whereClause = buildClientWhere(conditions);

  const [data, countResult] = await Promise.all([
'''
clients_new = '''  const resolvedSearch = await resolveClientSearchConditions(db, filters);
  const conditions = resolvedSearch.conditions;
  const whereClause = buildClientWhere(conditions);

  const [data, countResult] = await Promise.all([
'''
if text.count(clients_old) != 1:
    raise SystemExit(f"FAIL: expected getClients query anchor once, found {text.count(clients_old)}")
text = text.replace(clients_old, clients_new, 1)

utils_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(patch_dir / "smartSearch.ts", utils_dir / "smartSearch.ts")
shutil.copy2(patch_dir / "smartSearch.test.ts", utils_dir / "smartSearch.test.ts")
db.write_text(text, encoding="utf-8")

print("PASS/FAIL: PASS")
print("PATCH_APPLIED: YES")
print(f"PATCH_NAME: {PATCH_NAME}")
print("FILES_CHANGED: server/db.ts, server/utils/smartSearch.ts, server/utils/smartSearch.test.ts")
print(f"BACKUP_CREATED: {backup}")
print("FUZZY_CANDIDATE_LIMIT: 1000")
print("DB_CHANGED: NO")
print("NOTES: Exact Phase 1 search remains first; fuzzy fallback activates only after exact search returns zero matches and preserves existing authorization/filter conditions.")
