#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

PATCH_NAME = "TFCRM-Smart-Search-Phase3-Autocomplete-V1"
root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
client_pool = root / "client/src/pages/ClientPool.tsx"
db = root / "server/db.ts"

if not client_pool.exists():
    raise SystemExit(f"FAIL: target not found: {client_pool}")
if not db.exists():
    raise SystemExit(f"FAIL: Phase 2 prerequisite file not found: {db}")

phase2_text = db.read_text(encoding="utf-8")
if "SMART_SEARCH_PHASE2_FUZZY_CANDIDATE_LIMIT" not in phase2_text:
    raise SystemExit("FAIL: Smart Search Phase 2 marker is missing; apply Phase 2 first")

text = client_pool.read_text(encoding="utf-8")
marker = "SMART_SEARCH_PHASE3_AUTOCOMPLETE_V1"
if marker in text:
    print("PASS/FAIL: PASS")
    print("PHASE2_PREREQUISITE: PASS")
    print("PATCH_APPLIED: ALREADY_APPLIED")
    print("FILES_CHANGED: NONE")
    print("DB_CHANGED: NO")
    raise SystemExit(0)

backup = client_pool.with_suffix(".tsx.smart-search-phase3-autocomplete.bak")
if not backup.exists():
    shutil.copy2(client_pool, backup)

# 1) Add UI state directly after the existing debounced search state.
state_anchor = "  const [debouncedSearch, setDebouncedSearch] = useState(search);\n"
state_insert = state_anchor + "  const [searchSuggestionsOpen, setSearchSuggestionsOpen] = useState(false);\n  const [activeSearchSuggestion, setActiveSearchSuggestion] = useState(-1);\n"
if text.count(state_anchor) != 1:
    raise SystemExit(f"FAIL: expected debounced search state anchor once, found {text.count(state_anchor)}")
text = text.replace(state_anchor, state_insert, 1)

# 2) Track background fetches so autocomplete can show a non-stale loading state.
query_destructure_old = "  const { data, isLoading, refetch } =\n    trpc.accountManagement.listClients.useQuery({"
query_destructure_new = "  const { data, isLoading, isFetching, refetch } =\n    trpc.accountManagement.listClients.useQuery({"
if text.count(query_destructure_old) != 1:
    raise SystemExit(f"FAIL: expected listClients query destructure once, found {text.count(query_destructure_old)}")
text = text.replace(query_destructure_old, query_destructure_new, 1)

# 3) Reuse the exact same permission-aware listClients result as the autocomplete source.
stats_anchor = "  const { data: poolStats } =\n    trpc.accountManagement.getClientPoolStats.useQuery(clientQueryFilters);\n"
suggestions_block = '''  // SMART_SEARCH_PHASE3_AUTOCOMPLETE_V1
  // Reuse the current permission-aware Smart Search result set instead of firing
  // a second search request for every keystroke. This keeps Phase 1/2 behavior,
  // role scope, filters, fuzzy fallback, and pagination source-of-truth aligned.
  const normalizedTypedSearch = search.trim();
  const searchSuggestions =
    searchSuggestionsOpen &&
    normalizedTypedSearch.length >= 2 &&
    debouncedSearch === normalizedTypedSearch
      ? (data?.data ?? []).slice(0, 6).map((client: any) => {
          const label = String(
            client.businessProfile ||
            client.leadName ||
            client.competentPerson ||
            `Client #${client.id}`
          ).trim();
          const secondaryCandidates = [client.leadName, client.group, client.accountManagerName]
            .map((value: unknown) => String(value ?? "").trim())
            .filter((value: string) => value && value !== label);
          return {
            id: Number(client.id),
            label,
            secondary: secondaryCandidates.slice(0, 2).join(" · "),
          };
        })
      : [];

  useEffect(() => {
    setActiveSearchSuggestion(-1);
  }, [debouncedSearch, searchSuggestionsOpen, data?.data?.length]);

  const selectSearchSuggestion = (suggestion: { id: number; label: string }) => {
    setSearch(suggestion.label);
    setDebouncedSearch(suggestion.label);
    setSearchSuggestionsOpen(false);
    setActiveSearchSuggestion(-1);
    setPage(0);
  };

'''
if text.count(stats_anchor) != 1:
    raise SystemExit(f"FAIL: expected Client Pool stats anchor once, found {text.count(stats_anchor)}")
text = text.replace(stats_anchor, suggestions_block + stats_anchor, 1)

# 4) Replace the unique Client Pool search input with combobox behavior + dropdown.
input_pattern = re.compile(
    r'(?P<indent>[ \t]*)<Input\s+placeholder=\{copy\.searchPlaceholder\}[\s\S]*?\n(?P=indent)/>',
    re.MULTILINE,
)
match = input_pattern.search(text)
if not match:
    raise SystemExit("FAIL: Client Pool search input anchor not found")
if len(input_pattern.findall(text)) != 1:
    raise SystemExit("FAIL: Client Pool search input anchor is not unique")

