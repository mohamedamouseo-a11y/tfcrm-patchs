from pathlib import Path
import base64, gzip, hashlib

HERE = Path(__file__).resolve().parent
PARTS = [
    HERE / "PATCHER_GZ_B64.part00",
    HERE / "PATCHER_GZ_B64.part01",
    HERE / "PATCHER_GZ_B64.part02",
    HERE / "PATCHER_GZ_B64.part03",
]
EXPECTED_SHA256 = "413a3087eeb29173bdcc1615aa3af5ea15ffbab65acb8915ac2a0e565adf08df"
OUT = HERE / "apply_tfcrm_egypt_walkin_patch.py"

missing = [p.name for p in PARTS if not p.exists()]
if missing:
    raise SystemExit(f"MISSING_PARTS: {', '.join(missing)}")

payload = "".join(p.read_text(encoding="utf-8").strip() for p in PARTS)
raw = gzip.decompress(base64.b64decode(payload))
sha = hashlib.sha256(raw).hexdigest()
if sha != EXPECTED_SHA256:
    raise SystemExit(f"SHA256_MISMATCH: expected={EXPECTED_SHA256} actual={sha}")
OUT.write_bytes(raw)
print(f"PATCHER_READY: {OUT}")
print(f"SHA256: {sha}")
