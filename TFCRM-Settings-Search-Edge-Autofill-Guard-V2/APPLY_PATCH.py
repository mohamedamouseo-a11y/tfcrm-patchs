#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

PATCH = "TFCRM-Settings-Search-Edge-Autofill-Guard-V2"
root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
target = root / "client/src/pages/AdminSettings.tsx"

if not target.exists():
    raise SystemExit(f"FAIL: target not found: {target}")

text = target.read_text(encoding="utf-8")

if 'data-tfcrm-settings-searchbox="v2"' in text:
    print("PASS/FAIL: PASS")
    print("PATCH_APPLIED: ALREADY_APPLIED")
    print("FILES_CHANGED: NONE")
    print("DB_CHANGED: NO")
    raise SystemExit(0)

import_old = 'import { useState, useEffect } from "react";'
import_new = 'import { useState, useEffect, useRef } from "react";'

state_old = '''  const [settingsSearch, setSettingsSearch] = useState("");
  const [settingsSearchEditable, setSettingsSearchEditable] = useState(false);'''
state_new = '''  const [settingsSearch, setSettingsSearch] = useState("");
  const settingsSearchRef = useRef<HTMLDivElement>(null);'''

input_old = '''              <Input
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

input_new = '''              <div
                ref={settingsSearchRef}
                data-tfcrm-settings-searchbox="v2"
                contentEditable
                suppressContentEditableWarning
                role="searchbox"
                tabIndex={0}
                aria-label={isRTL ? "ابحث داخل الإعدادات" : "Search settings"}
                spellCheck={false}
                onInput={(event) => setSettingsSearch(event.currentTarget.textContent ?? "")}
                onKeyDown={(event) => {
                  if (event.key === "Enter") event.preventDefault();
                }}
                className={cn(
                  "tfcrm-settings-search h-11 rounded-2xl border border-border/70 bg-background text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20 flex items-center whitespace-nowrap overflow-hidden",
                  isRTL ? "pr-10 pl-3" : "pl-10 pr-3"
                )}
              />
              {!settingsSearch && (
                <span
                  aria-hidden="true"
                  className={cn(
                    "pointer-events-none absolute top-1/2 -translate-y-1/2 text-sm text-muted-foreground",
                    isRTL ? "right-10" : "left-10"
                  )}
                >
                  {isRTL ? "ابحث داخل الإعدادات..." : "Search settings..."}
                </span>
              )}'''

sync_anchor = '  const normalizedSettingsSearch = settingsSearch.trim().toLowerCase();\n'
sync_block = '''  useEffect(() => {
    const node = settingsSearchRef.current;
    if (node && node.textContent !== settingsSearch) {
      node.textContent = settingsSearch;
    }
  }, [settingsSearch]);

'''

checks = {
    "react import": text.count(import_old),
    "settings search state": text.count(state_old),
    "guarded input": text.count(input_old),
    "sync anchor": text.count(sync_anchor),
}
for label, count in checks.items():
    if count != 1:
        raise SystemExit(f"FAIL: expected {label} exactly once, found {count}; refusing to guess")

backup = target.with_suffix(target.suffix + ".edge-autofill-guard-v2.bak")
if not backup.exists():
    shutil.copy2(target, backup)

text = text.replace(import_old, import_new, 1)
text = text.replace(state_old, state_new, 1)
text = text.replace(input_old, input_new, 1)
text = text.replace(sync_anchor, sync_block + sync_anchor, 1)
target.write_text(text, encoding="utf-8")

print("PASS/FAIL: PASS")
print("PATCH_APPLIED: YES")
print(f"PATCH_NAME: {PATCH}")
print("FILES_CHANGED: client/src/pages/AdminSettings.tsx")
print(f"BACKUP_CREATED: {backup}")
print("DB_CHANGED: NO")
print("NOTES: Replaced credential-autofillable input with an accessible contentEditable searchbox while preserving the existing settingsSearch state/filter behavior.")
