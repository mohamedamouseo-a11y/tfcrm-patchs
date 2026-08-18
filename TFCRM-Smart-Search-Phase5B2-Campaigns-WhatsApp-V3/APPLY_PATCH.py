#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

PATCH = "TFCRM-Smart-Search-Phase5B2-Campaigns-WhatsApp-V3"
MARKER = "SMART_SEARCH_PHASE5B2_CAMPAIGNS_WHATSAPP_V1"
root = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/TFCRM").resolve()
here = Path(__file__).resolve().parent

test_target = root / "server/utils/smartSearchCollection.test.ts"
source_test = here / "server-smartSearchCollection.test.ts"

required_markers = {
    "Meta": root / "client/src/pages/MetaCampaigns.tsx",
    "GoogleAds": root / "client/src/pages/GoogleAdsCampaignsPage.tsx",
    "LinkedIn": root / "client/src/pages/LinkedInCampaignsPage.tsx",
    "Snapchat": root / "client/src/pages/SnapchatCampaignsPage.tsx",
    "TikTok": root / "client/src/pages/TikTokCampaignsPage.tsx",
    "WAInbox": root / "client/src/components/wa/ConversationList.tsx",
    "WAForward": root / "client/src/components/wa/ForwardMessageDialog.tsx",
    "WAServer": root / "server/services/waGatewayIntegrationService.ts",
}

missing = []
for label, path in required_markers.items():
    if not path.exists() or MARKER not in path.read_text(encoding="utf-8", errors="replace"):
        missing.append(label)
if missing:
    raise SystemExit("FAIL: Phase5B2 V2 applied markers missing: " + ", ".join(missing))

if "smartFilterCollection(rows, search" not in required_markers["TikTok"].read_text(encoding="utf-8", errors="replace"):
    raise SystemExit("FAIL: TikTok smart collection search marker missing")

wa = required_markers["WAServer"].read_text(encoding="utf-8", errors="replace")
for needle in [
    "WA_SMART_SEARCH_FUZZY_CANDIDATE_LIMIT = 500",
    "resolveWAGatewayChatConditions",
    "buildMysqlSmartSearchCondition",
]:
    if needle not in wa:
        raise SystemExit(f"FAIL: WhatsApp smart search marker missing: {needle}")

if not source_test.exists():
    raise SystemExit("FAIL: server-compatible collection test source missing")

new_content = source_test.read_text(encoding="utf-8")
old_content = test_target.read_text(encoding="utf-8") if test_target.exists() else None
if old_content != new_content:
    if test_target.exists():
        bak = test_target.with_name(test_target.name + ".phase5b2-v3.bak")
        if not bak.exists():
            shutil.copy2(test_target, bak)
    test_target.write_text(new_content, encoding="utf-8")
    changed = "YES"
else:
    changed = "NO"

print("PASS/FAIL: PASS")
print(f"PATCH_NAME: {PATCH}")
print("PHASE5B2_V2_STATE: VERIFIED")
print("FEATURE_REAPPLIED: NO")
print(f"SERVER_COLLECTION_TEST_WRITTEN: {changed}")
print("TEST_PATH: server/utils/smartSearchCollection.test.ts")
print("DB_CHANGED: NO")
print("SCHEMA_CHANGED: NO")
print("EVOLUTION_CHANGED: NO")
