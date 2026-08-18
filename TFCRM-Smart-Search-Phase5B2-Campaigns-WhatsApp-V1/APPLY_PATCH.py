#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

PATCH = "TFCRM-Smart-Search-Phase5B2-Campaigns-WhatsApp-V1"
MARKER = "SMART_SEARCH_PHASE5B2_CAMPAIGNS_WHATSAPP_V1"
root = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/TFCRM").resolve()
here = Path(__file__).resolve().parent

required = [
    root / "client/src/lib/smartSearchClient.ts",
    root / "client/src/hooks/useSmartSearchVoice.ts",
    root / "server/utils/smartSearch.ts",
    root / "client/src/pages/MetaCampaigns.tsx",
    root / "client/src/pages/GoogleAdsCampaignsPage.tsx",
    root / "client/src/pages/LinkedInCampaignsPage.tsx",
    root / "client/src/pages/SnapchatCampaignsPage.tsx",
    root / "client/src/pages/TikTokCampaignsPage.tsx",
    root / "client/src/pages/wa/WAGatewayInbox.tsx",
    root / "client/src/components/wa/ConversationList.tsx",
    root / "client/src/components/wa/ForwardMessageDialog.tsx",
    root / "server/services/waGatewayIntegrationService.ts",
]
for path in required:
    if not path.exists():
        raise SystemExit(f"FAIL: required file missing: {path}")
if "smartSearchTextMatches" not in (root / "client/src/lib/smartSearchClient.ts").read_text(encoding="utf-8", errors="replace"):
    raise SystemExit("FAIL: Phase 5A client Smart Search core missing")
if "useSmartSearchVoice" not in (root / "client/src/hooks/useSmartSearchVoice.ts").read_text(encoding="utf-8", errors="replace"):
    raise SystemExit("FAIL: Phase 4 voice hook missing")
if "scoreFuzzySearchRecord" not in (root / "server/utils/smartSearch.ts").read_text(encoding="utf-8", errors="replace"):
    raise SystemExit("FAIL: Phase 2 server Smart Search core missing")

changed = []

def backup(path: Path):
    bak = path.with_name(path.name + ".smart-search-phase5b2.bak")
    if not bak.exists(): shutil.copy2(path, bak)

def write(path: Path, content: str):
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == content: return
    if path.exists(): backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    changed.append(str(path.relative_to(root)))

def replace_once(text: str, old: str, new: str, label: str):
    count = text.count(old)
    if count != 1: raise SystemExit(f"FAIL: {label}: expected 1 anchor, found {count}")
    return text.replace(old, new, 1)

# Shared client helpers.
write(root / "client/src/lib/smartSearchCollection.ts", (here / "smartSearchCollection.ts").read_text(encoding="utf-8"))
write(root / "client/src/lib/smartSearchCollection.test.ts", (here / "smartSearchCollection.test.ts").read_text(encoding="utf-8"))
write(root / "client/src/components/SmartSearchField.tsx", (here / "SmartSearchField.tsx").read_text(encoding="utf-8"))

