-- One-time migration: single-company IMS database -> multi-company schema.
-- Safe to run exactly once on a database created with the old db_schema.sql.
-- All existing data is kept and assigned to company 1 (taken from system_info).
-- Run with:  psql -d ims_db -v ON_ERROR_STOP=1 -f migrate_multicompany.sql

BEGIN;

-- 1. Old "companies" (product manufacturers) becomes "brands".
ALTER TABLE companies RENAME TO brands;
ALTER TABLE products RENAME COLUMN company_id TO brand_id;
ALTER TABLE products RENAME CONSTRAINT products_company_id_fkey TO products_brand_id_fkey;

-- 2. Session-company helper used by defaults, filters and RLS policies.
CREATE FUNCTION app_company_id() RETURNS integer
    LANGUAGE sql STABLE AS
$$ SELECT NULLIF(current_setting('app.company_id', true), '')::integer $$;

-- 3. New companies (shops) table, seeded from the old system_info row.
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    address TEXT DEFAULT '',
    telephone_no VARCHAR(100) DEFAULT '',
    email_address VARCHAR(100) DEFAULT '',
    web_address VARCHAR(100) DEFAULT '',
    start_date DATE DEFAULT CURRENT_DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO companies (code, name, address, telephone_no, email_address,
                       web_address, start_date)
SELECT '00001', company_name, company_address, telephone_no, email_address,
       web_address, system_start_date
FROM system_info WHERE id = 1;

-- system_info now only remembers which company the app opens with.
ALTER TABLE system_info
    DROP COLUMN company_name,
    DROP COLUMN company_address,
    DROP COLUMN telephone_no,
    DROP COLUMN email_address,
    DROP COLUMN web_address,
    DROP COLUMN system_start_date,
    ADD COLUMN default_company_id INTEGER REFERENCES companies(id);
UPDATE system_info SET default_company_id = 1 WHERE id = 1;

-- 4. Stamp every business table with company_id = 1 and add the
--    default / FK / not-null / RLS backstop / index in one pass.
SET app.company_id = '1';

DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'brands', 'categories', 'banks', 'card_types', 'products', 'employees',
        'customers', 'suppliers', 'purchases', 'sales', 'sales_returns',
        'purchase_returns', 'damaged_products', 'cash_collections',
        'cash_deliveries', 'bank_transactions', 'investment_heads',
        'investments', 'incomes', 'expenses']
    LOOP
        EXECUTE format('ALTER TABLE %I ADD COLUMN company_id INTEGER', t);
        EXECUTE format('UPDATE %I SET company_id = 1', t);
        EXECUTE format('ALTER TABLE %I
                            ALTER COLUMN company_id SET NOT NULL,
                            ALTER COLUMN company_id SET DEFAULT app_company_id(),
                            ADD CONSTRAINT %I FOREIGN KEY (company_id) REFERENCES companies(id)',
                       t, t || '_company_id_fkey');
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format(
            'CREATE POLICY company_isolation ON %I
                 USING (company_id = app_company_id())
                 WITH CHECK (company_id = app_company_id())', t);
        EXECUTE format('CREATE INDEX %I ON %I (company_id)', t || '_company_idx', t);
    END LOOP;
END $$;

-- 5. Invoice numbers are unique per company, not globally.
ALTER TABLE sales DROP CONSTRAINT sales_invoice_no_key;
ALTER TABLE sales ADD CONSTRAINT sales_company_invoice_key UNIQUE (company_id, invoice_no);

-- 6. Dues views: expose company_id and respect RLS of the querying role.
DROP VIEW IF EXISTS customer_dues, supplier_dues;

CREATE VIEW customer_dues WITH (security_invoker = true) AS
SELECT c.id,
       c.company_id,
       c.opening_due
       + COALESCE((SELECT SUM(s.net_total - s.paid_amount) FROM sales s
                   WHERE s.customer_id = c.id), 0)
       - COALESCE((SELECT SUM(cc.amount + cc.adjustment) FROM cash_collections cc
                   WHERE cc.customer_id = c.id), 0)
       - COALESCE((SELECT SUM(sr.back_amount) FROM sales_returns sr
                   JOIN sales s2 ON s2.id = sr.sale_id
                   WHERE s2.customer_id = c.id), 0) AS total_due
FROM customers c;

CREATE VIEW supplier_dues WITH (security_invoker = true) AS
SELECT sp.id,
       sp.company_id,
       sp.opening_due
       + COALESCE((SELECT SUM(p.net_total - p.paid_amount) FROM purchases p
                   WHERE p.supplier_id = sp.id), 0)
       - COALESCE((SELECT SUM(cd.amount) FROM cash_deliveries cd
                   WHERE cd.supplier_id = sp.id), 0)
       - COALESCE((SELECT SUM(pr.back_amount) FROM purchase_returns pr
                   JOIN purchases p2 ON p2.id = pr.purchase_id
                   WHERE p2.supplier_id = sp.id), 0) AS total_due
FROM suppliers sp;

COMMIT;
