from pathlib import Path
import base64, gzip, hashlib
HERE = Path(__file__).resolve().parent
PARTS = [HERE / f"PATCHER_GZ_B64.part{i:02d}" for i in range(6)]
EXPECTED_SHA256 = "e902faea14b2bf9633e5632c3b399bc3005f35903ff1d094b6a64910b9b218f6"
OUT = HERE / "apply_tfcrm_egypt_walkin_patch.py"
missing = [p.name for p in PARTS if not p.exists()]
if missing:
    raise SystemExit("MISSING_PARTS: " + ", ".join(missing))
payload = "".join(p.read_text(encoding="utf-8").strip() for p in PARTS)
raw = gzip.decompress(base64.b64decode(payload, validate=True))
actual = hashlib.sha256(raw).hexdigest()
if actual != EXPECTED_SHA256:
    raise SystemExit(f"SHA256_MISMATCH: expected={EXPECTED_SHA256} actual={actual}")
OUT.write_bytes(raw)
print("PATCHER_READY")
print(f"SHA256: {actual}")
print(f"PATH: {OUT}")
