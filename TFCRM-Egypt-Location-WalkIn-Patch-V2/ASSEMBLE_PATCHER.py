#!/usr/bin/env python3
from pathlib import Path
import base64, gzip, hashlib

ROOT = Path(__file__).resolve().parent
PART_NAMES = [
    "PATCHER_GZ_B64.part00",
    "PATCHER_GZ_B64.part01",
    "PATCHER_GZ_B64.part02a",
    "PATCHER_GZ_B64.part02b",
    "PATCHER_GZ_B64.part03",
]
PARTS = [ROOT / name for name in PART_NAMES]
EXPECTED_SHA256 = "413a3087eeb29173bdcc1615aa3af5ea15ffbab65acb8915ac2a0e565adf08df"

missing = [p.name for p in PARTS if not p.exists()]
if missing:
    raise SystemExit(f"Missing patcher part(s): {', '.join(missing)}")

payload = "".join(p.read_text(encoding="utf-8").strip() for p in PARTS)
script = gzip.decompress(base64.b64decode(payload))
actual = hashlib.sha256(script).hexdigest()
if actual != EXPECTED_SHA256:
    raise SystemExit(f"Checksum mismatch: expected {EXPECTED_SHA256}, got {actual}")

target = ROOT / "apply_tfcrm_egypt_walkin_patch.py"
target.write_bytes(script)
target.chmod(0o755)
print(f"PATCHER_READY: {target.name} sha256={actual}")