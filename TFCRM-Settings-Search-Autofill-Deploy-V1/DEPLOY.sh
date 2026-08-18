#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/var/www/TFCRM}"
ROOT="$(cd "$ROOT" && pwd -P)"
SOURCE="$ROOT/client/src/pages/AdminSettings.tsx"

if [[ ! -f "$SOURCE" ]]; then
  echo "PASS/FAIL: FAIL"
  echo "REASON: AdminSettings.tsx not found at $SOURCE"
  exit 1
fi

if ! grep -q 'name="tfcrm-settings-filter"' "$SOURCE" || ! grep -q 'readOnly={!settingsSearchEditable}' "$SOURCE"; then
  echo "PASS/FAIL: FAIL"
  echo "REASON: TFCRM-Settings-Search-Autofill-Fix-V1 markers are missing. Refusing to deploy an unknown source state."
  exit 1
fi

echo "SOURCE_FIX: PRESENT"
echo "BUILD: START"
cd "$ROOT"
npm run build
echo "BUILD: PASS"

PM2_IDS="$(pm2 jlist | python3 - "$ROOT" <<'PY'
import json, os, sys
root = os.path.realpath(sys.argv[1])
try:
    data = json.load(sys.stdin)
except Exception as exc:
    print(f"ERROR:{exc}")
    raise SystemExit(2)
ids = []
for proc in data:
    env = proc.get("pm2_env") or {}
    cwd = env.get("pm_cwd")
    if cwd and os.path.realpath(cwd) == root:
        ids.append(str(proc.get("pm_id")))
print(" ".join(ids))
PY
)"

if [[ "$PM2_IDS" == ERROR:* || -z "${PM2_IDS// }" ]]; then
  echo "PASS/FAIL: FAIL"
  echo "BUILD: PASS"
  echo "TFCRM_RESTART: NOT_RUN"
  echo "REASON: Could not uniquely locate any PM2 process whose cwd is exactly $ROOT"
  exit 1
fi

echo "TFCRM_PM2_IDS: $PM2_IDS"
for id in $PM2_IDS; do
  pm2 restart "$id" --update-env
 done

echo "TFCRM_RESTART: PASS"

sleep 2
for id in $PM2_IDS; do
  status="$(pm2 jlist | python3 - "$id" <<'PY'
import json, sys
pid = str(sys.argv[1])
try:
    data = json.load(sys.stdin)
except Exception:
    print("unknown")
    raise SystemExit(0)
for proc in data:
    if str(proc.get("pm_id")) == pid:
        print((proc.get("pm2_env") or {}).get("status", "unknown"))
        break
else:
    print("missing")
PY
)"
  echo "PM2_STATUS[$id]: $status"
  if [[ "$status" != "online" ]]; then
    echo "PASS/FAIL: FAIL"
    echo "REASON: TFCRM PM2 process $id is not online after restart"
    exit 1
  fi
 done

echo "PASS/FAIL: PASS"
echo "SOURCE_FIX: PRESENT"
echo "BUILD: PASS"
echo "TFCRM_RESTART: PASS"
echo "DB_CHANGED: NO"
echo "EVOLUTION_TOUCHED: NO"
echo "WHATSAPP_TOUCHED: NO"
echo "NOTES: Production bundle rebuilt and only PM2 processes rooted at $ROOT were restarted."
