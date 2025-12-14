SELECT * FROM public.bills
ORDER BY id ASC 


CREATE USER billuser WITH PASSWORD 'billpass123';
CREATE DATABASE utility_bills;
GRANT ALL PRIVILEGES ON DATABASE utility_bills TO billuser;


CREATE TABLE IF NOT EXISTS bills (
    id SERIAL PRIMARY KEY,

    -- metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    property_name TEXT,
    utility_provider TEXT,
    utility_type TEXT,
    account_number TEXT,
    meter_serial_number TEXT,

    billing_date DATE,
    billing_start_date DATE,
    billing_end_date DATE,
    due_date DATE,

    current_charges NUMERIC,
    previous_balance NUMERIC,
    past_due_balance NUMERIC,
    total_amount_due NUMERIC,
    units_used NUMERIC,
    unit_type TEXT,
    payments NUMERIC,
    balance_forward NUMERIC,

    water_charges NUMERIC,
    sewer_charges NUMERIC,
    storm_water_charges NUMERIC,
    environmental_fee NUMERIC,
    trash_charges NUMERIC,
    gas_charges NUMERIC,
    electric_charges NUMERIC,

    rate_plan TEXT,
    service_days INTEGER,

    extraction_method TEXT,             -- pdfco or openai
    confidence_score NUMERIC,
    requires_review BOOLEAN DEFAULT FALSE,
    raw_extracted_data JSONB            -- entire normalized+raw dictionary
);
