# TFCRM Egypt Location + Walk-in Patch V4

Use V4 only.

V4 uses a fresh deterministic assembler that reads the already-verified V3 data parts, applies the regex replacement fix before writing the patcher, and verifies the final SHA256.

Expected output:
PATCHER_READY_V4

Expected patcher SHA256:
5863a6621c65bd069df0b2bebdf8f402f3088de4a86303c3230f2a30cafab471

Execution:
1. Fetch latest main of tfcrm-patchs.
2. Enter TFCRM-Egypt-Location-WalkIn-Patch-V4.
3. Remove any old generated apply_tfcrm_egypt_walkin_patch.py in V4.
4. Run python3 ASSEMBLE_PATCHER.py.
5. Verify PATCHER_READY_V4 and the exact SHA256 above.
6. From TFCRM root run dry-run, then apply only if dry-run succeeds.
7. Run only scripts/apply-crm-egypt-location-walkin-migration.ts after successful apply.

Do not use V1, V2 or V3 execution scripts.
