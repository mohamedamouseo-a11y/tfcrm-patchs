#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
BACKUP = ROOT / ".tfcrm-egp-base-currency-v1-backup"

FILES = {
    "currency": ROOT / "server/lib/currency.ts",
    "sync": ROOT / "server/exchangeRateSync.ts",
    "settings": ROOT / "client/src/components/CurrencySettingsTab.tsx",
    "schema": ROOT / "drizzle/schema.ts",
    "db": ROOT / "server/db.ts",
}

missing = [str(p) for p in FILES.values() if not p.exists()]
if missing:
    raise SystemExit("MISSING_REQUIRED_FILES:\n" + "\n".join(missing))

BACKUP.mkdir(exist_ok=True)


def backup(path: Path):
    dst = BACKUP / path.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 match, found {count}")
    return text.replace(old, new, 1)


# 1) Central base currency logic.
p = FILES["currency"]
backup(p)
text = p.read_text(encoding="utf-8")
text = replace_once(
    text,
    'export const BASE_CURRENCY = "SAR";',
    'export const BASE_CURRENCY = "EGP";',
    "BASE_CURRENCY",
)
p.write_text(text, encoding="utf-8")

# 2) Live FX synchronization should resolve supported foreign currencies into EGP.
p = FILES["sync"]
backup(p)
text = p.read_text(encoding="utf-8")
text = replace_once(text, "// Currency pairs to sync (from -> to SAR)", "// Currency pairs to sync (from -> to EGP)", "sync comment")
text = replace_once(
    text,
    '''const CURRENCY_PAIRS = [\n  { from: "egp", to: "sar" },\n  { from: "usd", to: "sar" },\n];''',
    '''const CURRENCY_PAIRS = [\n  { from: "sar", to: "egp" },\n  { from: "usd", to: "egp" },\n];''',
    "sync pairs",
)
text = replace_once(
    text,
    '''  // Always ensure SAR -> SAR = 1\n  await upsertExchangeRate("SAR", "SAR", "1.00000000");''',
    '''  // Always ensure EGP -> EGP = 1\n  await upsertExchangeRate("EGP", "EGP", "1.00000000");''',
    "base identity rate",
)
p.write_text(text, encoding="utf-8")

# 3) Admin Currency Settings UI.
p = FILES["settings"]
backup(p)
text = p.read_text(encoding="utf-8")
old_pairs = '''  const currencyPairs = [\n    { from: "EGP", to: "SAR", label: "جنيه مصري → ريال سعودي", labelEn: "Egyptian Pound → Saudi Riyal", flag: "🇪🇬" },\n    { from: "USD", to: "SAR", label: "دولار أمريكي → ريال سعودي", labelEn: "US Dollar → Saudi Riyal", flag: "🇺🇸" },\n    { from: "SAR", to: "SAR", label: "ريال سعودي (العملة الأساسية)", labelEn: "Saudi Riyal (Base Currency)", flag: "🇸🇦" },\n  ];'''
new_pairs = '''  const currencyPairs = [\n    { from: "SAR", to: "EGP", label: "ريال سعودي → جنيه مصري", labelEn: "Saudi Riyal → Egyptian Pound", flag: "🇸🇦" },\n    { from: "USD", to: "EGP", label: "دولار أمريكي → جنيه مصري", labelEn: "US Dollar → Egyptian Pound", flag: "🇺🇸" },\n    { from: "EGP", to: "EGP", label: "جنيه مصري (العملة الأساسية)", labelEn: "Egyptian Pound (Base Currency)", flag: "🇪🇬" },\n  ];'''
text = replace_once(text, old_pairs, new_pairs, "currency settings pairs")
text = text.replace(
    "حدد أسعار الصرف لتحويل العملات المختلفة إلى الريال السعودي (العملة الأساسية). يتم استخدام هذه الأسعار لحساب الإيرادات الإجمالية في لوحات التحكم.",
    "حدد أسعار الصرف لتحويل العملات المختلفة إلى الجنيه المصري (العملة الأساسية). يتم استخدام هذه الأسعار لحساب الإيرادات الإجمالية في لوحات التحكم.",
)
text = text.replace(
    "Set exchange rates to convert different currencies to Saudi Riyal (base currency). These rates are used to calculate total revenue in dashboards.",
    "Set exchange rates to convert different currencies to Egyptian Pound (base currency). These rates are used to calculate total revenue in dashboards.",
)
text = text.replace(
    "بعد تغيير أسعار الصرف، اضغط هنا لإعادة حساب قيم كل الصفقات بالعملة الأساسية (الريال السعودي).",
    "بعد تغيير أسعار الصرف، اضغط هنا لإعادة حساب قيم كل الصفقات بالعملة الأساسية (الجنيه المصري).",
)
text = text.replace(
    "After changing exchange rates, click here to recalculate all deal values in the base currency (SAR).",
    "After changing exchange rates, click here to recalculate all deal values in the base currency (EGP).",
)
p.write_text(text, encoding="utf-8")

# 4) Database schema defaults: only currency-field defaults are changed; legacy column names stay intact.
p = FILES["schema"]
backup(p)
text = p.read_text(encoding="utf-8")
text, count_single = re.subn(r"(currency:\s*varchar\(\{\s*length:\s*10\s*\}\)\.default\()'SAR'(\))", r"\1'EGP'\2", text)
text, count_double = re.subn(r'(currency:\s*varchar\(\{\s*length:\s*10\s*\}\)\.default\()"SAR"(\))', r'\1"EGP"\2', text)
if count_single + count_double < 2:
    raise RuntimeError(f"schema currency defaults: expected at least 2 matches, found {count_single + count_double}")
p.write_text(text, encoding="utf-8")

# 5) Runtime/reporting DB code currently uses SAR literals as the base/default currency.
# In server/db.ts those hardcoded SAR tokens represent base-currency assumptions, while actual
# transaction currencies remain data-driven. Keep legacy identifiers such as valueSar unchanged.
p = FILES["db"]
backup(p)
text = p.read_text(encoding="utf-8")
single_count = text.count("'SAR'")
double_count = text.count('"SAR"')
if single_count + double_count == 0:
    raise RuntimeError("server/db.ts: no SAR base literals found; source shape changed")
text = text.replace("'SAR'", "'EGP'").replace('"SAR"', '"EGP"')
text = text.replace("valueBase stores SAR", "valueBase stores EGP")
text = text.replace(" in SAR ", " in EGP ")
text = text.replace("base currency (SAR)", "base currency (EGP)")
p.write_text(text, encoding="utf-8")

print("TFCRM_EGP_BASE_CURRENCY_V1_APPLIED")
print(f"Root: {ROOT}")
print("Base currency: EGP")
print(f"Schema currency defaults changed: {count_single + count_double}")
print(f"server/db.ts SAR base literals changed: {single_count + double_count}")
print(f"Backup: {BACKUP}")
print("Next: run npm run check, then start the app and use Admin Settings > Currency > Sync Rates Now, then Recalculate All Values.")
