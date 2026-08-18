#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

PATCH = "TFCRM-Smart-Search-Phase5B1-Global-BD-V1"
root = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/TFCRM").resolve()

files = {
    "global": root / "client/src/components/GlobalSearch.tsx",
    "companies_ui": root / "client/src/pages/BD/CompaniesList.tsx",
    "contacts_ui": root / "client/src/pages/BD/ContactsList.tsx",
    "deals_ui": root / "client/src/pages/BD/DealsKanban.tsx",
    "search_route": root / "server/routes/bd/search.ts",
    "companies_route": root / "server/routes/bd/companies.ts",
    "contacts_route": root / "server/routes/bd/contacts.ts",
    "deals_route": root / "server/routes/bd/deals.ts",
    "server_core": root / "server/utils/smartSearch.ts",
    "voice_hook": root / "client/src/hooks/useSmartSearchVoice.ts",
    "client_core": root / "client/src/lib/smartSearchClient.ts",
}

for key, path in files.items():
    if not path.exists():
        raise SystemExit(f"FAIL: required file missing ({key}): {path}")

if "scoreFuzzySearchRecord" not in files["server_core"].read_text(encoding="utf-8", errors="replace"):
    raise SystemExit("FAIL: Phase 2 server Smart Search core missing")
if "useSmartSearchVoice" not in files["voice_hook"].read_text(encoding="utf-8", errors="replace"):
    raise SystemExit("FAIL: Phase 4 voice hook missing")
if "smartSearchTextMatches" not in files["client_core"].read_text(encoding="utf-8", errors="replace"):
    raise SystemExit("FAIL: Phase 5A client Smart Search core missing")

MARKER = "SMART_SEARCH_PHASE5B1_GLOBAL_BD_V1"
if all(MARKER in files[key].read_text(encoding="utf-8", errors="replace") for key in ["global", "companies_ui", "contacts_ui", "deals_ui", "search_route", "companies_route", "contacts_route", "deals_route"]):
    print("PASS/FAIL: PASS")
    print("PATCH_APPLIED: ALREADY_APPLIED")
    print("DB_CHANGED: NO")
    raise SystemExit(0)

changed = []

def backup(path: Path):
    bak = path.with_name(path.name + ".smart-search-phase5b1.bak")
    if not bak.exists():
        shutil.copy2(path, bak)
    return bak


