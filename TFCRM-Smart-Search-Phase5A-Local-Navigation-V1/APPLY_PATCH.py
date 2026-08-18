#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys
import re

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/TFCRM").resolve()
PAYLOAD = Path(__file__).resolve().parent

crm = ROOT / "client/src/components/CRMLayout.tsx"
settings = ROOT / "client/src/pages/AdminSettings.tsx"
shared = ROOT / "client/src/lib/smartSearchClient.ts"
voice = ROOT / "client/src/hooks/useSmartSearchVoice.ts"

for p in (crm, settings, voice):
    if not p.exists():
        raise SystemExit(f"FAIL: required file missing: {p}")

crm_text = crm.read_text(encoding="utf-8")
settings_text = settings.read_text(encoding="utf-8")

if "SMART_SEARCH_PHASE5A_LOCAL_NAVIGATION_V1" in crm_text and "SMART_SEARCH_PHASE5A_LOCAL_NAVIGATION_V1" in settings_text:
    print("PASS/FAIL: PASS")
    print("PATCH_APPLIED: ALREADY_APPLIED")
    print("FILES_CHANGED: NONE")
    print("DB_CHANGED: NO")
    raise SystemExit(0)

if "SMART_SEARCH_PHASE4_VOICE" not in (ROOT / "client/src/pages/ClientPool.tsx").read_text(encoding="utf-8"):
    raise SystemExit("FAIL: Phase 4 prerequisite marker missing from ClientPool")
if 'data-tfcrm-settings-searchbox="v2"' not in settings_text:
    raise SystemExit("FAIL: Settings Edge Autofill Guard V2 marker missing; refusing to replace settings search with credential-autofillable input")

# Shared client-side search core.
shared.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(PAYLOAD / "smartSearchClient.ts", shared)

# Backups.
for p in (crm, settings):
    b = p.with_suffix(p.suffix + ".smart-search-phase5a.bak")
    if not b.exists(): shutil.copy2(p, b)

# ── CRMLayout / NAVIGATION ──────────────────────────────────────────────
if "SMART_SEARCH_PHASE5A_LOCAL_NAVIGATION_V1" not in crm_text:
    import_anchor = 'import { bdApi } from "@/api/bd";\n'
    if import_anchor not in crm_text:
        raise SystemExit("FAIL: CRMLayout import anchor missing")
    crm_text = crm_text.replace(import_anchor, import_anchor + 'import { smartSearchTextMatches } from "@/lib/smartSearchClient";\nimport { resolveSmartSearchVoiceLanguage, smartSearchVoiceErrorMessage, useSmartSearchVoice } from "@/hooks/useSmartSearchVoice";\nimport { Mic, MicOff } from "lucide-react";\n', 1)

    state_anchor = '  const [menuSearch, setMenuSearch] = useState("");\n'
    if state_anchor not in crm_text:
        raise SystemExit("FAIL: CRMLayout menuSearch state anchor missing")
    crm_text = crm_text.replace(state_anchor, state_anchor + '''  // SMART_SEARCH_PHASE5A_LOCAL_NAVIGATION_V1
  const menuVoice = useSmartSearchVoice(resolveSmartSearchVoiceLanguage(isRTL));

  useEffect(() => {
    const text = menuVoice.transcript.trim();
    if (text) setMenuSearch(text);
  }, [menuVoice.transcript]);

  useEffect(() => {
    if (!menuVoice.error) return;
    console.warn(smartSearchVoiceErrorMessage(menuVoice.error, isRTL));
  }, [menuVoice.error, isRTL]);
''', 1)

    old_match = '      const matches = !query || (node.textContent ?? "").toLocaleLowerCase(lang === "ar" ? "ar" : "en").includes(query);\n'
    new_match = '      const matches = !query || smartSearchTextMatches(node.textContent ?? "", menuSearch);\n'
    if old_match not in crm_text:
        raise SystemExit("FAIL: CRMLayout search matching anchor missing")
    crm_text = crm_text.replace(old_match, new_match, 1)

    old_ui = '''          <label className="tfcrm-menu-search">
            <Search size={17} />
            <input value={menuSearch} onChange={(event) => setMenuSearch(event.target.value)} placeholder={isRTL ? "بحث في الإعدادات والقوائم..." : "Search settings and menus..."} />
          </label>'''
    new_ui = '''          <label className="tfcrm-menu-search" role="search">
            <Search size={17} />
            <input
              value={menuSearch}
              onChange={(event) => setMenuSearch(event.target.value)}
              placeholder={isRTL ? "بحث في الإعدادات والقوائم..." : "Search settings and menus..."}
              autoComplete="off"
              role="combobox"
              aria-autocomplete="list"
              aria-label={isRTL ? "بحث ذكي في القوائم" : "Smart menu search"}
            />
            {menuVoice.isSupported && (
              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  menuVoice.isListening ? menuVoice.stopListening() : menuVoice.startListening();
                }}
                aria-label={menuVoice.isListening ? (isRTL ? "إيقاف الاستماع" : "Stop listening") : (isRTL ? "بحث بالصوت" : "Voice search")}
                className={cn("rounded-full p-1.5 transition", menuVoice.isListening && "animate-pulse")}
              >
                {menuVoice.isListening ? <MicOff size={15} /> : <Mic size={15} />}
              </button>
            )}
          </label>'''
    if old_ui not in crm_text:
        raise SystemExit("FAIL: CRMLayout menu search UI anchor missing")
    crm_text = crm_text.replace(old_ui, new_ui, 1)

