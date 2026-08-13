CREATE DATABASE IF NOT EXISTS pcms;
USE pcms;

-- The Flask application creates the tables automatically with SQLAlchemy.
-- Set DATABASE_URL in .env:
-- mysql+pymysql://root:YOUR_PASSWORD@localhost/pcms


-- Milestone 2 tables are created automatically by SQLAlchemy db.create_all().
-- Tables:
-- electronic_health_records
-- consultations
-- prescriptions
-- laboratory_reports


-- Milestone 4: Patient Feedback & Satisfaction
CREATE TABLE IF NOT EXISTS patient_feedback (
  id INT PRIMARY KEY AUTO_INCREMENT,
  patient_id INT NOT NULL,
  doctor_id INT NULL,
  department VARCHAR(120),
  consultation_rating INT NOT NULL,
  hospital_rating INT NOT NULL,
  laboratory_rating INT NOT NULL,
  pharmacy_rating INT NOT NULL,
  comments TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_feedback_patient (patient_id),
  INDEX idx_feedback_doctor (doctor_id),
  CONSTRAINT fk_feedback_patient FOREIGN KEY (patient_id) REFERENCES patients(id),
  CONSTRAINT fk_feedback_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id)
);


-- Payment transactions: supports patient UPI, Online and Cash workflows.
CREATE TABLE IF NOT EXISTS payment_transactions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  bill_id INT NOT NULL,
  patient_id INT NOT NULL,
  amount DECIMAL(12,2) NOT NULL DEFAULT 0,
  payment_method VARCHAR(50) NOT NULL,
  status VARCHAR(40) DEFAULT 'Pending',
  transaction_reference VARCHAR(120) UNIQUE,
  notes TEXT,
  gateway VARCHAR(40) NULL,
  gateway_order_id VARCHAR(100) NULL,
  gateway_payment_id VARCHAR(100) NULL,
  gateway_signature VARCHAR(128) NULL,
  gateway_status VARCHAR(40) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  processed_at DATETIME NULL,
  INDEX idx_payment_bill (bill_id),
  INDEX idx_payment_patient (patient_id),
  CONSTRAINT fk_payment_bill FOREIGN KEY (bill_id) REFERENCES bills(id),
  CONSTRAINT fk_payment_patient FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- Admin-managed system settings.
CREATE TABLE IF NOT EXISTS system_settings (
  id INT PRIMARY KEY AUTO_INCREMENT,
  setting_key VARCHAR(100) NOT NULL UNIQUE,
  setting_value TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT IGNORE INTO system_settings(setting_key, setting_value) VALUES
('hospital_name','Integrated Patient Care Hospital'),
('currency_symbol','₹'),
('upi_id','hospital@upi'),
('cash_payment_enabled','1'),
('upi_payment_enabled','1'),
('online_payment_enabled','1'),
('appointment_window','30'),
('maintenance_mode','0');