def write_if_changed(path: Path, old: str, new: str):
    if old == new:
        return
    backup(path)
    path.write_text(new, encoding="utf-8")
    changed.append(str(path.relative_to(root)))


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"FAIL: expected {label} exactly once, found {count}")
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Server: Global BD Search
# ---------------------------------------------------------------------------
path = files["search_route"]
old = path.read_text(encoding="utf-8")
if MARKER not in old:
    if 'router.get("/", async' not in old or 'bdDeals' not in old or 'bdCompanies' not in old or 'bdContacts' not in old:
        raise SystemExit("FAIL: unexpected server/routes/bd/search.ts structure")
    new = '''// SMART_SEARCH_PHASE5B1_GLOBAL_BD_V1\nimport { Router } from "express";\nimport type { BdAuthedRequest } from "./index";\nimport { getDb } from "../../db";\nimport { bdDeals, bdCompanies, bdContacts, bdStages } from "../../../drizzle/schema_bd";\nimport { and, eq, isNull } from "drizzle-orm";\nimport { buildMysqlSmartSearchCondition, isFuzzySearchEligible, scoreFuzzySearchRecord } from "../../utils/smartSearch";\n\nconst router = Router();\nconst FUZZY_CANDIDATE_LIMIT = 500;\n\nfunction fuzzyRank<T>(rows: T[], query: string, values: (row: T) => unknown[], limit: number): T[] {\n  return rows\n    .map((row) => ({ row, score: scoreFuzzySearchRecord(values(row), query) }))\n    .filter((entry) => entry.score !== null)\n    .sort((a, b) => Number(b.score) - Number(a.score))\n    .slice(0, limit)\n    .map((entry) => entry.row);\n}\n\nrouter.get("/", async (req: BdAuthedRequest, res) => {\n  try {\n    const q = String(req.query.q || "").trim();\n    if (q.length < 2) return res.json({ deals: [], companies: [], contacts: [] });\n    const db = (await getDb())!;\n    const isLimited = req.bdUser!.bdRole === "bd_rep" || req.bdUser!.bdRole === "bd_viewer";\n    const userId = req.bdUser!.id;\n\n    const dealBase: any[] = [isNull(bdDeals.deletedAt), ...(isLimited ? [eq(bdDeals.ownerId, userId)] : [])];\n    const companyBase: any[] = [isNull(bdCompanies.deletedAt)];\n    const contactBase: any[] = [isNull(bdContacts.deletedAt)];\n\n    const dealExact = buildMysqlSmartSearchCondition([bdDeals.title], q);\n    const companyExact = buildMysqlSmartSearchCondition([bdCompanies.name, (bdCompanies as any).industry], q);\n    const contactExact = buildMysqlSmartSearchCondition([bdContacts.fullName, bdContacts.email], q);\n\n    const dealsQ = db.select({\n      id: bdDeals.id, title: bdDeals.title, dealValue: bdDeals.dealValue, stageId: bdDeals.stageId, stageName: bdStages.name, stageColor: bdStages.color,\n    })\n      .from(bdDeals)\n      .innerJoin(bdStages, eq(bdDeals.stageId, bdStages.id))\n      .where(and(...dealBase, ...(dealExact ? [dealExact as any] : [])))\n      .limit(8);\n\n    const companiesQ = db.select({ id: bdCompanies.id, name: bdCompanies.name, industry: (bdCompanies as any).industry, country: bdCompanies.country })\n      .from(bdCompanies)\n      .where(and(...companyBase, ...(companyExact ? [companyExact as any] : [])))\n      .limit(8);\n\n    const contactsQ = db.select({ id: bdContacts.id, fullName: bdContacts.fullName, email: bdContacts.email, jobTitle: bdContacts.jobTitle, companyId: bdContacts.companyId })\n      .from(bdContacts)\n      .where(and(...contactBase, ...(contactExact ? [contactExact as any] : [])))\n      .limit(8);\n\n    let [deals, companies, contacts] = await Promise.all([dealsQ, companiesQ, contactsQ]);\n\n    if (isFuzzySearchEligible(q)) {\n      const fallbackTasks: Promise<void>[] = [];\n      if (deals.length === 0) {\n        fallbackTasks.push((async () => {\n          const candidates = await db.select({\n            id: bdDeals.id, title: bdDeals.title, dealValue: bdDeals.dealValue, stageId: bdDeals.stageId, stageName: bdStages.name, stageColor: bdStages.color,\n          }).from(bdDeals).innerJoin(bdStages, eq(bdDeals.stageId, bdStages.id)).where(and(...dealBase)).limit(FUZZY_CANDIDATE_LIMIT);\n          deals = fuzzyRank(candidates, q, (row: any) => [row.title], 8);\n        })());\n      }\n      if (companies.length === 0) {\n        fallbackTasks.push((async () => {\n          const candidates = await db.select({ id: bdCompanies.id, name: bdCompanies.name, industry: (bdCompanies as any).industry, country: bdCompanies.country })\n            .from(bdCompanies).where(and(...companyBase)).limit(FUZZY_CANDIDATE_LIMIT);\n          companies = fuzzyRank(candidates, q, (row: any) => [row.name, row.industry], 8);\n        })());\n      }\n      if (contacts.length === 0) {\n        fallbackTasks.push((async () => {\n          const candidates = await db.select({ id: bdContacts.id, fullName: bdContacts.fullName, email: bdContacts.email, jobTitle: bdContacts.jobTitle, companyId: bdContacts.companyId })\n            .from(bdContacts).where(and(...contactBase)).limit(FUZZY_CANDIDATE_LIMIT);\n          contacts = fuzzyRank(candidates, q, (row: any) => [row.fullName, row.email], 8);\n        })());\n      }\n      await Promise.all(fallbackTasks);\n    }\n\n    res.json({ deals, companies, contacts });\n  } catch (err: any) {\n    console.error("[BD smart search]", err);\n    res.status(500).json({ error: "internal_error", message: err?.message });\n  }\n});\n\nexport default router;\n'''
    write_if_changed(path, old, new)

