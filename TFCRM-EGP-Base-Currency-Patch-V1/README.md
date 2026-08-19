# TFCRM EGP Base Currency Patch V1

This patch changes TFCRM's base/default currency from Saudi Riyal (SAR) to Egyptian Pound (EGP).

## Scope

- Central `BASE_CURRENCY` becomes `EGP`.
- Live exchange-rate sync becomes `SAR -> EGP` and `USD -> EGP`.
- Admin Currency Settings displays Egyptian Pound as the base currency.
- Currency defaults in the Drizzle schema become EGP.
- Runtime payment/deal/reporting base-currency assumptions in `server/db.ts` become EGP.
- Existing legacy database field names such as `valueSar` are intentionally preserved for compatibility.
- Existing historical records are not relabeled or blindly converted.

## Apply

From the TFCRM project root:

```bash
python /path/to/TFCRM-EGP-Base-Currency-Patch-V1/APPLY_PATCH.py .
npm run check
```

Then start TFCRM and go to:

`Admin Settings > Currency`

1. Click **Sync Rates Now**.
2. Confirm `SAR -> EGP`, `USD -> EGP`, and `EGP -> EGP = 1`.
3. Click **Recalculate All Values** so `valueBase` is recalculated in EGP.

## Safety

The patch creates `.tfcrm-egp-base-currency-v1-backup/` inside the TFCRM project before modifying files.

Do not rename the legacy `valueSar` database column as part of this patch; it stores the original deal amount and changing its physical name would require a separate migration and compatibility review.
