#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

PATCH = "TFCRM-Smart-Search-Phase5B2-Campaigns-WhatsApp-V2"
root = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/TFCRM").resolve()
here = Path(__file__).resolve().parent
v1_dir = here.parent / "TFCRM-Smart-Search-Phase5B2-Campaigns-WhatsApp-V1"
v1_apply = v1_dir / "APPLY_PATCH.py"

if not v1_apply.exists():
    raise SystemExit(f"FAIL: V1 patch source missing: {v1_apply}")

# This V2 intentionally reuses the V1 marker so already-applied Google/LinkedIn/Snapchat
# files are skipped and the patch resumes safely from the partial state.
source = v1_apply.read_text(encoding="utf-8")

old_patch_name = 'PATCH = "TFCRM-Smart-Search-Phase5B2-Campaigns-WhatsApp-V1"'
if old_patch_name not in source:
    raise SystemExit("FAIL: V1 patch-name anchor not found")
source = source.replace(old_patch_name, f'PATCH = "{PATCH}"', 1)

old_pattern = "pattern = r'if \\(search\\.trim\\(\\)\\) \\{[^\\n]*?rows = rows\\.filter\\([\\s\\S]*?\\); \\}'"
new_pattern = "pattern = r'if \\(search\\.trim\\(\\)\\) \\{\\s*(?:const q = search\\.toLowerCase\\(\\);\\s*)?rows = rows\\.filter\\([\\s\\S]*?\\);\\s*\\}'"
if source.count(old_pattern) != 1:
    raise SystemExit(f"FAIL: V1 TikTok/campaign regex anchor count={source.count(old_pattern)}")
source = source.replace(old_pattern, new_pattern, 1)

# Add an explicit recovery marker to the generated runner without changing the target-file V1 marker.
needle = 'root = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/TFCRM").resolve()\n'
source = source.replace(needle, needle + 'print("RECOVERY_MODE: PHASE5B2_V2_RESUME_PARTIAL_STATE")\n', 1)

temp_runner = v1_dir / ".APPLY_PATCH_V2_RESUME.py"
temp_runner.write_text(source, encoding="utf-8")
try:
    completed = subprocess.run([sys.executable, str(temp_runner), str(root)])
finally:
    try:
        temp_runner.unlink()
    except FileNotFoundError:
        pass

if completed.returncode != 0:
    raise SystemExit(completed.returncode)

marker = "SMART_SEARCH_PHASE5B2_CAMPAIGNS_WHATSAPP_V1"
checks = {
    "META": root / "client/src/pages/MetaCampaigns.tsx",
    "GOOGLE_ADS": root / "client/src/pages/GoogleAdsCampaignsPage.tsx",
    "LINKEDIN": root / "client/src/pages/LinkedInCampaignsPage.tsx",
    "SNAPCHAT": root / "client/src/pages/SnapchatCampaignsPage.tsx",
    "TIKTOK": root / "client/src/pages/TikTokCampaignsPage.tsx",
    "WHATSAPP_LIST": root / "client/src/components/wa/ConversationList.tsx",
    "WHATSAPP_FORWARD": root / "client/src/components/wa/ForwardMessageDialog.tsx",
    "WHATSAPP_SERVER": root / "server/services/waGatewayIntegrationService.ts",
}

missing = []
for label, path in checks.items():
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if marker not in text:
        missing.append(label)

if missing:
    raise SystemExit("FAIL: recovery verification markers missing: " + ", ".join(missing))

# Specific TikTok verification for the exact failure seen in V1.
tiktok = checks["TIKTOK"].read_text(encoding="utf-8", errors="replace")
if "smartFilterCollection(rows, search" not in tiktok or "<SmartSearchField" not in tiktok:
    raise SystemExit("FAIL: TikTok recovery verification failed")

wa = checks["WHATSAPP_SERVER"].read_text(encoding="utf-8", errors="replace")
for required in [
    "WA_SMART_SEARCH_FUZZY_CANDIDATE_LIMIT = 500",
    "resolveWAGatewayChatConditions",
    "buildMysqlSmartSearchCondition",
]:
    if required not in wa:
        raise SystemExit(f"FAIL: WhatsApp server verification missing: {required}")

print("PASS/FAIL: PASS")
print(f"PATCH_NAME: {PATCH}")
print("RECOVERY_FROM: Phase5B2 V1 partial apply")
print("PARTIAL_STATE_RESET_REQUIRED: NO")
print("TIKTOK_MULTILINE_SEARCH_ANCHOR: FIXED")
print("V1_ALREADY_APPLIED_FILES: SKIPPED_IDEMPOTENTLY")
print("DB_CHANGED: NO")
print("SCHEMA_CHANGED: NO")
print("EVOLUTION_CHANGED: NO")