# Campaign page migrations: preserve existing access-gated datasets and all non-search filters.
def campaign_common(path: Path, state_name: str, result_name: str, search_text_expr: str, input_pattern: str, placeholder_expr: str, page_reset: str):
    text = path.read_text(encoding="utf-8")
    if MARKER in text: return
    original = text
    # Import shared smart search pieces.
    anchor = 'import CRMLayout from "@/components/CRMLayout";\n'
    text = replace_once(text, anchor, anchor + 'import { SmartSearchField } from "@/components/SmartSearchField";\nimport { smartFilterCollection } from "@/lib/smartSearchCollection";\n', f"{path.name} imports")
    text = "// " + MARKER + "\n" + text
    # Replace the specific old lowercase search block/line via supplied regex.
    m = re.search(input_pattern, text, re.S)
    if not m: raise SystemExit(f"FAIL: {path.name}: search filter anchor not found")
    replacement = f'''if ({state_name}.trim()) {{\n      {result_name} = smartFilterCollection({result_name}, {state_name}, (row: any) => {search_text_expr});\n    }}'''
    text = text[:m.start()] + replacement + text[m.end():]

    # Replace the visual search wrapper. Supports both compact w-52 and Meta flexible toolbar.
    if path.name == "MetaCampaigns.tsx":
        wrapper = re.compile(r'<div className="relative flex-1 min-w-\[200px\]">\s*<Search[\s\S]*?</div>')
        suggestions = 'filteredCampaigns.slice(0, 6).map((row: any) => ({ id: row.id ?? row.campaignId, label: row.campaignName || String(row.campaignId || ""), secondary: row.objective || row.status }))'
        field = f'''<SmartSearchField\n                  value={{{state_name}}}\n                  onChange={{(value) => {{ setSearchQuery(value); setCurrentPage(1); }}}}\n                  placeholder={{{placeholder_expr}}}\n                  isRTL={{isRTL}}\n                  suggestions={{{suggestions}}}\n                  className="flex-1 min-w-[200px]"\n                />'''
    else:
        wrapper = re.compile(r'<div className="relative w-52">\s*<Search[\s\S]*?<Input[\s\S]*?/>\s*</div>')
        source = "displayed" if path.name == "TikTokCampaignsPage.tsx" else "filtered"
        label = "row.name" if path.name == "TikTokCampaignsPage.tsx" else "row.campaignName"
        secondary = "row.objective || row.status" if path.name != "LinkedInCampaignsPage.tsx" else "row.type || row.status"
        field = f'''<SmartSearchField value={{{state_name}}} onChange={{(value) => {{ {('setSearch(value)' if state_name == 'search' else 'setSearchQuery(value)')}; {page_reset}; }}}} placeholder={{{placeholder_expr}}} isRTL={{isRTL}} suggestions={{{source}.slice(0, 6).map((row: any) => ({{ id: row.id ?? row.campaignId, label: {label} || String(row.campaignId || row.id || ""), secondary: {secondary} }}))}} className="w-52" compact />'''
    text, n = wrapper.subn(field, text, count=1)
    if n != 1: raise SystemExit(f"FAIL: {path.name}: search UI wrapper not found")
    write(path, text)

# Meta: result variable is result, source already filtered from campaigns.
campaign_common(
    root / "client/src/pages/MetaCampaigns.tsx", "searchQuery", "result",
    '`${row.campaignName ?? ""} ${row.campaignId ?? ""} ${row.objective ?? ""}`',
    r'if \(searchQuery\.trim\(\)\) \{\s*const q = searchQuery\.toLowerCase\(\);\s*result = result\.filter\([\s\S]*?\);\s*\}',
    'isRTL ? "بحث باسم الحملة..." : "Search campaigns..."', 'setCurrentPage(1)'
)

# Other platform pages use local `rows` inside their filter memo.
for filename, expr in [
    ("GoogleAdsCampaignsPage.tsx", '`${row.campaignName ?? ""} ${row.campaignId ?? ""} ${row.objective ?? ""}`'),
    ("LinkedInCampaignsPage.tsx", '`${row.campaignName ?? ""} ${row.campaignId ?? ""} ${row.type ?? ""} ${row.objective ?? ""}`'),
    ("SnapchatCampaignsPage.tsx", '`${row.campaignName ?? ""} ${row.campaignId ?? ""} ${row.objective ?? ""}`'),
    ("TikTokCampaignsPage.tsx", '`${row.name ?? ""} ${row.id ?? ""} ${row.objective ?? ""}`'),
]:
    path = root / "client/src/pages" / filename
    # Match each page's single-line lowercase contains filter.
    pattern = r'if \(search\.trim\(\)\) \{[^\n]*?rows = rows\.filter\([\s\S]*?\); \}'
    campaign_common(path, "search", "rows", expr, pattern, 'isRTL ? "بحث..." : "Search..."', 'setPage(1)')

