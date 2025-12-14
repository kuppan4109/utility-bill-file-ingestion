CREATE TABLE IF NOT EXISTS bills (
  id SERIAL PRIMARY KEY,
  email_subject TEXT,
  email_from VARCHAR(255),
  email_received_date TIMESTAMP,
  filename VARCHAR(500),
  file_path TEXT,
  sha256 VARCHAR(64) UNIQUE,
  property_name VARCHAR(200),
  utility_provider VARCHAR(200),
  utility_type VARCHAR(50),
  account_number VARCHAR(100),
  meter_serial_number VARCHAR(100),
  billing_date DATE,
  billing_start_date DATE,
  billing_end_date DATE,
  due_date DATE,
  current_charges DECIMAL(10,2),
  previous_balance DECIMAL(10,2),
  past_due_balance DECIMAL(10,2),
  total_amount_due DECIMAL(10,2),
  units_used DECIMAL(10,2),
  unit_type VARCHAR(20),
  extraction_method VARCHAR(50),
  confidence_score DECIMAL(3,2),
  requires_review BOOLEAN DEFAULT FALSE,
  reviewed BOOLEAN DEFAULT FALSE,
  raw_extracted_data JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bills_sha256 ON bills(sha256);
CREATE INDEX IF NOT EXISTS idx_bills_provider ON bills(utility_provider);
CREATE INDEX IF NOT EXISTS idx_bills_property ON bills(property_name);
CREATE INDEX IF NOT EXISTS idx_bills_billing_date ON bills(billing_date);
