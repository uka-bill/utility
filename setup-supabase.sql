-- UKA-BILL Supabase Setup Script
-- Run this in your Supabase SQL Editor
-- Project: uka-bill
-- Year: 2026
-- Contact: aka.sazali@gmail.com

-- 1. Create schools table
CREATE TABLE IF NOT EXISTS schools (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT,
    address TEXT,
    contact_person TEXT,
    phone TEXT,
    email TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create departments table
CREATE TABLE IF NOT EXISTS departments (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT,
    description TEXT,
    contact_person TEXT,
    phone TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create utility_bills table
CREATE TABLE IF NOT EXISTS utility_bills (
    id BIGSERIAL PRIMARY KEY,
    utility_type TEXT NOT NULL CHECK (utility_type IN ('water', 'electricity', 'telephone')),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('school', 'department')),
    entity_id BIGINT NOT NULL,
    account_number TEXT,
    meter_number TEXT,
    phone_number TEXT,
    current_charges DECIMAL(10,2) DEFAULT 0.00,
    late_charges DECIMAL(10,2) DEFAULT 0.00,
    unsettled_charges DECIMAL(10,2) DEFAULT 0.00,
    amount_paid DECIMAL(10,2) DEFAULT 0.00,
    consumption_m3 DECIMAL(10,2),
    consumption_kwh DECIMAL(10,2),
    month INTEGER NOT NULL CHECK (month >= 1 AND month <= 12),
    year INTEGER NOT NULL,
    bill_image TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create budgets table
CREATE TABLE IF NOT EXISTS budgets (
    id BIGSERIAL PRIMARY KEY,
    total_allocated DECIMAL(10,2) DEFAULT 60000.00,
    water_allocated DECIMAL(10,2) DEFAULT 15000.00,
    electricity_allocated DECIMAL(10,2) DEFAULT 35000.00,
    telephone_allocated DECIMAL(10,2) DEFAULT 10000.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Insert default budget for 2026
INSERT INTO budgets (total_allocated, water_allocated, electricity_allocated, telephone_allocated)
VALUES (60000.00, 15000.00, 35000.00, 10000.00)
ON CONFLICT DO NOTHING;

-- 6. Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_utility_bills_entity_type ON utility_bills(entity_type);
CREATE INDEX IF NOT EXISTS idx_utility_bills_entity_id ON utility_bills(entity_id);
CREATE INDEX IF NOT EXISTS idx_utility_bills_month_year ON utility_bills(month, year);
CREATE INDEX IF NOT EXISTS idx_utility_bills_utility_type ON utility_bills(utility_type);

-- 7. Enable Row Level Security (optional but recommended)
ALTER TABLE schools ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE utility_bills ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;

-- 8. Create policies for public access (since this is internal ministry app)
CREATE POLICY "Enable read access for all users" ON schools FOR SELECT USING (true);
CREATE POLICY "Enable insert access for all users" ON schools FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for all users" ON schools FOR UPDATE USING (true);
CREATE POLICY "Enable delete access for all users" ON schools FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON departments FOR SELECT USING (true);
CREATE POLICY "Enable insert access for all users" ON departments FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for all users" ON departments FOR UPDATE USING (true);
CREATE POLICY "Enable delete access for all users" ON departments FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON utility_bills FOR SELECT USING (true);
CREATE POLICY "Enable insert access for all users" ON utility_bills FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for all users" ON utility_bills FOR UPDATE USING (true);
CREATE POLICY "Enable delete access for all users" ON utility_bills FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON budgets FOR SELECT USING (true);
CREATE POLICY "Enable insert access for all users" ON budgets FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for all users" ON budgets FOR UPDATE USING (true);

-- 9. Add sample data for testing (optional)
INSERT INTO schools (name, code, address, contact_person, phone, email) VALUES
('Ministry of Education HQ', 'MOE-001', 'Bandar Seri Begawan', 'Director', '+6731234567', 'hq@moe.gov.bn'),
('Sekolah Rendah Example', 'SR-001', 'Kuala Belait', 'Headmaster', '+6732345678', 'sr001@moe.gov.bn')
ON CONFLICT DO NOTHING;

INSERT INTO departments (name, code, description, contact_person, phone) VALUES
('Finance Department', 'FIN-001', 'Handles all financial matters', 'Finance Director', '+6733456789'),
('Administration Department', 'ADM-001', 'General administration', 'Admin Manager', '+6734567890')
ON CONFLICT DO NOTHING;

-- 10. Print success message
DO $$
BEGIN
    RAISE NOTICE '✅ UKA-BILL database setup completed successfully!';
    RAISE NOTICE '📅 Year: 2026';
    RAISE NOTICE '👤 Contact: aka.sazali@gmail.com';
    RAISE NOTICE '🚀 System ready for Ministry of Education Brunei';
END $$;