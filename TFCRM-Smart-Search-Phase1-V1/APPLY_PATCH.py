#!/usr/bin/env python3
from pathlib import Path
import shutil, sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
db = root / "server/db.ts"
patch_dir = Path(__file__).resolve().parent

if not db.exists():
    raise SystemExit("FAIL: server/db.ts not found")

text = db.read_text(encoding="utf-8")
backup = db.with_suffix(".ts.smart-search-phase1.bak")
if not backup.exists():
    shutil.copy2(db, backup)

import_anchor = '} from "./utils/clientCreateIdempotency";\n'
smart_import = 'import { buildMysqlSmartSearchCondition } from "./utils/smartSearch";\n'
if smart_import not in text:
    if import_anchor not in text:
        raise SystemExit("FAIL: import anchor not found in server/db.ts")
    text = text.replace(import_anchor, import_anchor + smart_import, 1)

old = '''  if (filters.search?.trim()) {
    const q = `%${filters.search.trim()}%`;
    conditions.push(or(
      like(clients.businessProfile, q),
      like(clients.leadName, q),
      like(clients.competentPerson, q),
      like(clients.group, q),
      like(clients.phone, q),
      like(clients.otherPhones, q),
      like(clients.contactPhone, q),
      like(clients.contactEmail, q),
      like(clients.servicesNeeded, q),
      like(clients.marketingObjective, q),
    ));
  }
'''
new = '''  const smartSearch = buildMysqlSmartSearchCondition([
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

if new not in text:
    if old not in text:
        raise SystemExit("FAIL: expected Client Pool search block not found; patch not applied")
    text = text.replace(old, new, 1)

utils = root / "server/utils"
utils.mkdir(parents=True, exist_ok=True)
shutil.copy2(patch_dir / "smartSearch.ts", utils / "smartSearch.ts")
shutil.copy2(patch_dir / "smartSearch.test.ts", utils / "smartSearch.test.ts")

db.write_text(text, encoding="utf-8")
print("SMART_SEARCH_PHASE1_PATCH=APPLIED")
print(f"BACKUP={backup}")
print("FILES=server/db.ts,server/utils/smartSearch.ts,server/utils/smartSearch.test.ts")
