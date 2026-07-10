-- Audit trail migration. Re-runnable: psql -d ims_db -f migrate_audit_log.sql
--
-- Records every INSERT/UPDATE/DELETE on every table into audit_log via
-- row-level triggers, tagged with the logged-in user. The app publishes the
-- username once per session (SET app.username), the same way it publishes
-- app.company_id. Viewing the log is Admin-only, enforced in the application.

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    logged_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    username VARCHAR(50) NOT NULL DEFAULT '',
    company_id INTEGER,
    table_name VARCHAR(63) NOT NULL,
    operation VARCHAR(6) NOT NULL,          -- INSERT | UPDATE | DELETE
    record_id BIGINT,
    old_data JSONB,                          -- row before (UPDATE/DELETE)
    new_data JSONB                           -- row after  (INSERT/UPDATE)
);

CREATE INDEX IF NOT EXISTS audit_log_logged_at_idx ON audit_log (logged_at DESC);
CREATE INDEX IF NOT EXISTS audit_log_table_idx ON audit_log (table_name);

CREATE OR REPLACE FUNCTION log_audit() RETURNS trigger
    LANGUAGE plpgsql AS
$$
DECLARE
    old_row JSONB;
    new_row JSONB;
BEGIN
    -- Skip UPDATEs that change nothing.
    IF TG_OP = 'UPDATE' AND OLD IS NOT DISTINCT FROM NEW THEN
        RETURN NEW;
    END IF;
    IF TG_OP <> 'INSERT' THEN
        old_row := to_jsonb(OLD) - 'password_hash';   -- never log password hashes
    END IF;
    IF TG_OP <> 'DELETE' THEN
        new_row := to_jsonb(NEW) - 'password_hash';
    END IF;
    INSERT INTO audit_log (username, company_id, table_name, operation,
                           record_id, old_data, new_data)
    VALUES (COALESCE(current_setting('app.username', true), ''),
            COALESCE((new_row ->> 'company_id')::integer,
                     (old_row ->> 'company_id')::integer,
                     app_company_id()),
            TG_TABLE_NAME, TG_OP,
            COALESCE(new_row ->> 'id', old_row ->> 'id')::bigint,
            old_row, new_row);
    RETURN COALESCE(NEW, OLD);
END
$$;

-- Attach the trigger to every table except the log itself.
DO $$
DECLARE t text;
BEGIN
    FOR t IN SELECT tablename FROM pg_tables
             WHERE schemaname = 'public' AND tablename <> 'audit_log'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS audit_trg ON %I', t);
        EXECUTE format('CREATE TRIGGER audit_trg
                            AFTER INSERT OR UPDATE OR DELETE ON %I
                            FOR EACH ROW EXECUTE FUNCTION log_audit()', t);
    END LOOP;
END $$;