indent = match.group("indent")
replacement = f'''{indent}<Input
{indent}  name="tfcrm-client-pool-smart-search"
{indent}  autoComplete="off"
{indent}  role="combobox"
{indent}  aria-autocomplete="list"
{indent}  aria-expanded={{searchSuggestionsOpen && normalizedTypedSearch.length >= 2}}
{indent}  placeholder={{copy.searchPlaceholder}}
{indent}  value={{search}}
{indent}  onFocus={{() => setSearchSuggestionsOpen(true)}}
{indent}  onBlur={{() => window.setTimeout(() => setSearchSuggestionsOpen(false), 120)}}
{indent}  onChange={{e => {{
{indent}    setSearch(e.target.value);
{indent}    setSearchSuggestionsOpen(true);
{indent}    setActiveSearchSuggestion(-1);
{indent}  }}}}
{indent}  onKeyDown={{e => {{
{indent}    if (e.key === "ArrowDown" && searchSuggestions.length > 0) {{
{indent}      e.preventDefault();
{indent}      setSearchSuggestionsOpen(true);
{indent}      setActiveSearchSuggestion(current => (current + 1) % searchSuggestions.length);
{indent}    }} else if (e.key === "ArrowUp" && searchSuggestions.length > 0) {{
{indent}      e.preventDefault();
{indent}      setSearchSuggestionsOpen(true);
{indent}      setActiveSearchSuggestion(current => current <= 0 ? searchSuggestions.length - 1 : current - 1);
{indent}    }} else if (e.key === "Enter" && activeSearchSuggestion >= 0 && searchSuggestions[activeSearchSuggestion]) {{
{indent}      e.preventDefault();
{indent}      selectSearchSuggestion(searchSuggestions[activeSearchSuggestion]);
{indent}    }} else if (e.key === "Escape") {{
{indent}      setSearchSuggestionsOpen(false);
{indent}      setActiveSearchSuggestion(-1);
{indent}    }}
{indent}  }}}}
{indent}  className={{cn(
{indent}    "h-11 rounded-2xl bg-background",
{indent}    isRTL ? "pr-9" : "pl-9"
{indent}  )}}
{indent}/>
{indent}{{searchSuggestionsOpen && normalizedTypedSearch.length >= 2 && (
{indent}  <div
{indent}    role="listbox"
{indent}    className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-2xl border border-border bg-background shadow-xl"
{indent}  >
{indent}    {{(debouncedSearch !== normalizedTypedSearch || isFetching) ? (
{indent}      <div className="flex items-center gap-2 px-4 py-3 text-sm text-muted-foreground">
{indent}        <Loader2 className="h-4 w-4 animate-spin" />
{indent}        <span>{{isRTL ? "جاري تجهيز الاقتراحات..." : "Loading suggestions..."}}</span>
{indent}      </div>
{indent}    ) : searchSuggestions.length > 0 ? (
{indent}      <div className="py-1">
{indent}        <div className="px-4 py-2 text-xs font-medium text-muted-foreground">
{indent}          {{isRTL ? "اقتراحات البحث" : "Search suggestions"}}
{indent}        </div>
{indent}        {{searchSuggestions.map((suggestion: any, index: number) => (
{indent}          <button
{indent}            key={{suggestion.id}}
{indent}            type="button"
{indent}            role="option"
{indent}            aria-selected={{index === activeSearchSuggestion}}
{indent}            onMouseDown={{event => {{
{indent}              event.preventDefault();
{indent}              selectSearchSuggestion(suggestion);
{indent}            }}}}
{indent}            onMouseEnter={{() => setActiveSearchSuggestion(index)}}
{indent}            className={{cn(
{indent}              "flex w-full items-center gap-3 px-4 py-2.5 text-start transition-colors",
{indent}              index === activeSearchSuggestion ? "bg-muted" : "hover:bg-muted/60"
{indent}            )}}
{indent}          >
{indent}            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-muted">
{indent}              <Building2 className="h-4 w-4" />
{indent}            </div>
{indent}            <div className="min-w-0 flex-1">
{indent}              <div className="truncate text-sm font-medium">{{suggestion.label}}</div>
{indent}              {{suggestion.secondary && (
{indent}                <div className="truncate text-xs text-muted-foreground">{{suggestion.secondary}}</div>
{indent}              )}}
{indent}            </div>
{indent}          </button>
{indent}        ))}}
{indent}      </div>
{indent}    ) : (
{indent}      <div className="px-4 py-3 text-sm text-muted-foreground">
{indent}        {{isRTL ? "لا توجد اقتراحات مطابقة" : "No matching suggestions"}}
{indent}      </div>
{indent}    )}}
{indent}  </div>
{indent})}}'''

text = text[:match.start()] + replacement + text[match.end():]
client_pool.write_text(text, encoding="utf-8")

print("PASS/FAIL: PASS")
print("PHASE2_PREREQUISITE: PASS")
print("PATCH_APPLIED: YES")
print(f"PATCH_NAME: {PATCH_NAME}")
print("FILES_CHANGED: client/src/pages/ClientPool.tsx")
print(f"BACKUP_CREATED: {backup}")
print("SUGGESTION_SOURCE: existing accountManagement.listClients results")
print("SUGGESTION_LIMIT: 6")
print("DB_CHANGED: NO")
print("NOTES: Adds permission-aware autocomplete without adding a second backend search query; supports mouse and ArrowUp/ArrowDown/Enter/Escape keyboard interaction.")
