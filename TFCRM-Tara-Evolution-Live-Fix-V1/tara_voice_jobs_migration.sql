-- TFCRM_TARA_EVOLUTION_LIVE_FIX_V1
-- SAFE RUNTIME DATA ONLY. NO VOICE TABLE MIGRATION IN V1.
-- The confirmed tara_voice_jobs legacy schema is intentionally left unchanged here.
-- V1 restores TEXT WhatsApp replies by isolating voice-queue failure in source code.

-- Re-verify both rows immediately before applying.
UPDATE whatsapp_sessions
SET tara_enabled = 1
WHERE id = 6
  AND session_key = 'tcrm-mini-cash-a6b3a6';

UPDATE tara_settings
SET enabled = 1,
    auto_send = 1
WHERE tenant_key = 'tfcrm';

-- Deployment requirement (not SQL):
-- Set TARA_TENANT_KEY=tfcrm in the TFCRM PM2 runtime environment/configuration.

-- DO NOT change Evolution API configuration.
-- DO NOT bulk-update other sessions or tenants.
-- DO NOT ALTER tara_voice_jobs in this V1 patch.