# WhatsApp Inbox search field: server-returned chats are permission-scoped suggestions.
path = root / "client/src/components/wa/ConversationList.tsx"
text = path.read_text(encoding="utf-8")
if MARKER not in text:
    original = text
    text = replace_once(text, 'import { Input } from "@/components/ui/input";\n', 'import { Input } from "@/components/ui/input";\nimport { SmartSearchField } from "@/components/SmartSearchField";\n', "ConversationList import")
    pattern = re.compile(r'<div className="relative">\s*<Search[\s\S]*?<Input value=\{search\}[\s\S]*?/>\s*</div>')
    field = '''<SmartSearchField\n          value={search}\n          onChange={onSearch}\n          placeholder={copy.search}\n          ariaLabel={copy.search}\n          isRTL={locale.toLowerCase().startsWith("ar")}\n          suggestions={chats.slice(0, 6).map((chat) => ({ id: chat.id, label: conversationLabel(chat), secondary: conversationSecondaryLabel(chat) || chat.lastMessagePreview }))}\n        />'''
    text, n = pattern.subn(field, text, count=1)
    if n != 1: raise SystemExit("FAIL: ConversationList search UI anchor not found")
    text = "// " + MARKER + "\n" + text
    write(path, text)

# WhatsApp Forward search reuses same permission-scoped listChatsPage result.
path = root / "client/src/components/wa/ForwardMessageDialog.tsx"
text = path.read_text(encoding="utf-8")
if MARKER not in text:
    text = replace_once(text, 'import { Input } from "@/components/ui/input";\n', 'import { Input } from "@/components/ui/input";\nimport { SmartSearchField } from "@/components/SmartSearchField";\n', "Forward import")
    pattern = re.compile(r'<div className="relative">\s*<Search[\s\S]*?<Input\s*autoFocus[\s\S]*?/>\s*</div>')
    field = '''<SmartSearchField\n            value={search}\n            onChange={setSearch}\n            placeholder={copy.forwardSearch}\n            isRTL={isRTL}\n            suggestions={chats.slice(0, 6).map((chat) => ({ id: chat.id, label: chat.displayName || chat.contactName || chat.pushName || chat.phoneNumber || chat.jid, secondary: chat.phoneNumber || chat.jid }))}\n          />'''
    text, n = pattern.subn(field, text, count=1)
    if n != 1: raise SystemExit("FAIL: ForwardMessageDialog search UI anchor not found")
    text = "// " + MARKER + "\n" + text
    write(path, text)

