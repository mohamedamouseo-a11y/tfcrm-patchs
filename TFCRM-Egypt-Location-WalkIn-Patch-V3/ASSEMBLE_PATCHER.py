from pathlib import Path
import base64, gzip, hashlib

HERE = Path(__file__).resolve().parent
PARTS = [HERE / f"PATCHER_GZ_B64.part{i:02d}" for i in range(6)]
BASE_SHA256 = "e902faea14b2bf9633e5632c3b399bc3005f35903ff1d094b6a64910b9b218f6"
FINAL_SHA256 = "362ad7043de89ae8d2fd80c638f276b71d10264e63d99cd5e6cb8ca73883a52c"
OUT = HERE / "apply_tfcrm_egypt_walkin_patch.py"

missing = [p.name for p in PARTS if not p.exists()]
if missing:
    raise SystemExit("MISSING_PARTS: " + ", ".join(missing))

payload = "".join(p.read_text(encoding="utf-8").strip() for p in PARTS)
raw = gzip.decompress(base64.b64decode(payload, validate=True))
base_actual = hashlib.sha256(raw).hexdigest()
if base_actual != BASE_SHA256:
    raise SystemExit(f"BASE_SHA256_MISMATCH: expected={BASE_SHA256} actual={base_actual}")

text = raw.decode("utf-8")
old = '''def regex_once(text: str, pattern: str, repl, label: str, flags=0, required=True) -> str:\n    result, count = re.subn(pattern, repl, text, count=1, flags=flags)\n'''
new = '''def regex_once(text: str, pattern: str, repl, label: str, flags=0, required=True) -> str:\n    # Use a callable for string replacements so backslashes in generated source\n    # (for example JavaScript /\\D/g) are treated literally by Python regex.\n    replacement = (lambda _match: repl) if isinstance(repl, str) else repl\n    result, count = re.subn(pattern, replacement, text, count=1, flags=flags)\n'''
if text.count(old) != 1:
    raise SystemExit(f"REGEX_HOTFIX_ANCHOR_MISMATCH: matches={text.count(old)}")
patched = text.replace(old, new, 1).encode("utf-8")
final_actual = hashlib.sha256(patched).hexdigest()
if final_actual != FINAL_SHA256:
    raise SystemExit(f"FINAL_SHA256_MISMATCH: expected={FINAL_SHA256} actual={final_actual}")

OUT.write_bytes(patched)
print("PATCHER_READY")
print(f"SHA256: {final_actual}")
print(f"PATH: {OUT}")
