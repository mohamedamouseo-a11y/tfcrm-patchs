from pathlib import Path
import base64, gzip, hashlib

HERE = Path(__file__).resolve().parent
V3 = HERE.parent / "TFCRM-Egypt-Location-WalkIn-Patch-V3"
PARTS = [V3 / f"PATCHER_GZ_B64.part{i:02d}" for i in range(6)]
BASE_SHA256 = "e902faea14b2bf9633e5632c3b399bc3005f35903ff1d094b6a64910b9b218f6"
FINAL_SHA256 = "5863a6621c65bd069df0b2bebdf8f402f3088de4a86303c3230f2a30cafab471"
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
old = '''def regex_once(text: str, pattern: str, repl, label: str, flags=0, required=True) -> str:\n    result, count = re.subn(pattern, repl, text, count=1, flags=flags)\n'''
new = '''def regex_once(text: str, pattern: str, repl, label: str, flags=0, required=True) -> str:\n    replacement = (lambda _match: repl) if isinstance(repl, str) else repl\n    result, count = re.subn(pattern, replacement, text, count=1, flags=flags)\n'''

matches = text.count(old)
if matches != 1:
    raise SystemExit(f"REGEX_FIX_ANCHOR_MISMATCH: matches={matches}")
patched = text.replace(old, new, 1).encode("utf-8")
final_actual = hashlib.sha256(patched).hexdigest()
if final_actual != FINAL_SHA256:
    raise SystemExit(f"FINAL_SHA256_MISMATCH: expected={FINAL_SHA256} actual={final_actual}")

OUT.write_bytes(patched)
print("PATCHER_READY_V4")
print(f"SHA256: {final_actual}")
print(f"PATH: {OUT}")