# Shared route block replacer for list endpoints.
def replace_route_get(path: Path, next_anchor: str, new_block: str, label: str):
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    pattern = re.compile(r'router\.get\("/", async \(req: BdAuthedRequest, res\) => \{[\s\S]*?\n\}\);\n\n' + re.escape(next_anchor))
    m = pattern.search(text)
    if not m:
        raise SystemExit(f"FAIL: could not locate GET list block in {label}")
    replacement = new_block.rstrip() + "\n\n" + next_anchor
    updated = text[:m.start()] + replacement + text[m.end():]
    # Add import once immediately after existing imports.
    if 'from "../../utils/smartSearch"' not in updated:
        lines = updated.splitlines()
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("import "):
                insert_at = i + 1
        lines.insert(insert_at, 'import { buildMysqlSmartSearchCondition, isFuzzySearchEligible, scoreFuzzySearchRecord } from "../../utils/smartSearch";')
        updated = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    updated = "// SMART_SEARCH_PHASE5B1_GLOBAL_BD_V1\n" + updated
    write_if_changed(path, text, updated)

companies_block = '''router.get("/", async (req: BdAuthedRequest, res) => {\n  const db = await getDb();\n  const search = String(req.query.search || "").trim();\n  const country = req.query.country as string | undefined;\n  const limit = Math.min(parseInt(req.query.limit as string) || 50, 200);\n  const offset = parseInt(req.query.offset as string) || 0;\n\n  const baseWhere: any[] = [isNull(bdCompanies.deletedAt)];\n  if (country) baseWhere.push(eq(bdCompanies.country, country as any));\n\n  if (!search) {\n    const rows = await db.select().from(bdCompanies).where(and(...baseWhere)).orderBy(desc(bdCompanies.createdAt)).limit(limit).offset(offset);\n    const [{ total }] = await db.select({ total: sql<number>`count(*)` }).from(bdCompanies).where(and(...baseWhere));\n    return res.json({ data: rows, total: Number(total), limit, offset });\n  }\n\n  const exactCondition = buildMysqlSmartSearchCondition([bdCompanies.name, bdCompanies.domain], search);\n  const exactWhere = [...baseWhere, ...(exactCondition ? [exactCondition as any] : [])];\n  const [{ total: exactTotal }] = await db.select({ total: sql<number>`count(*)` }).from(bdCompanies).where(and(...exactWhere));\n  if (Number(exactTotal) > 0 || !isFuzzySearchEligible(search)) {\n    const rows = await db.select().from(bdCompanies).where(and(...exactWhere)).orderBy(desc(bdCompanies.createdAt)).limit(limit).offset(offset);\n    return res.json({ data: rows, total: Number(exactTotal), limit, offset });\n  }\n\n  const candidates = await db.select().from(bdCompanies).where(and(...baseWhere)).orderBy(desc(bdCompanies.createdAt)).limit(1000);\n  const matches = candidates\n    .map((row: any) => ({ row, score: scoreFuzzySearchRecord([row.name, row.domain], search) }))\n    .filter((entry: any) => entry.score !== null)\n    .sort((a: any, b: any) => Number(b.score) - Number(a.score));\n  const rows = matches.slice(offset, offset + limit).map((entry: any) => entry.row);\n  return res.json({ data: rows, total: matches.length, limit, offset, fuzzy: true });\n});'''
replace_route_get(files["companies_route"], 'router.get("/:id"', companies_block, "companies.ts")

