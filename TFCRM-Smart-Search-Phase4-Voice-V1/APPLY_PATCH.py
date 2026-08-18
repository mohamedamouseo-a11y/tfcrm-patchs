#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

PATCH_NAME = "TFCRM-Smart-Search-Phase4-Voice-V1"
root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
client_pool = root / "client/src/pages/ClientPool.tsx"
voice_hook_target = root / "client/src/hooks/useSmartSearchVoice.ts"
patch_dir = Path(__file__).resolve().parent

if not client_pool.exists():
    raise SystemExit(f"FAIL: target not found: {client_pool}")

text = client_pool.read_text(encoding="utf-8")
phase3_marker = "SMART_SEARCH_PHASE3_AUTOCOMPLETE_V1"
phase4_marker = "SMART_SEARCH_PHASE4_VOICE_V1"
if phase3_marker not in text:
    raise SystemExit("FAIL: Smart Search Phase 3 marker is missing; apply Phase 3 first")
if phase4_marker in text:
    print("PASS/FAIL: PASS")
    print("PHASE3_PREREQUISITE: PASS")
    print("PATCH_APPLIED: ALREADY_APPLIED")
    print("FILES_CHANGED: NONE")
    print("DB_CHANGED: NO")
    raise SystemExit(0)

backup = client_pool.with_suffix(".tsx.smart-search-phase4-voice.bak")
if not backup.exists():
    shutil.copy2(client_pool, backup)

# Add Mic icons to the existing lucide import.
icon_anchor = "  FileSpreadsheet,\n} from \"lucide-react\";"
icon_replacement = "  FileSpreadsheet,\n  Mic,\n  MicOff,\n} from \"lucide-react\";"
if text.count(icon_anchor) != 1:
    raise SystemExit(f"FAIL: expected lucide icon anchor once, found {text.count(icon_anchor)}")
text = text.replace(icon_anchor, icon_replacement, 1)

# Add voice hook import.
import_anchor = 'import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";\n'
voice_import = 'import { resolveSmartSearchVoiceLanguage, smartSearchVoiceErrorMessage, useSmartSearchVoice } from "@/hooks/useSmartSearchVoice";\n'
if text.count(import_anchor) != 1:
    raise SystemExit(f"FAIL: expected tooltip import anchor once, found {text.count(import_anchor)}")
text = text.replace(import_anchor, import_anchor + voice_import, 1)

# Add hook usage after language setup.
component_anchor = '''export default function ClientPool() {
  const { lang, isRTL } = useLanguage();
  const copy = uiText[lang === "ar" ? "ar" : "en"];
'''
component_replacement = '''export default function ClientPool() {
  const { lang, isRTL } = useLanguage();
  const copy = uiText[lang === "ar" ? "ar" : "en"];
  // SMART_SEARCH_PHASE4_VOICE_V1
  const voiceSearch = useSmartSearchVoice(resolveSmartSearchVoiceLanguage(isRTL));
'''
if text.count(component_anchor) != 1:
    raise SystemExit(f"FAIL: expected ClientPool component anchor once, found {text.count(component_anchor)}")
text = text.replace(component_anchor, component_replacement, 1)

# Sync live transcript into the same search state used by Phase 1/2/3.
state_anchor = "  const [activeSearchSuggestion, setActiveSearchSuggestion] = useState(-1);\n"
state_replacement = state_anchor + '''
  useEffect(() => {
    const voiceText = voiceSearch.transcript.trim();
    if (!voiceText) return;
    setSearch(voiceText);
    setSearchSuggestionsOpen(true);
    setActiveSearchSuggestion(-1);
  }, [voiceSearch.transcript]);

  useEffect(() => {
    if (!voiceSearch.error) return;
    const message = smartSearchVoiceErrorMessage(voiceSearch.error, isRTL);
    if (message) toast.error(message);
  }, [voiceSearch.error, isRTL]);
'''
if text.count(state_anchor) != 1:
    raise SystemExit(f"FAIL: expected autocomplete state anchor once, found {text.count(state_anchor)}")
