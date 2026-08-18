#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

PATCH_NAME = "TFCRM-Settings-Search-Autofill-Fix-V1"
root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
target = root / "client/src/pages/AdminSettings.tsx"

if not target.exists():
    raise SystemExit(f"FAIL: target not found: {target}")

text = target.read_text(encoding="utf-8")

state_old = '  const [settingsSearch, setSettingsSearch] = useState("");\n'
state_new = state_old + '  const [settingsSearchEditable, setSettingsSearchEditable] = useState(false);\n'

input_old = '''              <Input
                value={settingsSearch}
                onChange={(event) => setSettingsSearch(event.target.value)}
                placeholder={isRTL ? "ابحث داخل الإعدادات..." : "Search settings..."}
                className={cn(
                  "tfcrm-settings-search h-11 rounded-2xl border-border/70 bg-background text-sm shadow-sm focus-visible:ring-primary/20",
                  isRTL ? "pr-10" : "pl-10"
                )}
              />'''

input_new = '''              <Input
                type="search"
                name="tfcrm-settings-filter"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                readOnly={!settingsSearchEditable}
                onPointerDown={() => setSettingsSearchEditable(true)}
                onFocus={() => setSettingsSearchEditable(true)}
                value={settingsSearch}
                onChange={(event) => setSettingsSearch(event.target.value)}
                placeholder={isRTL ? "ابحث داخل الإعدادات..." : "Search settings..."}
                className={cn(
                  "tfcrm-settings-search h-11 rounded-2xl border-border/70 bg-background text-sm shadow-sm focus-visible:ring-primary/20",
                  isRTL ? "pr-10" : "pl-10"
                )}
              />'''

state_done = 'const [settingsSearchEditable, setSettingsSearchEditable] = useState(false);' in text
input_done = 'name="tfcrm-settings-filter"' in text and 'readOnly={!settingsSearchEditable}' in text

if state_done and input_done:
    print("PASS/FAIL: PASS")
    print("PATCH_APPLIED: ALREADY_APPLIED")
    print("FILES_CHANGED: NONE")
    print("DB_CHANGED: NO")
    print("NOTES: Settings search autofill guard already exists.")
    raise SystemExit(0)

if state_done != input_done:
    raise SystemExit("FAIL: partial patch state detected; refusing to guess")

if text.count(state_old) != 1:
    raise SystemExit(f"FAIL: expected settingsSearch state anchor exactly once, found {text.count(state_old)}")
if text.count(input_old) != 1:
    raise SystemExit(f"FAIL: expected settings search input anchor exactly once, found {text.count(input_old)}")

backup = target.with_suffix(target.suffix + ".settings-search-autofill-fix.bak")
if not backup.exists():
    shutil.copy2(target, backup)

text = text.replace(state_old, state_new, 1)
text = text.replace(input_old, input_new, 1)
target.write_text(text, encoding="utf-8")

print("PASS/FAIL: PASS")
print("PATCH_APPLIED: YES")
print(f"PATCH_NAME: {PATCH_NAME}")
print("FILES_CHANGED: client/src/pages/AdminSettings.tsx")
print(f"BACKUP_CREATED: {backup}")
print("DB_CHANGED: NO")
print("NOTES: Prevents browser/password-manager credential autofill in Settings search while keeping normal search editable on user interaction.")