contacts_block = '''router.get("/", async (req: BdAuthedRequest, res) => {\n  const db = await getDb();\n  const search = String(req.query.search || "").trim();\n  const companyId = req.query.companyId ? parseInt(req.query.companyId as string) : null;\n  const limit = Math.min(parseInt(req.query.limit as string) || 50, 200);\n  const offset = parseInt(req.query.offset as string) || 0;\n\n  const baseWhere: any[] = [isNull(bdContacts.deletedAt)];\n  if (companyId) baseWhere.push(eq(bdContacts.companyId, companyId));\n\n  if (!search) {\n    const rows = await db.select().from(bdContacts).where(and(...baseWhere)).orderBy(desc(bdContacts.createdAt)).limit(limit).offset(offset);\n    const [{ total }] = await db.select({ total: sql<number>`count(*)` }).from(bdContacts).where(and(...baseWhere));\n    return res.json({ data: rows, total: Number(total), limit, offset });\n  }\n\n  const exactCondition = buildMysqlSmartSearchCondition([bdContacts.fullName, bdContacts.email, bdContacts.phone], search);\n  const exactWhere = [...baseWhere, ...(exactCondition ? [exactCondition as any] : [])];\n  const [{ total: exactTotal }] = await db.select({ total: sql<number>`count(*)` }).from(bdContacts).where(and(...exactWhere));\n  if (Number(exactTotal) > 0 || !isFuzzySearchEligible(search)) {\n    const rows = await db.select().from(bdContacts).where(and(...exactWhere)).orderBy(desc(bdContacts.createdAt)).limit(limit).offset(offset);\n    return res.json({ data: rows, total: Number(exactTotal), limit, offset });\n  }\n\n  const candidates = await db.select().from(bdContacts).where(and(...baseWhere)).orderBy(desc(bdContacts.createdAt)).limit(1000);\n  const matches = candidates\n    .map((row: any) => ({ row, score: scoreFuzzySearchRecord([row.fullName, row.email, row.phone], search) }))\n    .filter((entry: any) => entry.score !== null)\n    .sort((a: any, b: any) => Number(b.score) - Number(a.score));\n  const rows = matches.slice(offset, offset + limit).map((entry: any) => entry.row);\n  return res.json({ data: rows, total: matches.length, limit, offset, fuzzy: true });\n});'''
replace_route_get(files["contacts_route"], 'router.get("/:id"', contacts_block, "contacts.ts")

# Deals list GET has a comment anchor before KANBAN.
path = files["deals_route"]
text = path.read_text(encoding="utf-8")
if MARKER not in text:
    pattern = re.compile(r'// LIST \(with filters\)\nrouter\.get\("/", async \(req: BdAuthedRequest, res\) => \{[\s\S]*?\n\}\);\n\n// KANBAN')
    m = pattern.search(text)
    if not m:
        raise SystemExit("FAIL: could not locate deals list GET block")
    deals_block = '''// LIST (with filters)\nrouter.get("/", async (req: BdAuthedRequest, res) => {\n  const db = await getDb();\n  const search = String(req.query.search || "").trim();\n  const pipelineId = req.query.pipelineId ? parseInt(req.query.pipelineId as string) : null;\n  const stageId = req.query.stageId ? parseInt(req.query.stageId as string) : null;\n  const ownerId = req.query.ownerId ? parseInt(req.query.ownerId as string) : null;\n  const limit = Math.min(parseInt(req.query.limit as string) || 100, 500);\n  const offset = parseInt(req.query.offset as string) || 0;\n\n  const baseWhere: any[] = [isNull(bdDeals.deletedAt)];\n  if (pipelineId) baseWhere.push(eq(bdDeals.pipelineId, pipelineId));\n  if (stageId) baseWhere.push(eq(bdDeals.stageId, stageId));\n  if (ownerId) baseWhere.push(eq(bdDeals.ownerId, ownerId));\n\n  if (!search) {\n    const rows = await db.select().from(bdDeals).where(and(...baseWhere)).orderBy(desc(bdDeals.updatedAt)).limit(limit).offset(offset);\n    const [{ total }] = await db.select({ total: sql<number>`count(*)` }).from(bdDeals).where(and(...baseWhere));\n    return res.json({ data: rows, total: Number(total), limit, offset });\n  }\n\n  const exactCondition = buildMysqlSmartSearchCondition([bdDeals.title], search);\n  const exactWhere = [...baseWhere, ...(exactCondition ? [exactCondition as any] : [])];\n  const [{ total: exactTotal }] = await db.select({ total: sql<number>`count(*)` }).from(bdDeals).where(and(...exactWhere));\n  if (Number(exactTotal) > 0 || !isFuzzySearchEligible(search)) {\n    const rows = await db.select().from(bdDeals).where(and(...exactWhere)).orderBy(desc(bdDeals.updatedAt)).limit(limit).offset(offset);\n    return res.json({ data: rows, total: Number(exactTotal), limit, offset });\n  }\n\n  const candidates = await db.select().from(bdDeals).where(and(...baseWhere)).orderBy(desc(bdDeals.updatedAt)).limit(1000);\n  const matches = candidates\n    .map((row: any) => ({ row, score: scoreFuzzySearchRecord([row.title], search) }))\n    .filter((entry: any) => entry.score !== null)\n    .sort((a: any, b: any) => Number(b.score) - Number(a.score));\n  const rows = matches.slice(offset, offset + limit).map((entry: any) => entry.row);\n  return res.json({ data: rows, total: matches.length, limit, offset, fuzzy: true });\n});\n\n// KANBAN'''
    updated = text[:m.start()] + deals_block + text[m.end():]
    if 'from "../../utils/smartSearch"' not in updated:
        lines = updated.splitlines()
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("import "):
                insert_at = i + 1
        lines.insert(insert_at, 'import { buildMysqlSmartSearchCondition, isFuzzySearchEligible, scoreFuzzySearchRecord } from "../../utils/smartSearch";')
        updated = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    updated = "// SMART_SEARCH_PHASE5B1_GLOBAL_BD_V1\n" + updated
    write_if_changed(path, text, updated)