# ── AdminSettings / SETTINGS ────────────────────────────────────────────
if "SMART_SEARCH_PHASE5A_LOCAL_NAVIGATION_V1" not in settings_text:
    import_anchor = 'import { cn } from "@/lib/utils";\n'
    if import_anchor not in settings_text:
        raise SystemExit("FAIL: AdminSettings import anchor missing")
    settings_text = settings_text.replace(import_anchor, import_anchor + 'import { buildSmartSearchSuggestions, smartSearchTextMatches } from "@/lib/smartSearchClient";\nimport { resolveSmartSearchVoiceLanguage, smartSearchVoiceErrorMessage, useSmartSearchVoice } from "@/hooks/useSmartSearchVoice";\n', 1)

    # Mic/MicOff in existing lucide import.
    lucide_anchor = 'Search } from "lucide-react";'
    if lucide_anchor in settings_text:
        settings_text = settings_text.replace(lucide_anchor, 'Search, Mic, MicOff } from "lucide-react";', 1)
    elif 'MicOff' not in settings_text:
        raise SystemExit("FAIL: AdminSettings lucide Search import anchor missing")

    state_anchor = '  const [settingsSearch, setSettingsSearch] = useState("");\n'
    if state_anchor not in settings_text:
        raise SystemExit("FAIL: AdminSettings settingsSearch state anchor missing")
    settings_text = settings_text.replace(state_anchor, state_anchor + '  const [settingsSuggestionsOpen, setSettingsSuggestionsOpen] = useState(false);\n', 1)

    assistant_anchor = '  const assistantName = !storedAssistantName || storedAssistantName === "فهيم" || storedAssistantName.toLowerCase() === "fahim"\n    ? (isRTL ? "فهيم" : "Fahim")\n    : storedAssistantName;\n'
    if assistant_anchor not in settings_text:
        raise SystemExit("FAIL: AdminSettings assistantName anchor missing")
    settings_text = settings_text.replace(assistant_anchor, assistant_anchor + '''
  // SMART_SEARCH_PHASE5A_LOCAL_NAVIGATION_V1
  const settingsVoice = useSmartSearchVoice(resolveSmartSearchVoiceLanguage(isRTL));
  useEffect(() => {
    const text = settingsVoice.transcript.trim();
    if (text) {
      setSettingsSearch(text);
      setSettingsSuggestionsOpen(true);
    }
  }, [settingsVoice.transcript]);
  useEffect(() => {
    if (!settingsVoice.error) return;
    toast.error(smartSearchVoiceErrorMessage(settingsVoice.error, isRTL));
  }, [settingsVoice.error, isRTL]);
''', 1)

    old_logic = '''  const normalizedSettingsSearch = settingsSearch.trim().toLowerCase();
  const visibleSettingsTabs = settingsTabGroups.flatMap((group) => group.tabs.filter((tab) => tab.visible !== false));'''
    new_logic = '''  const normalizedSettingsSearch = settingsSearch.trim();
  const visibleSettingsTabs = settingsTabGroups.flatMap((group) => group.tabs.filter((tab) => tab.visible !== false));
  const settingsSmartSuggestions = buildSmartSearchSuggestions(
    visibleSettingsTabs,
    normalizedSettingsSearch,
    (tab: any) => `${tab.label ?? ""} ${tab.description ?? ""} ${tab.badge ?? ""}`,
    (tab: any) => String(tab.label ?? ""),
    (tab: any) => String(tab.description ?? ""),
    6,
  );'''
    if old_logic not in settings_text:
        raise SystemExit("FAIL: AdminSettings normalized search anchor missing")
    settings_text = settings_text.replace(old_logic, new_logic, 1)

    old_match = '    return `${group.label} ${group.description} ${tab.label} ${tab.description} ${tab.badge ?? ""}`.toLowerCase().includes(normalizedSettingsSearch);\n'
    new_match = '    return smartSearchTextMatches(`${group.label} ${group.description} ${tab.label} ${tab.description} ${tab.badge ?? ""}`, normalizedSettingsSearch);\n'
    if old_match not in settings_text:
        raise SystemExit("FAIL: AdminSettings tab search matching anchor missing")
    settings_text = settings_text.replace(old_match, new_match, 1)

    # Add voice button and suggestion list after the Autofill Guard V2 searchbox.
    pattern = re.compile(r'(data-tfcrm-settings-searchbox="v2"[\s\S]{0,1400}?\n\s*/>)')
    match = pattern.search(settings_text)
    if not match:
        raise SystemExit("FAIL: AdminSettings V2 searchbox block not found")
    addition = match.group(1) + '''
              {settingsVoice.isSupported && (
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => settingsVoice.isListening ? settingsVoice.stopListening() : settingsVoice.startListening()}
                  className={cn("absolute top-1/2 -translate-y-1/2 rounded-full p-1.5", isRTL ? "left-2" : "right-2", settingsVoice.isListening && "animate-pulse")}
                  aria-label={settingsVoice.isListening ? (isRTL ? "إيقاف الاستماع" : "Stop listening") : (isRTL ? "بحث بالصوت" : "Voice search")}
                >
                  {settingsVoice.isListening ? <MicOff size={15} /> : <Mic size={15} />}
                </button>
              )}
              {settingsSuggestionsOpen && normalizedSettingsSearch.length >= 2 && settingsSmartSuggestions.length > 0 && (
                <div className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-2xl border border-border bg-background shadow-xl">
                  {settingsSmartSuggestions.map((suggestion: any) => (
                    <button
                      key={suggestion.item.value}
                      type="button"
                      className="block w-full px-4 py-2.5 text-start hover:bg-muted/60"
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => {
                        setSettingsSearch(suggestion.label);
                        setSettingsSuggestionsOpen(false);
                      }}
                    >
                      <div className="text-sm font-medium">{suggestion.label}</div>
                      {suggestion.secondary && <div className="text-xs text-muted-foreground">{suggestion.secondary}</div>}
                    </button>
                  ))}
                </div>
              )}'''
    settings_text = settings_text[:match.start()] + addition + settings_text[match.end():]

    # Ensure actual user editing opens suggestions; keep V2 contentEditable architecture.
    settings_text = settings_text.replace(
        'onInput={(event) => setSettingsSearch(event.currentTarget.textContent ?? "")}',
        'onInput={(event) => { setSettingsSearch(event.currentTarget.textContent ?? ""); setSettingsSuggestionsOpen(true); }}',
        1,
    )

crm.write_text(crm_text, encoding="utf-8")
settings.write_text(settings_text, encoding="utf-8")

print("PASS/FAIL: PASS")
print("PATCH_APPLIED: YES")
print("MIGRATED_SEARCH_TYPES: NAVIGATION, SETTINGS")
print("CAPABILITIES: P1_NORMALIZATION,P2_FUZZY,P3_SUGGESTIONS,P4_VOICE")
print("FILES_CHANGED: client/src/components/CRMLayout.tsx; client/src/pages/AdminSettings.tsx; client/src/lib/smartSearchClient.ts")
print("DB_CHANGED: NO")
print("SERVER_CHANGED: NO")
print("NOTES: Phase 5A intentionally excludes server-data searches; those belong to Phase 5B so permissions/pagination/API behavior can be preserved.")
