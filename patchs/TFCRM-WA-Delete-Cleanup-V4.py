#!/usr/bin/env python3
from pathlib import Path
import re
import sys

TARGET = Path("server/services/waGatewayIntegrationService.ts")

if len(sys.argv) != 2 or sys.argv[1] not in {"--check", "--apply"}:
    print("Usage: TFCRM-WA-Delete-Cleanup-V4.py --check|--apply", file=sys.stderr)
    sys.exit(2)

mode = sys.argv[1]
if not TARGET.exists():
    print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
    sys.exit(3)

text = TARGET.read_text(encoding="utf-8")
original = text

required_markers = [
    "_waContactDeleteRunning",
    "_waContactMutationCounts",
    "beginWAGatewayContactMutation",
    "deleteContactsWithLockRetry",
    "contactSyncDeadline",
]
missing = [m for m in required_markers if m not in text]
if missing:
    print("ERROR: expected V1/V2/V3 cleanup markers are missing: " + ", ".join(missing), file=sys.stderr)
    sys.exit(4)

ops = []

def sub_exact(name: str, pattern: str, repl: str, flags: int = 0):
    global text
    text, count = re.subn(pattern, repl, text, count=1, flags=flags)
    ops.append((name, count))

# Remove V2/V3 delete/mutation state helpers, preserving the original sync mutex.
sub_exact(
    "remove delete/mutation helpers",
    r"const _waContactDeleteRunning = new Set<number>\(\);\n"
    r"const _waContactMutationCounts = new Map<number, number>\(\);\n\n"
    r"function beginWAGatewayContactMutation\(sessionId: number\) \{.*?\n"
    r"function hasWAGatewayContactMutation\(sessionId: number\) \{.*?\n\}\n",
    "",
    re.S,
)

# Restore the original contact sync entry/exit behavior.
sub_exact(
    "remove delete guard from contact sync",
    r"  if \(_waContactDeleteRunning\.has\(sessionId\)\) return 0;\n",
    "",
)
sub_exact(
    "remove mutation begin from contact sync",
    r"  if \(!beginWAGatewayContactMutation\(sessionId\)\) return 0;\n",
    "",
)
sub_exact(
    "remove mutation end from contact sync",
    r"    endWAGatewayContactMutation\(sessionId\);\n",
    "",
)

# Remove the V2 delete wrapper.
sub_exact(
    "remove delete-running wrapper start",
    r"  _waContactDeleteRunning\.add\(session\.id\);\n  try \{\n",
    "",
)

# Remove V2/V3 wait-for-contact-mutations block.
sub_exact(
    "remove contact mutation wait",
    r"    const contactSyncDeadline = Date\.now\(\) \+ 15000;\n.*?"
    r"      throw new Error\(\"WhatsApp contact mutation is still running; retry delete shortly\"\);\n",
    "",
    re.S,
)

# Remove V1 retry helper (and the temporary diagnostic logging inside it) and restore the original DELETE.
sub_exact(
    "restore direct whatsapp_contacts delete",
    r"    const deleteContactsWithLockRetry = async \(\) => \{.*?\n"
    r"    \};\n"
    r"    await deleteContactsWithLockRetry\(\);\n",
    "    await db\n"
    "      .delete(whatsappContacts)\n"
    "      .where(eq(whatsappContacts.sessionId, session.id));\n",
    re.S,
)

# Remove V2 finally wrapper at the end of account deletion.
sub_exact(
    "remove delete-running wrapper end",
    r"  return \{ success: true, accountId: String\(session\.id\) \};\n"
    r"  \} finally \{\n"
    r"    _waContactDeleteRunning\.delete\(session\.id\);\n"
    r"  \}\n"
    r"\}",
    "  return { success: true, accountId: String(session.id) };\n}",
)

# Restore the original profile-picture contact update.
sub_exact(
    "restore direct profile picture contact update",
    r"    const contactSessionId = Number\(chat\.sessionId\);\n"
    r"    if \(beginWAGatewayContactMutation\(contactSessionId\)\) \{\n"
    r"      try \{\n"
    r"        await db\.update\(whatsappContacts\).*?\n"
    r"      \} finally \{\n"
    r"        endWAGatewayContactMutation\(contactSessionId\);\n"
    r"      \}\n"
    r"    \}\n",
    "    await db.update(whatsappContacts).set({ profilePictureUrl }).where(and(eq(whatsappContacts.sessionId, Number(chat.sessionId)), eq(whatsappContacts.jid, String(chat.jid)))).catch(() => {});\n",
    re.S,
)

failed = [name for name, count in ops if count != 1]
if failed:
    print("ERROR: cleanup precondition mismatch; no file was written.", file=sys.stderr)
    for name, count in ops:
        print(f"  {name}: matches={count}", file=sys.stderr)
    sys.exit(5)

for marker in [
    "_waContactDeleteRunning",
    "_waContactMutationCounts",
    "beginWAGatewayContactMutation",
    "endWAGatewayContactMutation",
    "hasWAGatewayContactMutation",
    "deleteContactsWithLockRetry",
    "contactSyncDeadline",
    "WA_DELETE_CONTACTS_ERROR",
]:
    if marker in text:
        print(f"ERROR: cleanup marker still present after transform: {marker}", file=sys.stderr)
        sys.exit(6)

if text == original:
    print("ERROR: cleanup produced no changes", file=sys.stderr)
    sys.exit(7)

if mode == "--check":
    print("CHECK_OK: V1/V2/V3 + diagnostic cleanup can be applied safely")
    for name, _ in ops:
        print(f"OK: {name}")
    sys.exit(0)

TARGET.write_text(text, encoding="utf-8")
print("APPLY_OK: cleanup written to server/services/waGatewayIntegrationService.ts")
