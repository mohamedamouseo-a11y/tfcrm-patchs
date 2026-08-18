from pathlib import Path
import base64, gzip, hashlib

HERE = Path(__file__).resolve().parent
V3 = HERE.parent / "TFCRM-Egypt-Location-WalkIn-Patch-V3"
PARTS = [V3 / f"PATCHER_GZ_B64.part{i:02d}" for i in range(6)]
BASE_SHA256 = "e902faea14b2bf9633e5632c3b399bc3005f35903ff1d094b6a64910b9b218f6"
FINAL_SHA256 = "6217b16339e53df1ca655181e91b7aab1a86384f299842bf5715a6f96c7a0012"
OUT = HERE / "apply_tfcrm_egypt_walkin_patch.py"

missing = [str(p) for p in PARTS if not p.exists()]
if missing:
    raise SystemExit("MISSING_V3_DATA_PARTS: " + ", ".join(missing))

payload = "".join(p.read_text(encoding="utf-8").strip() for p in PARTS)
raw = gzip.decompress(base64.b64decode(payload, validate=True))
base_actual = hashlib.sha256(raw).hexdigest()
if base_actual != BASE_SHA256:
    raise SystemExit(f"BASE_SHA256_MISMATCH: expected={BASE_SHA256} actual={base_actual}")

text = raw.decode("utf-8")

# Fix 1: prevent Python re.sub from interpreting backslashes in generated TS/JS replacement strings.
old_regex = '''def regex_once(text: str, pattern: str, repl, label: str, flags=0, required=True) -> str:\n    result, count = re.subn(pattern, repl, text, count=1, flags=flags)\n'''
new_regex = '''def regex_once(text: str, pattern: str, repl, label: str, flags=0, required=True) -> str:\n    replacement = (lambda _match: repl) if isinstance(repl, str) else repl\n    result, count = re.subn(pattern, replacement, text, count=1, flags=flags)\n'''
if text.count(old_regex) != 1:
    raise SystemExit(f"REGEX_FIX_ANCHOR_MISMATCH: matches={text.count(old_regex)}")
text = text.replace(old_regex, new_regex, 1)

# Fix 2: scope LeadFilters location insertion to the LeadFilters interface only.
old_lead_filters = '''        text = replace_once(text, "  leadQuality?: string;", "  leadQuality?: string;\\n  governorate?: string;\\n  city?: string;\\n  area?: string;\\n  entryMode?: \\"WalkIn\\" | \\"Remote\\";\\n  walkInBranchId?: number;", "LeadFilters location")'''
new_lead_filters = '''        text = regex_once(\n            text,\n            r'(export interface LeadFilters \\{.*?  leadQuality\\?: string;)',\n            lambda m: m.group(1) + '\\n  governorate?: string;\\n  city?: string;\\n  area?: string;\\n  entryMode?: "WalkIn" | "Remote";\\n  walkInBranchId?: number;',\n            "LeadFilters location",\n            flags=re.S,\n        )'''
if text.count(old_lead_filters) != 1:
    raise SystemExit(f"LEAD_FILTERS_FIX_ANCHOR_MISMATCH: matches={text.count(old_lead_filters)}")
text = text.replace(old_lead_filters, new_lead_filters, 1)

patched = text.encode("utf-8")
final_actual = hashlib.sha256(patched).hexdigest()
if final_actual != FINAL_SHA256:
    raise SystemExit(f"FINAL_SHA256_MISMATCH: expected={FINAL_SHA256} actual={final_actual}")

# Syntax-check without writing pyc.
compile(text, str(OUT), "exec")
OUT.write_bytes(patched)
print("PATCHER_READY_V4_1")
print(f"SHA256: {final_actual}")
print(f"PATH: {OUT}")
