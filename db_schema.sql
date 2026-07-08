-- PostgreSQL schema for the IMS desktop application (Shahajahan Enterprise clone).
-- Re-runnable: drops and recreates everything.

DROP VIEW IF EXISTS customer_dues, supplier_dues, product_stock CASCADE;
DROP TABLE IF EXISTS
    installment_payments, installments, sale_return_items, sales_returns,
    purchase_return_items, purchase_returns, damaged_products,
    sale_items, sales, purchase_items, purchases,
    cash_collections, cash_deliveries, bank_transactions,
    investments, investment_heads, incomes, expenses,
    employees, customers, suppliers, products,
    card_types, banks, categories, companies, system_info, users,
    sales_orders, purchase_orders, cash_collections_old, income
    CASCADE;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL,          -- sha256 hex
    full_name VARCHAR(100) DEFAULT ''
);

CREATE TABLE system_info (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    company_name VARCHAR(200) NOT NULL DEFAULT '',
    company_address TEXT DEFAULT '',
    telephone_no VARCHAR(100) DEFAULT '',
    email_address VARCHAR(100) DEFAULT '',
    web_address VARCHAR(100) DEFAULT '',
    system_start_date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL
);

CREATE TABLE banks (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL
);

CREATE TABLE card_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    company_id INTEGER REFERENCES companies(id),
    category_id INTEGER REFERENCES categories(id),
    product_type VARCHAR(20) DEFAULT 'NoBarCode',   -- NoBarCode | BarCode
    model_name VARCHAR(200) NOT NULL,
    warning_qty NUMERIC(12,2) DEFAULT 0,
    warranty_compressor INTEGER DEFAULT 0,
    warranty_panel INTEGER DEFAULT 0,
    warranty_motor INTEGER DEFAULT 0,
    warranty_spareparts INTEGER DEFAULT 0,
    warranty_service INTEGER DEFAULT 0,
    purchase_rate NUMERIC(14,2) DEFAULT 0,
    sales_rate NUMERIC(14,2) DEFAULT 0,
    mrp_rate NUMERIC(14,2) DEFAULT 0,
    stock_qty NUMERIC(12,2) DEFAULT 0
);

CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    father_name VARCHAR(200) DEFAULT '',
    mother_name VARCHAR(200) DEFAULT '',
    contact_no VARCHAR(50) DEFAULT '',
    email VARCHAR(100) DEFAULT '',
    national_id VARCHAR(50) DEFAULT '',
    blood_group VARCHAR(10) DEFAULT '',
    joining_date DATE DEFAULT CURRENT_DATE,
    designation VARCHAR(100) DEFAULT '',
    present_address TEXT DEFAULT '',
    permanent_address TEXT DEFAULT '',
    gross_salary NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    contact_no VARCHAR(50) DEFAULT '',
    address TEXT DEFAULT '',
    customer_type VARCHAR(20) DEFAULT 'Retail',
    opening_due NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    contact_person VARCHAR(200) DEFAULT '',
    contact_no VARCHAR(50) DEFAULT '',
    address TEXT DEFAULT '',
    opening_due NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE purchases (
    id SERIAL PRIMARY KEY,
    purchase_date DATE NOT NULL DEFAULT CURRENT_DATE,
    challan_no VARCHAR(50) DEFAULT '',
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    gross_total NUMERIC(14,2) DEFAULT 0,
    flat_discount NUMERIC(14,2) DEFAULT 0,
    net_total NUMERIC(14,2) DEFAULT 0,
    paid_amount NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE purchase_items (
    id SERIAL PRIMARY KEY,
    purchase_id INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    qty NUMERIC(12,2) NOT NULL,
    mrp_rate NUMERIC(14,2) DEFAULT 0,
    purchase_rate NUMERIC(14,2) DEFAULT 0,
    sales_rate NUMERIC(14,2) DEFAULT 0,
    discount_pct NUMERIC(7,2) DEFAULT 0,
    total NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    invoice_no VARCHAR(30) UNIQUE NOT NULL,
    sales_date DATE NOT NULL DEFAULT CURRENT_DATE,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    sale_kind VARCHAR(10) NOT NULL DEFAULT 'CASH',   -- CASH | CREDIT
    gross_total NUMERIC(14,2) DEFAULT 0,
    flat_discount NUMERIC(14,2) DEFAULT 0,
    vat_amount NUMERIC(14,2) DEFAULT 0,
    net_total NUMERIC(14,2) DEFAULT 0,
    paid_amount NUMERIC(14,2) DEFAULT 0,             -- cash + card + down payment
    card_bank_id INTEGER REFERENCES banks(id),
    card_amount NUMERIC(14,2) DEFAULT 0,
    interest_rate NUMERIC(7,2) DEFAULT 0,
    interest_amount NUMERIC(14,2) DEFAULT 0,
    remind_date DATE,
    sold_by VARCHAR(50) DEFAULT ''
);

CREATE TABLE sale_items (
    id SERIAL PRIMARY KEY,
    sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    qty NUMERIC(12,2) NOT NULL,
    unit_price NUMERIC(14,2) DEFAULT 0,
    discount_pct NUMERIC(7,2) DEFAULT 0,
    total NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE installments (
    id SERIAL PRIMARY KEY,
    sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    schedule_date DATE NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    paid_amount NUMERIC(14,2) DEFAULT 0,
    paid_date DATE,
    status VARCHAR(10) DEFAULT 'Due'                 -- Due | Paid
);

CREATE TABLE sales_returns (
    id SERIAL PRIMARY KEY,
    return_no VARCHAR(30) NOT NULL,
    return_date DATE NOT NULL DEFAULT CURRENT_DATE,
    sale_id INTEGER NOT NULL REFERENCES sales(id),
    net_total NUMERIC(14,2) DEFAULT 0,
    back_amount NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE sale_return_items (
    id SERIAL PRIMARY KEY,
    return_id INTEGER NOT NULL REFERENCES sales_returns(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    qty NUMERIC(12,2) NOT NULL,
    unit_price NUMERIC(14,2) DEFAULT 0,
    total NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE purchase_returns (
    id SERIAL PRIMARY KEY,
    return_no VARCHAR(30) NOT NULL,
    return_date DATE NOT NULL DEFAULT CURRENT_DATE,
    purchase_id INTEGER NOT NULL REFERENCES purchases(id),
    net_total NUMERIC(14,2) DEFAULT 0,
    back_amount NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE purchase_return_items (
    id SERIAL PRIMARY KEY,
    return_id INTEGER NOT NULL REFERENCES purchase_returns(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    qty NUMERIC(12,2) NOT NULL,
    unit_price NUMERIC(14,2) DEFAULT 0,
    total NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE damaged_products (
    id SERIAL PRIMARY KEY,
    damage_no VARCHAR(30) NOT NULL,
    damage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    qty NUMERIC(12,2) NOT NULL,
    rate NUMERIC(14,2) DEFAULT 0,
    total NUMERIC(14,2) DEFAULT 0,
    remarks TEXT DEFAULT ''
);

CREATE TABLE cash_collections (
    id SERIAL PRIMARY KEY,
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    receipt_no VARCHAR(30) DEFAULT '',
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    pay_type VARCHAR(30) DEFAULT 'Cash',             -- Cash | Check | Mobile Bank
    bank_id INTEGER REFERENCES banks(id),
    check_no VARCHAR(50) DEFAULT '',
    check_issue_date DATE,
    branch_name VARCHAR(100) DEFAULT '',
    account_no VARCHAR(50) DEFAULT '',
    mobile_bank VARCHAR(50) DEFAULT '',
    mobile_no VARCHAR(50) DEFAULT '',
    amount NUMERIC(14,2) DEFAULT 0,
    adjustment NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE cash_deliveries (
    id SERIAL PRIMARY KEY,
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    voucher_no VARCHAR(30) DEFAULT '',
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    pay_type VARCHAR(30) DEFAULT 'Cash',
    bank_id INTEGER REFERENCES banks(id),
    account_no VARCHAR(50) DEFAULT '',
    amount NUMERIC(14,2) DEFAULT 0,
    remarks TEXT DEFAULT ''
);

CREATE TABLE bank_transactions (
    id SERIAL PRIMARY KEY,
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    tran_no VARCHAR(30) DEFAULT '',
    tran_type VARCHAR(20) DEFAULT 'Deposit',         -- Deposit | Withdraw
    bank_id INTEGER REFERENCES banks(id),
    amount NUMERIC(14,2) DEFAULT 0,
    check_no VARCHAR(50) DEFAULT '',
    remarks TEXT DEFAULT ''
);

CREATE TABLE investment_heads (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    head_type VARCHAR(20) NOT NULL DEFAULT 'FIXED'   -- FIXED | CURRENT | LIABILITY
);

CREATE TABLE investments (
    id SERIAL PRIMARY KEY,
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    head_id INTEGER NOT NULL REFERENCES investment_heads(id),
    purpose VARCHAR(200) DEFAULT '',
    amount NUMERIC(14,2) DEFAULT 0,
    inv_type VARCHAR(20) NOT NULL DEFAULT 'FIXED'    -- FIXED | CURRENT | LIAB_REC | LIAB_PAY
);

CREATE TABLE incomes (
    id SERIAL PRIMARY KEY,
    income_date DATE NOT NULL DEFAULT CURRENT_DATE,
    description TEXT DEFAULT '',
    amount NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    expense_date DATE NOT NULL DEFAULT CURRENT_DATE,
    description TEXT DEFAULT '',
    amount NUMERIC(14,2) DEFAULT 0
);

-- Dues -------------------------------------------------------------------

CREATE VIEW customer_dues AS
SELECT c.id,
       c.opening_due
       + COALESCE((SELECT SUM(s.net_total - s.paid_amount) FROM sales s
                   WHERE s.customer_id = c.id), 0)
       - COALESCE((SELECT SUM(cc.amount + cc.adjustment) FROM cash_collections cc
                   WHERE cc.customer_id = c.id), 0)
       - COALESCE((SELECT SUM(sr.back_amount) FROM sales_returns sr
                   JOIN sales s2 ON s2.id = sr.sale_id
                   WHERE s2.customer_id = c.id), 0) AS total_due
FROM customers c;

CREATE VIEW supplier_dues AS
SELECT sp.id,
       sp.opening_due
       + COALESCE((SELECT SUM(p.net_total - p.paid_amount) FROM purchases p
                   WHERE p.supplier_id = sp.id), 0)
       - COALESCE((SELECT SUM(cd.amount) FROM cash_deliveries cd
                   WHERE cd.supplier_id = sp.id), 0)
       - COALESCE((SELECT SUM(pr.back_amount) FROM purchase_returns pr
                   JOIN purchases p2 ON p2.id = pr.purchase_id
                   WHERE p2.supplier_id = sp.id), 0) AS total_due
FROM suppliers sp;

-- Seed data ---------------------------------------------------------------

INSERT INTO users (username, password_hash, full_name) VALUES
-- password: 1234
('sajad', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'Sajad'),
-- password: admin
('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Administrator');

INSERT INTO system_info (id, company_name, company_address, telephone_no, email_address, web_address, system_start_date)
VALUES (1, 'Shahajahan Enterprise', 'Kesorhat, Mohanpur, Rajshahi', '+8801761777748', '', '', '2018-12-01');

INSERT INTO companies (code, name) VALUES
('00001', 'UNITECH'), ('00002', 'MINISTER'), ('00003', 'VIGO'),
('00004', 'WALTON'), ('00005', 'EURO STAR'), ('00006', 'KIAM'), ('00007', 'SHORIF');

INSERT INTO categories (code, name) VALUES
('00001', 'LED TELEVISION'), ('00002', 'FREEZE & REFREJERITOR'), ('00003', 'ELECTIC KECTLY'),
('00004', 'OVEN'), ('00005', 'RICE CUKER'), ('00006', 'PRESSER CUKER'), ('00007', 'COMPUTER BOX'),
('00008', 'GAS STOVE'), ('00009', 'BLENDER'), ('00010', 'CILING FAN'), ('00011', 'ROOM HITER'),
('00012', 'IRON'), ('00013', 'FLASK'), ('00014', 'REMOT'), ('00015', 'SELAI MECHINE'),
('00016', 'BATERY'), ('00017', 'TEL'), ('00018', 'KECHY'), ('00019', 'GAS SELINDER'),
('00020', 'TABLE FAN'), ('00021', 'HIGH SPEED FAN'), ('00022', 'INDUCTION CUKER');

INSERT INTO banks (code, name) VALUES
('00001', 'Jamuna Bank'), ('00002', 'City Bank'), ('00003', 'Islami Bank'), ('00004', 'Sonali Bank');

INSERT INTO card_types (code, name) VALUES
('00001', 'Visa'), ('00002', 'Master Card'), ('00003', 'DBBL Nexus');

INSERT INTO products (code, company_id, category_id, model_name, warning_qty,
                      purchase_rate, sales_rate, mrp_rate, stock_qty) VALUES
('000001', 1, 2, 'UPBLR-248L',  2, 25714.00, 30000.00, 34000.00, 1),
('000002', 1, 2, 'UPBLR-220L',  2, 22000.00, 26000.00, 28000.00, 15),
('000003', 1, 2, 'UPBLR-240L',  2, 24000.00, 28000.00, 30000.00, 12),
('000004', 1, 2, 'UPBLR-198L',  2, 19000.00, 23000.00, 25000.00, 8),
('000005', 1, 2, 'UPBLR-190L',  2, 18500.00, 22000.00, 24000.00, 6),
('000006', 1, 2, 'UPBLR-228L',  2, 23000.00, 27000.00, 29000.00, 9),
('000007', 2, 2, 'M-165 L',     2, 15000.00, 18000.00, 20000.00, 5),
('000008', 2, 2, 'M-195 L',     2, 17000.00, 20000.00, 22000.00, 4),
('000009', 1, 1, 'UPBLR-24"',   2,  9500.00, 12000.00, 13500.00, 7),
('000010', 3, 3, 'VIG-222 L',   2,  1500.00,  1950.00,  2200.00, 12),
('000011', 3, 1, 'VIG-22"',     2,  8800.00, 11000.00, 12500.00, 10),
('000012', 3, 1, 'VIG-20"',     2, 10230.00, 11000.00, 11000.00, 1),
('000013', 3, 5, 'VIG-3.0 L',   2,  1603.41,  2000.00,  2000.00, 14),
('000014', 3, 6, 'VIG-3 L',     2,   976.50,  1050.00,  1050.00, 1),
('000015', 3, 5, 'VIG- 633 L',  2,  1400.00,  1800.00,  2000.00, 11),
('000016', 3, 3, 'VIG-2 L',     2,  1100.00,  1400.00,  1600.00, 13),
('000017', 3, 7, 'VIG-1202 A',  2,  2430.00,  2700.00,  2700.00, 6),
('000018', 4, 2, 'WFA-2D4-0401',2, 21910.16, 26000.00, 28500.00, 3),
('000019', 5, 5, 'TC-2.2 L',    2,  1850.00,  2250.00,  2250.00, 4),
('000020', 5, 8, 'ES-114',      2,   750.00,  1050.00,  1050.00, 9);

INSERT INTO employees (code, name, contact_no, designation, joining_date, gross_salary) VALUES
('00001', 'SAJAD', '01761777748', 'Show Room Manager', '2019-01-01', 15000);

INSERT INTO customers (code, name, contact_no, address, customer_type, opening_due) VALUES
('NEW001', 'AJIJUL',      '01734240328', 'MIJAPUR BAGMARA',   'Retail', 3499.98),
('NEW002', 'AJIM VAI',    '01750330568', 'KHALGAM BAGMARA',   'Retail', 5500.00),
('NEW003', 'ANAMUL H.',   '01734245771', 'KONDA BAGMARA',     'Retail', 18000.00),
('NEW004', 'ATAUR',       '01780670813', 'NAOGA',             'Retail', 6999.93),
('NEW005', 'BABU',        '01736-350657','PALUPARA',          'Retail', 12000.00),
('NEW006', 'BABUL MISTRE','01852666159', 'MOHONPUR',          'Retail', 10050.00),
('NEW007', 'DANES (CH.)', '01784-092251','KESHUR HAT',        'Retail', 1500.00),
('NEW008', 'DULAL',       '01784923005', 'MIJAPUR BAGMARA',   'Retail', 3499.98),
('NEW009', 'HABIBUR',     '01746-852382','KKHUDAPUR BAGMARA', 'Retail', 0.00),
('NEW010', 'HABIBUR',     '01740258145', 'BELNA MOHON PUR',   'Retail', 4000.00),
('NEW011', 'ILIYAS',      '01740-255235','KONDA BAGMARA',     'Retail', 5000.00),
('NEW012', 'JAMAL MAMA',  '01712345678', 'KESORHAT',          'Retail', 6400.00),
('000458', 'JILLU RAHMAN','01795-414316','GARMATI TANOR',     'Retail', 8500.00),
('NEW013', 'MALEQ',       '01732-860188','MIJAPUR BAGMARA',   'Retail', 9500.00),
('NEW014', 'MANNAN',      '01791-465188','NARUPARA BAGMARA',  'Retail', -2000.00),
('NEW015', 'MOMIN MAMA',  '01736046599', 'KESORHAT',          'Retail', 4000.00),
('686',    'NAIMUL',      '01747-561155','HATTOR MOHON PUR',  'Retail', 12500.00);

INSERT INTO suppliers (code, name, contact_person, contact_no, address, opening_due) VALUES
('00001', 'SALMA SUTA GAR', 'MOJIBOR',      '01712570025', 'NAOGA',    0),
('00002', 'CIRCLE',         'NAJRUL ISLAM', '01777700575', 'RAJSHAHI', 0),
('00003', 'AKASH',          'MOCMOIL',      '01717954562', 'MOCMOIL',  0),
('00004', 'AMJAD',          'AMJAD',        '01740562064', 'KESHORHAT',0),
('00005', 'RAQIB SIR',      'RAQIB',        '01704167788', 'KESHOR HAT PARA', 104238.00),
('00006', 'ALOM',           'ALOM',         '01712570025', 'RAJSHAHI', 22200.00);

INSERT INTO investment_heads (code, name, head_type) VALUES
('00001', 'Showroom Security', 'FIXED'),
('00002', 'Decoration',        'FIXED'),
('00003', 'Furniture',         'FIXED'),
('00004', 'Equpment',          'FIXED'),
('00005', 'Software',          'FIXED'),
('00006', 'Bank Loan',         'LIABILITY'),
('00007', 'Person Loan',       'LIABILITY'),
('00008', 'Others',            'LIABILITY');

INSERT INTO investments (entry_date, head_id, purpose, amount, inv_type) VALUES
('2018-12-01', 1, 'Showroom Security', 300000, 'FIXED'),
('2018-12-01', 2, 'Opening Decoration', 100000, 'FIXED'),
('2018-12-01', 3, 'Opening Furniture',   50000, 'FIXED'),
('2018-12-01', 4, 'Computer',            13000, 'FIXED'),
('2018-12-01', 5, 'Software Purchase',   11000, 'FIXED');

INSERT INTO incomes (income_date, description, amount) VALUES
(CURRENT_DATE - 7, 'Servicing income', 2500.00),
(CURRENT_DATE - 2, 'Sales income',    12000.00);

INSERT INTO expenses (expense_date, description, amount) VALUES
(CURRENT_DATE - 7, 'Office expense',   500.00),
(CURRENT_DATE - 1, 'Electricity bill', 1200.00);