# ---------------------------------------------------------------------------
# Client: Global Search voice -> same q state. Existing grouped results remain P3.
# ---------------------------------------------------------------------------
path = files["global"]
text = path.read_text(encoding="utf-8")
if MARKER not in text:
    updated = text
    updated = replace_once(updated,
        "import { Search, X, Briefcase, Building2, User } from 'lucide-react';",
        "import { Search, X, Briefcase, Building2, User, Mic, MicOff } from 'lucide-react';",
        "GlobalSearch icons")
    import_anchor = "import { Link } from 'wouter';\n"
    updated = replace_once(updated, import_anchor, import_anchor + "import { useSmartSearchVoice, resolveSmartSearchVoiceLanguage, smartSearchVoiceErrorMessage } from '@/hooks/useSmartSearchVoice';\nimport { toast } from 'sonner';\n", "GlobalSearch imports")
    state_anchor = "  const inputRef = useRef<HTMLInputElement>(null);\n"
    voice_state = '''  const inputRef = useRef<HTMLInputElement>(null);\n  // SMART_SEARCH_PHASE5B1_GLOBAL_BD_V1\n  const globalVoice = useSmartSearchVoice(resolveSmartSearchVoiceLanguage(isRTL));\n\n  useEffect(() => {\n    if (globalVoice.transcript) setQ(globalVoice.transcript);\n  }, [globalVoice.transcript]);\n\n  useEffect(() => {\n    if (globalVoice.error) toast.error(smartSearchVoiceErrorMessage(globalVoice.error, isRTL));\n  }, [globalVoice.error, isRTL]);\n'''
    updated = replace_once(updated, state_anchor, voice_state, "GlobalSearch voice state")
    input_anchor = "          <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder={isRTL ? 'ابحث في الصفقات والشركات وجهات الاتصال...' : 'Search deals, companies, contacts...'} className='flex-1 bg-transparent outline-none text-slate-900 dark:text-white placeholder:text-slate-400' />\n"
    input_new = input_anchor + "          {globalVoice.isSupported && (\n            <button type='button' onClick={() => globalVoice.isListening ? globalVoice.stopListening() : globalVoice.startListening()} className={'relative p-1.5 rounded-lg transition ' + (globalVoice.isListening ? 'bg-rose-100 text-rose-600 dark:bg-rose-950/40' : 'text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800')} title={isRTL ? 'بحث صوتي' : 'Voice search'} aria-label={isRTL ? 'بحث صوتي' : 'Voice search'}>\n              {globalVoice.isListening && <span className='absolute inset-0 rounded-lg animate-ping bg-rose-400/20' />}\n              {globalVoice.isListening ? <MicOff size={17} className='relative' /> : <Mic size={17} />}\n            </button>\n          )}\n"
    updated = replace_once(updated, input_anchor, input_new, "GlobalSearch input")
    write_if_changed(path, text, updated)

