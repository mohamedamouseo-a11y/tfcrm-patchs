# TFCRM Egypt Location + Walk-in Patch

This package is a guarded semantic patch for the reviewed TFCRM `main` revision.

## What to run

```bash
python3 apply_tfcrm_egypt_walkin_patch.py --root . --dry-run
python3 apply_tfcrm_egypt_walkin_patch.py --root .
npx tsx scripts/apply-crm-egypt-location-walkin-migration.ts
npm run check
npm run build
```

The patcher creates the new project files and modifies only the listed TFCRM files through exact/guarded anchors. If a required anchor is missing or ambiguous, it stops instead of guessing.

See `PATCH_MANIFEST.txt` for scope and `PROMPT_REPLIT.txt` for the full low-cost application/verification instructions.

The complete executable package is `TFCRM-Egypt-Location-WalkIn-Patch-V1.zip` in this folder.
