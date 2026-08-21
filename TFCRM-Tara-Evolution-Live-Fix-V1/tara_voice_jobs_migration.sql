-- TFCRM_TARA_EVOLUTION_LIVE_FIX_V1
-- Additive compatibility migration for legacy tara_voice_jobs.
-- IMPORTANT: Manus must inspect INFORMATION_SCHEMA first and only apply missing columns/indexes.

ALTER TABLE tara_voice_jobs
  ADD COLUMN tenant_key varchar(120) NOT NULL DEFAULT 'primary' AFTER id,
  ADD COLUMN platform enum('evolution_whatsapp','meta_whatsapp') NOT NULL DEFAULT 'evolution_whatsapp' AFTER tenant_key,
  ADD COLUMN account_id varchar(255) NOT NULL DEFAULT '' AFTER platform,
  ADD COLUMN conversation_id varchar(255) NOT NULL DEFAULT '' AFTER account_id,
  ADD COLUMN source_message_id varchar(255) NOT NULL DEFAULT '' AFTER conversation_id,
  ADD COLUMN source_db_message_id int NULL AFTER source_message_id,
  ADD COLUMN source_media_ref json NULL AFTER source_db_message_id,
  MODIFY COLUMN status enum('queued','processing','retry','completed','failed','cancelled','superseded','manual_review') NOT NULL DEFAULT 'queued',
  ADD COLUMN attempt_count int NOT NULL DEFAULT 0 AFTER status,
  ADD COLUMN max_attempts int NOT NULL DEFAULT 2 AFTER attempt_count,
  ADD COLUMN lock_token varchar(64) NULL AFTER max_attempts,
  ADD COLUMN locked_at timestamp NULL AFTER lock_token,
  ADD COLUMN next_attempt_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER locked_at,
  ADD COLUMN run_id bigint NULL AFTER next_attempt_at,
  ADD COLUMN transcript_hash varchar(64) NULL AFTER run_id,
  ADD COLUMN transcript_language varchar(20) NULL AFTER transcript_hash,
  ADD COLUMN transcription_confidence decimal(5,4) NULL AFTER transcript_language,
  ADD COLUMN provider_request_id varchar(255) NULL AFTER transcription_confidence,
  ADD COLUMN provider_message_id varchar(255) NULL AFTER provider_request_id,
  ADD COLUMN generated_bytes int NOT NULL DEFAULT 0 AFTER provider_message_id,
  ADD COLUMN last_error_code varchar(120) NULL AFTER generated_bytes,
  ADD COLUMN last_error text NULL AFTER last_error_code,
  ADD COLUMN completed_at timestamp NULL AFTER last_error;

-- Add only when absent:
CREATE UNIQUE INDEX uq_tara_voice_source
  ON tara_voice_jobs (tenant_key, platform, account_id, source_message_id);

CREATE INDEX idx_tara_voice_jobs_ready
  ON tara_voice_jobs (status, next_attempt_at, id);

CREATE INDEX idx_tara_voice_jobs_conversation
  ON tara_voice_jobs (tenant_key, platform, account_id, conversation_id);

CREATE INDEX idx_tara_voice_jobs_lock
  ON tara_voice_jobs (status, locked_at);

-- Runtime data changes, execute only after re-verifying target rows:
UPDATE whatsapp_sessions
SET tara_enabled = 1
WHERE id = 6
  AND session_key = 'tcrm-mini-cash-a6b3a6';

UPDATE tara_settings
SET enabled = 1,
    auto_send = 1
WHERE tenant_key = 'tfcrm';

-- TARA_TENANT_KEY=tfcrm must be set in the TFCRM PM2 runtime environment/configuration.