# Helper to patch Companies/Contacts list UIs.
def patch_list_ui(path: Path, kind: str):
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    updated = text
    if kind == "companies":
        updated = replace_once(updated,
            "import { ArrowLeft, Plus, Search, Building2, Globe, MapPin, Trash2, ExternalLink } from 'lucide-react';",
            "import { ArrowLeft, Plus, Search, Building2, Globe, MapPin, Trash2, ExternalLink, Mic, MicOff } from 'lucide-react';",
            "Companies icons")
    else:
        updated = replace_once(updated,
            "import { ArrowLeft, Plus, Search, Users, Mail, Phone, Crown, Trash2 } from 'lucide-react';",
            "import { ArrowLeft, Plus, Search, Users, Mail, Phone, Crown, Trash2, Mic, MicOff } from 'lucide-react';",
            "Contacts icons")
    import_anchor = "import { getUrlString, useSyncUrlState } from '@/hooks/useUrlSyncedState';\n"
    updated = replace_once(updated, import_anchor, import_anchor + "import { useSmartSearchVoice, resolveSmartSearchVoiceLanguage, smartSearchVoiceErrorMessage } from '@/hooks/useSmartSearchVoice';\nimport { toast } from 'sonner';\n", f"{kind} imports")
    search_state = "  const [search, setSearch] = useState(() => getUrlString('search', ''));\n"
    state_new = search_state + "  const [searchFocused, setSearchFocused] = useState(false);\n  const searchVoice = useSmartSearchVoice(resolveSmartSearchVoiceLanguage(isRTL));\n"
    updated = replace_once(updated, search_state, state_new, f"{kind} search state")
    sync_anchor = "  useSyncUrlState({ search"
    idx = updated.find(sync_anchor)
    if idx < 0:
        raise SystemExit(f"FAIL: {kind} URL sync anchor missing")
    line_end = updated.find("\n", idx)
    effect_block = "\n\n  // SMART_SEARCH_PHASE5B1_GLOBAL_BD_V1\n  useEffect(() => {\n    if (searchVoice.transcript) setSearch(searchVoice.transcript);\n  }, [searchVoice.transcript]);\n\n  useEffect(() => {\n    if (searchVoice.error) toast.error(smartSearchVoiceErrorMessage(searchVoice.error, isRTL));\n  }, [searchVoice.error, isRTL]);\n"
    updated = updated[:line_end+1] + effect_block + updated[line_end+1:]

    if kind == "companies":
        old_input = "          <input placeholder={t('bdSearchCompanies')} value={search} onChange={e => setSearch(e.target.value)} className={'w-full border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded-lg py-2 text-sm focus:ring-2 focus:ring-emerald-500 outline-none ' + (isRTL ? 'pr-9 pl-3' : 'pl-9 pr-3')} />"
        new_input = """          <input placeholder={t('bdSearchCompanies')} value={search} onFocus={() => setSearchFocused(true)} onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)} onChange={e => setSearch(e.target.value)} className={'w-full border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded-lg py-2 text-sm focus:ring-2 focus:ring-emerald-500 outline-none ' + (isRTL ? 'pr-9 pl-10' : 'pl-9 pr-10')} />\n          {searchVoice.isSupported && <button type='button' onMouseDown={e => e.preventDefault()} onClick={() => searchVoice.isListening ? searchVoice.stopListening() : searchVoice.startListening()} className={'absolute top-1/2 -translate-y-1/2 p-1 rounded ' + (isRTL ? 'left-2' : 'right-2') + (searchVoice.isListening ? ' text-rose-600' : ' text-slate-400')} aria-label={isRTL ? 'بحث صوتي' : 'Voice search'}>{searchVoice.isListening ? <MicOff size={15} className='animate-pulse' /> : <Mic size={15} />}</button>}\n          {searchFocused && search.trim().length >= 2 && !loading && rows.length > 0 && (\n            <div className='absolute left-0 right-0 top-full z-40 mt-1 rounded-xl border border-slate-200 bg-white dark:bg-slate-900 dark:border-slate-700 shadow-xl overflow-hidden'>\n              {rows.slice(0, 6).map((row: any) => <button key={row.id} type='button' onMouseDown={e => { e.preventDefault(); setSearch(row.name || ''); setSearchFocused(false); }} className='block w-full text-start px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800'><span className='font-medium'>{row.name}</span>{row.domain && <span className='text-xs text-slate-400 ms-2'>{row.domain}</span>}</button>)}\n            </div>\n          )}"""
    else:
        old_input = "          <input placeholder={t('bdSearch')} value={search} onChange={e => setSearch(e.target.value)} className={'w-full border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded-lg py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none ' + (isRTL ? 'pr-9 pl-3' : 'pl-9 pr-3')} />"
        new_input = """          <input placeholder={t('bdSearch')} value={search} onFocus={() => setSearchFocused(true)} onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)} onChange={e => setSearch(e.target.value)} className={'w-full border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded-lg py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none ' + (isRTL ? 'pr-9 pl-10' : 'pl-9 pr-10')} />\n          {searchVoice.isSupported && <button type='button' onMouseDown={e => e.preventDefault()} onClick={() => searchVoice.isListening ? searchVoice.stopListening() : searchVoice.startListening()} className={'absolute top-1/2 -translate-y-1/2 p-1 rounded ' + (isRTL ? 'left-2' : 'right-2') + (searchVoice.isListening ? ' text-rose-600' : ' text-slate-400')} aria-label={isRTL ? 'بحث صوتي' : 'Voice search'}>{searchVoice.isListening ? <MicOff size={15} className='animate-pulse' /> : <Mic size={15} />}</button>}\n          {searchFocused && search.trim().length >= 2 && !loading && rows.length > 0 && (\n            <div className='absolute left-0 right-0 top-full z-40 mt-1 rounded-xl border border-slate-200 bg-white dark:bg-slate-900 dark:border-slate-700 shadow-xl overflow-hidden'>\n              {rows.slice(0, 6).map((row: any) => <button key={row.id} type='button' onMouseDown={e => { e.preventDefault(); setSearch(row.fullName || ''); setSearchFocused(false); }} className='block w-full text-start px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800'><span className='font-medium'>{row.fullName}</span>{row.jobTitle && <span className='text-xs text-slate-400 ms-2'>{row.jobTitle}</span>}</button>)}\n            </div>\n          )}"""
    updated = replace_once(updated, old_input, new_input, f"{kind} search input")
    write_if_changed(path, text, updated)

