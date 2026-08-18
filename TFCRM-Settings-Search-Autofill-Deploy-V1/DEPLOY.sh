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

export TFCRM_ROOT="$ROOT"
PM2_IDS="$(pm2 jlist | node -e '
let raw="";
process.stdin.setEncoding("utf8");
process.stdin.on("data", c => raw += c);
process.stdin.on("end", () => {
  const path = require("path");
  let data;
  try { data = JSON.parse(raw); } catch (e) { process.stderr.write(String(e)); process.exit(2); }
  const root = path.resolve(process.env.TFCRM_ROOT || "");
  const ids = data.filter(p => {
    const cwd = p && p.pm2_env && p.pm2_env.pm_cwd;
    return cwd && path.resolve(cwd) === root;
  }).map(p => String(p.pm_id));
  process.stdout.write(ids.join(" "));
});
')"

if [[ -z "${PM2_IDS// }" ]]; then
  echo "PASS/FAIL: FAIL"
  echo "BUILD: PASS"
  echo "TFCRM_RESTART: NOT_RUN"
  echo "REASON: Could not locate a PM2 process whose cwd is exactly $ROOT"
  exit 1
fi

echo "TFCRM_PM2_IDS: $PM2_IDS"
for id in $PM2_IDS; do
  pm2 restart "$id" --update-env
 done

echo "TFCRM_RESTART: PASS"

sleep 2
for id in $PM2_IDS; do
  export TFCRM_PM2_ID="$id"
  status="$(pm2 jlist | node -e '
let raw="";
process.stdin.setEncoding("utf8");
process.stdin.on("data", c => raw += c);
process.stdin.on("end", () => {
  let data;
  try { data = JSON.parse(raw); } catch { process.stdout.write("unknown"); return; }
  const id = String(process.env.TFCRM_PM2_ID || "");
  const proc = data.find(p => String(p.pm_id) === id);
  process.stdout.write(proc && proc.pm2_env ? String(proc.pm2_env.status || "unknown") : "missing");
});
')"
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