text = text.replace(state_anchor, state_replacement, 1)

# Locate the Phase 3 smart search input and wrap it with a mic button overlay.
input_marker = 'name="tfcrm-client-pool-smart-search"'
input_pos = text.find(input_marker)
if input_pos < 0:
    raise SystemExit("FAIL: Phase 3 smart search input not found")

# Adjust input padding to leave space for microphone button on the trailing edge.
old_class = '''                className={cn(
                  "h-11 rounded-2xl bg-background",
                  isRTL ? "pr-9" : "pl-9"
                )}'''
new_class = '''                className={cn(
                  "h-11 rounded-2xl bg-background",
                  isRTL ? "pr-9 pl-12" : "pl-9 pr-12"
                )}'''
if text.count(old_class) != 1:
    raise SystemExit(f"FAIL: expected smart search class block once, found {text.count(old_class)}")
text = text.replace(old_class, new_class, 1)

input_end_anchor = '''              />
              {searchSuggestionsOpen && normalizedTypedSearch.length >= 2 && ('''
mic_block = '''              />
              {voiceSearch.isSupported && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      aria-label={voiceSearch.isListening
                        ? (isRTL ? "إيقاف البحث الصوتي" : "Stop voice search")
                        : (isRTL ? "ابدأ البحث الصوتي" : "Start voice search")}
                      onMouseDown={event => event.preventDefault()}
                      onClick={() => {
                        if (voiceSearch.isListening) voiceSearch.stopListening();
                        else voiceSearch.startListening();
                      }}
                      className={cn(
                        "absolute top-1/2 z-20 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border transition-all",
                        isRTL ? "left-2" : "right-2",
                        voiceSearch.isListening
                          ? "border-rose-400 bg-rose-500 text-white shadow-lg shadow-rose-500/30 animate-pulse"
                          : "border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                    >
                      {voiceSearch.isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {voiceSearch.isListening
                      ? (isRTL ? "استماع... اضغط للإيقاف" : "Listening... click to stop")
                      : (isRTL ? "بحث بالصوت" : "Voice search")}
                  </TooltipContent>
                </Tooltip>
              )}
              {voiceSearch.isListening && (
                <div
                  aria-live="polite"
                  className={cn(
                    "absolute top-full z-40 mt-1 flex items-center gap-2 rounded-xl border border-rose-200 bg-background/95 px-3 py-1.5 text-xs text-rose-600 shadow-sm backdrop-blur",
                    isRTL ? "left-0" : "right-0"
                  )}
                >
                  <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
                  <span>{isRTL ? "جاري الاستماع..." : "Listening..."}</span>
                </div>
              )}
              {searchSuggestionsOpen && normalizedTypedSearch.length >= 2 && ('''
if text.count(input_end_anchor) != 1:
    raise SystemExit(f"FAIL: expected smart search input end anchor once, found {text.count(input_end_anchor)}")
text = text.replace(input_end_anchor, mic_block, 1)

voice_hook_target.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(patch_dir / "useSmartSearchVoice.ts", voice_hook_target)
client_pool.write_text(text, encoding="utf-8")

print("PASS/FAIL: PASS")
print("PHASE3_PREREQUISITE: PASS")
print("PATCH_APPLIED: YES")
print(f"PATCH_NAME: {PATCH_NAME}")
print("FILES_CHANGED: client/src/pages/ClientPool.tsx, client/src/hooks/useSmartSearchVoice.ts")
print(f"BACKUP_CREATED: {backup}")
print("VOICE_ENGINE: Browser SpeechRecognition/webkitSpeechRecognition (same STT pattern as Rakan)")
print("VOICE_LANG_AR: ar-SA")
print("VOICE_LANG_EN: en-US")
print("DB_CHANGED: NO")
print("NOTES: Voice transcript feeds the existing search state, so Phase 1 normalization, Phase 2 fuzzy, and Phase 3 autocomplete remain the single search pipeline.")