# WhatsApp server: P1 normalized SQL + exact-first bounded P2 fuzzy fallback while preserving ALL existing access/filter conditions.
path = root / "server/services/waGatewayIntegrationService.ts"
text = path.read_text(encoding="utf-8")
if MARKER not in text:
    original = text
    import_anchor = 'import { createAuditLog, getDb } from "../db";\n'
    text = replace_once(text, import_anchor, import_anchor + 'import { buildMysqlSmartSearchCondition, isFuzzySearchEligible, scoreFuzzySearchRecord } from "../utils/smartSearch";\n', "WA Smart Search import")
    text = replace_once(text,
        'async function buildWAGatewayChatConditions(input: WAGatewayChatListInput) {',
        'async function buildWAGatewayChatConditions(input: WAGatewayChatListInput, options: { includeSearch?: boolean } = {}) {',
        "WA condition signature")
    old_search = '''  if (input.search?.trim()) {\n    const q = `%${escapeLikePattern(input.search.trim().slice(0, 120))}%`;\n    conditions.push(\n      or(\n        like(whatsappChats.displayName, q),\n        like(whatsappChats.phoneNumber, q),\n        like(whatsappChats.jid, q),\n        like(whatsappChats.lastMessagePreview, q),\n        sql`EXISTS (SELECT 1 FROM whatsapp_messages wa_search WHERE wa_search.chat_id = ${whatsappChats.id} AND wa_search.body LIKE ${q})`\n      )\n    );\n  }'''
    new_search = '''  if (options.includeSearch !== false && input.search?.trim()) {\n    const rawSearch = input.search.trim().slice(0, 120);\n    const q = `%${escapeLikePattern(rawSearch)}%`;\n    const normalizedDirect = buildMysqlSmartSearchCondition(\n      [whatsappChats.displayName, whatsappChats.phoneNumber, whatsappChats.jid, whatsappChats.lastMessagePreview],\n      rawSearch,\n    );\n    conditions.push(\n      or(\n        ...(normalizedDirect ? [normalizedDirect as any] : []),\n        sql`EXISTS (SELECT 1 FROM whatsapp_messages wa_search WHERE wa_search.chat_id = ${whatsappChats.id} AND wa_search.body LIKE ${q})`\n      )\n    );\n  }'''
    text = replace_once(text, old_search, new_search, "WA exact search condition")

    resolver_anchor = 'export async function listWAGatewayChats(input: {'
    resolver = '''// SMART_SEARCH_PHASE5B2_CAMPAIGNS_WHATSAPP_V1\nconst WA_SMART_SEARCH_FUZZY_CANDIDATE_LIMIT = 500;\n\nasync function resolveWAGatewayChatConditions(input: WAGatewayChatListInput) {\n  const exact = await buildWAGatewayChatConditions(input);\n  if (exact.noAccess || !input.search?.trim() || !isFuzzySearchEligible(input.search)) return exact;\n  const db = await getDb();\n  if (!db) return exact;\n\n  const exactHit = await db\n    .select({ id: whatsappChats.id })\n    .from(whatsappChats)\n    .innerJoin(whatsappSessions, eq(whatsappSessions.id, whatsappChats.sessionId))\n    .where(and(...exact.conditions))\n    .limit(1);\n  if (exactHit.length > 0) return exact;\n\n  const base = await buildWAGatewayChatConditions(input, { includeSearch: false });\n  if (base.noAccess) return base;\n  const candidates = await db\n    .select({\n      id: whatsappChats.id,\n      displayName: whatsappChats.displayName,\n      phoneNumber: whatsappChats.phoneNumber,\n      jid: whatsappChats.jid,\n      lastMessagePreview: whatsappChats.lastMessagePreview,\n    })\n    .from(whatsappChats)\n    .innerJoin(whatsappSessions, eq(whatsappSessions.id, whatsappChats.sessionId))\n    .where(and(...base.conditions))\n    .orderBy(desc(whatsappChats.lastMessageAt), desc(whatsappChats.id))\n    .limit(WA_SMART_SEARCH_FUZZY_CANDIDATE_LIMIT);\n\n  const ids = candidates\n    .map((row) => ({ row, score: scoreFuzzySearchRecord([row.displayName, row.phoneNumber, row.jid, row.lastMessagePreview], input.search) }))\n    .filter((entry) => entry.score !== null)\n    .sort((a, b) => Number(b.score) - Number(a.score))\n    .map((entry) => Number(entry.row.id));\n\n  return {\n    conditions: [...base.conditions, ids.length ? inArray(whatsappChats.id, ids) : sql`1 = 0`],\n    noAccess: false,\n  };\n}\n\n'''
    idx = text.find(resolver_anchor)
    if idx < 0: raise SystemExit("FAIL: WA list function anchor not found")
    text = text[:idx] + resolver + text[idx:]
    # Both list and paged list now resolve exact-first fuzzy while retaining existing cursor/pagination code.
    text = text.replace('const { conditions, noAccess } = await buildWAGatewayChatConditions(input);', 'const { conditions, noAccess } = await resolveWAGatewayChatConditions(input);', 2)
    text = "// " + MARKER + "\n" + text
    write(path, text)

print("PASS/FAIL: PASS")
print(f"PATCH_NAME: {PATCH}")
print("PATCH_APPLIED: YES")
print("FILES_CHANGED:")
for item in changed: print(f"- {item}")
print("CAMPAIGN_PLATFORMS: Meta, Google Ads, LinkedIn, Snapchat, TikTok")
print("WHATSAPP_SEARCH: normalized exact + bounded fuzzy fallback + suggestions + voice")
print("WA_FUZZY_CANDIDATE_LIMIT: 500")
print("WA_PERMISSION_FILTER_SCOPE: PRESERVED via existing buildWAGatewayChatConditions base conditions")
print("NUMERIC_ONLY_FUZZY: DISABLED by shared Smart Search core")
print("DB_CHANGED: NO")
print("SCHEMA_CHANGED: NO")
print("EVOLUTION_CHANGED: NO")
