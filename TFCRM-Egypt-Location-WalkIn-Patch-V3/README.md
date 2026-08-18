# TFCRM Egypt Location + Walk-in Patch V3

V3 replaces the broken V1/V2 packaging.

## Verified patcher

Expected SHA256:
`e902faea14b2bf9633e5632c3b399bc3005f35903ff1d094b6a64910b9b218f6`

`ASSEMBLE_PATCHER.py` reads exactly these six files only:
- `PATCHER_GZ_B64.part00`
- `PATCHER_GZ_B64.part01`
- `PATCHER_GZ_B64.part02`
- `PATCHER_GZ_B64.part03`
- `PATCHER_GZ_B64.part04`
- `PATCHER_GZ_B64.part05`

The six-part package was verified locally to reconstruct the patcher byte-for-byte and print `PATCHER_READY`.

## Apply

From this V3 folder:

```bash
python3 ASSEMBLE_PATCHER.py
```

Continue only if it prints `PATCHER_READY` and the expected SHA256.

Then from the TFCRM project root:

```bash
python3 <V3_PATH>/apply_tfcrm_egypt_walkin_patch.py --root . --dry-run
```

If dry-run succeeds:

```bash
python3 <V3_PATH>/apply_tfcrm_egypt_walkin_patch.py --root .
npx tsx scripts/apply-crm-egypt-location-walkin-migration.ts
```

Do not use V1 or V2 for this deployment.