patch_list_ui(files["companies_ui"], "companies")
patch_list_ui(files["contacts_ui"], "contacts")

# Deals Kanban is local collection search: P1/P2 from shared client core, P3 current deals, P4 voice.
path = files["deals_ui"]
text = path.read_text(encoding="utf-8")
if MARKER not in text:
    updated = text
    updated = replace_once(updated,
        "import { Plus, Filter, ArrowLeft, Briefcase, GripVertical, Calendar, Building2, CheckSquare, Square } from 'lucide-react';",
        "import { Plus, Filter, ArrowLeft, Briefcase, GripVertical, Calendar, Building2, CheckSquare, Square, Search, Mic, MicOff } from 'lucide-react';",
        "Deals icons")
    anchor = "import { trpc } from '@/lib/trpc';\n"
    updated = replace_once(updated, anchor, anchor + "import { smartSearchTextMatches, buildSmartSearchSuggestions } from '@/lib/smartSearchClient';\nimport { useSmartSearchVoice, resolveSmartSearchVoiceLanguage, smartSearchVoiceErrorMessage } from '@/hooks/useSmartSearchVoice';\nimport { toast } from 'sonner';\n", "Deals imports")
    state_anchor = "  const [search, setSearch] = useState(() => getUrlString('search', ''));\n"
    updated = replace_once(updated, state_anchor, state_anchor + "  const [searchFocused, setSearchFocused] = useState(false);\n  const searchVoice = useSmartSearchVoice(resolveSmartSearchVoiceLanguage(isRTL));\n", "Deals state")
    url_anchor = "  useSyncUrlState({ pipelineId: pipelineId ?? 0, search }, { pipelineId: 0, search: '' });\n"
    voice_effect = url_anchor + "\n  // SMART_SEARCH_PHASE5B1_GLOBAL_BD_V1\n  useEffect(() => { if (searchVoice.transcript) setSearch(searchVoice.transcript); }, [searchVoice.transcript]);\n  useEffect(() => { if (searchVoice.error) toast.error(smartSearchVoiceErrorMessage(searchVoice.error, isRTL)); }, [searchVoice.error, isRTL]);\n"
    updated = replace_once(updated, url_anchor, voice_effect, "Deals voice effect")
    old_filter = "  const filterDeal = (d: any) => !search || (d.title?.toLowerCase().includes(search.toLowerCase()) || d.companyName?.toLowerCase().includes(search.toLowerCase()));\n"
    new_filter = """  const allDealsForSearch = columns.flatMap((column: any) => column.deals || []);\n  const dealSuggestions = buildSmartSearchSuggestions(allDealsForSearch, search, (d: any) => `${d.title ?? ''} ${d.companyName ?? ''}`, (d: any) => d.title || `Deal #${d.id}`, (d: any) => d.companyName, 6);\n  const filterDeal = (d: any) => smartSearchTextMatches(`${d.title ?? ''} ${d.companyName ?? ''}`, search);\n"""
    updated = replace_once(updated, old_filter, new_filter, "Deals local filter")
    old_input = """        <input\n          type='text'\n          value={search}\n          onChange={e => setSearch(e.target.value)}\n          placeholder={isRTL ? 'بحث في الصفقات...' : 'Search deals...'}\n          className='flex-1 min-w-[200px] border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none'\n        />"""
    new_input = """        <div className='relative flex-1 min-w-[200px]'>\n          <Search size={14} className={'absolute top-1/2 -translate-y-1/2 text-slate-400 ' + (isRTL ? 'right-3' : 'left-3')} />\n          <input\n            type='text'\n            value={search}\n            onFocus={() => setSearchFocused(true)}\n            onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)}\n            onChange={e => setSearch(e.target.value)}\n            placeholder={isRTL ? 'بحث في الصفقات...' : 'Search deals...'}\n            className={'w-full border border-slate-200 dark:border-slate-700 dark:bg-slate-800 rounded-lg py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none ' + (isRTL ? 'pr-9 pl-10' : 'pl-9 pr-10')}\n          />\n          {searchVoice.isSupported && <button type='button' onMouseDown={e => e.preventDefault()} onClick={() => searchVoice.isListening ? searchVoice.stopListening() : searchVoice.startListening()} className={'absolute top-1/2 -translate-y-1/2 p-1 rounded ' + (isRTL ? 'left-2' : 'right-2') + (searchVoice.isListening ? ' text-rose-600' : ' text-slate-400')} aria-label={isRTL ? 'بحث صوتي' : 'Voice search'}>{searchVoice.isListening ? <MicOff size={15} className='animate-pulse' /> : <Mic size={15} />}</button>}\n          {searchFocused && search.trim().length >= 2 && dealSuggestions.length > 0 && (\n            <div className='absolute left-0 right-0 top-full z-40 mt-1 rounded-xl border border-slate-200 bg-white dark:bg-slate-900 dark:border-slate-700 shadow-xl overflow-hidden'>\n              {dealSuggestions.map((suggestion: any) => <button key={suggestion.item.id} type='button' onMouseDown={e => { e.preventDefault(); setSearch(suggestion.label); setSearchFocused(false); }} className='block w-full text-start px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800'><span className='font-medium'>{suggestion.label}</span>{suggestion.secondary && <span className='text-xs text-slate-400 ms-2'>{suggestion.secondary}</span>}</button>)}\n            </div>\n          )}\n        </div>"""
    updated = replace_once(updated, old_input, new_input, "Deals search input")
    write_if_changed(path, text, updated)

print("PASS/FAIL: PASS")
print("PATCH_APPLIED: YES")
print(f"PATCH_NAME: {PATCH}")
print("FILES_CHANGED:")
for item in changed:
    print(f"- {item}")
print("SERVER_SMART_SEARCH: Global BD + companies + contacts + deals")
print("GLOBAL_PERMISSION_SCOPE: PRESERVED (bd_rep/bd_viewer deal owner scope unchanged)")
print("FUZZY_CANDIDATE_LIMIT_GLOBAL: 500")
print("FUZZY_CANDIDATE_LIMIT_LISTS: 1000")
print("NUMERIC_ONLY_FUZZY: DISABLED_BY_SHARED_CORE")
print("DB_CHANGED: NO")
print("SCHEMA_CHANGED: NO")
