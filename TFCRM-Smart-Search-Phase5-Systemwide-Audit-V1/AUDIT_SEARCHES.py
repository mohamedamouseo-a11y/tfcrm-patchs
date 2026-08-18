#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys
from collections import defaultdict

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/TFCRM").resolve()
CLIENT = ROOT / "client" / "src"
SERVER = ROOT / "server"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/TFCRM_SMART_SEARCH_SYSTEMWIDE_AUDIT.md")

if not CLIENT.exists():
    raise SystemExit(f"FAIL: client/src not found under {ROOT}")

SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx"}
SKIP_PARTS = {"node_modules", "dist", "build", ".git"}

ui_patterns = [
    ("TYPE_SEARCH", re.compile(r'type\s*=\s*["\']search["\']', re.I)),
    ("SEARCH_ROLE", re.compile(r'role\s*=\s*["\'](?:search|searchbox|combobox)["\']', re.I)),
    ("SEARCH_PLACEHOLDER_EN", re.compile(r'placeholder[^\n]{0,180}(?:search|find|lookup)', re.I)),
    ("SEARCH_PLACEHOLDER_AR", re.compile(r'placeholder[^\n]{0,180}(?:ابحث|بحث|اعثر)', re.I)),
    ("SEARCH_STATE", re.compile(r'\b(?:search|searchTerm|searchQuery|searchText|menuSearch|settingsSearch|filterText|query)\b', re.I)),
    ("COMMAND_SEARCH", re.compile(r'<(?:CommandInput|SearchInput|GlobalSearch|SmartSearch)', re.I)),
]

backend_patterns = [
    ("BACKEND_SEARCH_INPUT", re.compile(r'\bsearch\s*:\s*z\.', re.I)),
    ("BACKEND_FILTER_SEARCH", re.compile(r'filters?\.search|input\.search', re.I)),
    ("BACKEND_LIKE_SEARCH", re.compile(r'\b(?:like|ilike)\s*\(', re.I)),
    ("SMART_SEARCH_CORE", re.compile(r'buildMysqlSmartSearchCondition|normalizeSearchText|scoreFuzzySearchRecord', re.I)),
]


def iter_sources(base: Path):
    if not base.exists():
        return
    for path in base.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")):
            continue
        yield path


def compact(line: str, width: int = 220) -> str:
    value = re.sub(r"\s+", " ", line.strip())
    return value[:width] + ("…" if len(value) > width else "")


def current_phase(text: str) -> str:
    phases = []
    if "SMART_SEARCH_PHASE1" in text or "normalizeSearchText" in text:
        phases.append("P1")
    if "SMART_SEARCH_PHASE2" in text or "scoreFuzzySearchRecord" in text:
        phases.append("P2")
    if "SMART_SEARCH_PHASE3_AUTOCOMPLETE" in text:
        phases.append("P3")
    if "SMART_SEARCH_PHASE4_VOICE" in text or "useSmartSearchVoice" in text:
        phases.append("P4")
    if 'data-tfcrm-settings-searchbox="v2"' in text:
        phases.append("SETTINGS_AUTOFILL_V2")
    return ",".join(phases) if phases else "NONE"


ui_hits = defaultdict(list)
ui_file_meta = {}
for path in iter_sources(CLIENT):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    phase = current_phase(text)
    rel = str(path.relative_to(ROOT))
    lines = text.splitlines()
    seen = set()
    for idx, line in enumerate(lines, 1):
        matched = [name for name, pattern in ui_patterns if pattern.search(line)]
        if not matched:
            continue
        # Require a stronger signal than a generic variable name alone.
        strong = any(name != "SEARCH_STATE" for name in matched)
        local_context = " ".join(lines[max(0, idx-3):min(len(lines), idx+2)])
        if not strong and not re.search(r'<Input|<input|CommandInput|placeholder|onChange|useState|useQuery|filter\(', local_context, re.I):
            continue
        key = (idx, tuple(matched))
        if key in seen:
            continue
        seen.add(key)
        ui_hits[rel].append((idx, ",".join(matched), compact(line)))
    if rel in ui_hits:
        ui_file_meta[rel] = phase

backend_hits = defaultdict(list)
for path in iter_sources(SERVER):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    rel = str(path.relative_to(ROOT))
    for idx, line in enumerate(text.splitlines(), 1):
        matched = [name for name, pattern in backend_patterns if pattern.search(line)]
        if matched:
            backend_hits[rel].append((idx, ",".join(matched), compact(line)))

# Reduce noisy UI entries to distinct files, while preserving every detected line in report.
all_ui_files = sorted(ui_hits)
phase4_files = [p for p in all_ui_files if "P4" in ui_file_meta.get(p, "")]
not_phase4_files = [p for p in all_ui_files if "P4" not in ui_file_meta.get(p, "")]

lines = []
lines.append("# TFCRM Smart Search — System-wide Live Inventory")
lines.append("")
lines.append(f"- Target: `{ROOT}`")
lines.append(f"- UI files with search signals: **{len(all_ui_files)}**")
lines.append(f"- UI files already carrying Phase 4 marker/hook: **{len(phase4_files)}**")
lines.append(f"- UI files still requiring classification/migration: **{len(not_phase4_files)}**")
lines.append(f"- Server files with search-related signals: **{len(backend_hits)}**")
lines.append("")
lines.append("## UI Search Inventory")
lines.append("")
for rel in all_ui_files:
    lines.append(f"### `{rel}` — current markers: `{ui_file_meta.get(rel, 'NONE')}`")
    for idx, kind, snippet in ui_hits[rel]:
        lines.append(f"- L{idx} `{kind}` — `{snippet.replace('`', "'")}`")
    lines.append("")

lines.append("## Server-side Search Inventory")
lines.append("")
for rel in sorted(backend_hits):
    lines.append(f"### `{rel}`")
    for idx, kind, snippet in backend_hits[rel]:
        lines.append(f"- L{idx} `{kind}` — `{snippet.replace('`', "'")}`")
    lines.append("")

lines.append("## Migration Rule")
lines.append("")
lines.append("Every real user-facing search must be classified before migration as one of: `SERVER_DATA`, `LOCAL_COLLECTION`, `NAVIGATION`, `SETTINGS`, or `GLOBAL`.")
lines.append("The rollout must preserve the page's existing permission scope, filters, pagination and API source. No search is considered migrated merely because a microphone icon was added.")
lines.append("")
lines.append("Required capabilities after migration: P1 normalization, P2 typo tolerance, P3 suggestions/autocomplete, P4 voice-to-the-same-search-state.")
lines.append("")
lines.append("## Safety")
lines.append("")
lines.append("This audit makes **no source, DB, schema or PM2 changes**.")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("PASS/FAIL: PASS")
print(f"AUDIT_REPORT: {OUT}")
print(f"UI_SEARCH_FILES: {len(all_ui_files)}")
print(f"PHASE4_MARKED_UI_FILES: {len(phase4_files)}")
print(f"PENDING_UI_FILES: {len(not_phase4_files)}")
print(f"SERVER_SEARCH_FILES: {len(backend_hits)}")
print("SOURCE_CHANGED: NO")
print("DB_CHANGED: NO")
print("PM2_TOUCHED: NO")
