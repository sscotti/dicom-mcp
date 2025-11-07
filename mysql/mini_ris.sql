-- Mini-RIS schema for dicom-mcp development
-- -----------------------------------------------------------------------------
-- This schema keeps only the essentials required to drive local imaging
-- workflows, generate HL7/FHIR messages, and produce MWL entries.
-- It intentionally mirrors naming used by HL7 ORM/ORU and FHIR resources
-- (ServiceRequest, ImagingStudy, DiagnosticReport, Practitioner, Patient).

-- Ensure we are operating inside the default schema created by docker-compose
USE orthanc_ris;

SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- -----------------------------------------------------------------------------
-- Lookup tables
-- -----------------------------------------------------------------------------

DROP TABLE IF EXISTS modalities;
CREATE TABLE modalities (
  modality_code VARCHAR(8) PRIMARY KEY,
  modality_name VARCHAR(64) NOT NULL
) ENGINE=InnoDB;

DROP TABLE IF EXISTS body_parts;
CREATE TABLE body_parts (
  body_part_code VARCHAR(32) PRIMARY KEY,
  description VARCHAR(128) NOT NULL
) ENGINE=InnoDB;

DROP TABLE IF EXISTS encounter_types;
CREATE TABLE encounter_types (
  encounter_type_code VARCHAR(16) PRIMARY KEY,
  description VARCHAR(128) NOT NULL
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- Core entities
-- -----------------------------------------------------------------------------

DROP TABLE IF EXISTS patients;
CREATE TABLE patients (
  patient_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  mrn VARCHAR(32) NOT NULL UNIQUE,
  given_name VARCHAR(64) NOT NULL,
  family_name VARCHAR(64) NOT NULL,
  date_of_birth DATE NOT NULL,
  sex ENUM('M','F','O','U') NOT NULL COMMENT 'M=Male, F=Female, O=Other, U=Unknown',
  phone VARCHAR(32),
  email VARCHAR(128),
  address_line VARCHAR(128),
  city VARCHAR(64),
  state VARCHAR(32),
  postal_code VARCHAR(16),
  country_code CHAR(2) NOT NULL,
  preferred_language ENUM('en','es','fr','de','it','pt','nl','sv','fi','da','et','lv','lt','pl','cs','sk','sl','hu','ro','bg','hr','el','mt','ga') NOT NULL DEFAULT 'en',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT chk_patient_mrn CHECK (mrn REGEXP '^MRN[0-9]{4,}$'),
  CONSTRAINT chk_patient_country CHECK (country_code IN ('US','AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE'))
) ENGINE=InnoDB;

DROP TABLE IF EXISTS providers;
CREATE TABLE providers (
  provider_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  npi VARCHAR(20) UNIQUE,
  provider_type ENUM('Radiologist','Ordering','Technologist') NOT NULL,
  given_name VARCHAR(64) NOT NULL,
  family_name VARCHAR(64) NOT NULL,
  phone VARCHAR(32),
  email VARCHAR(128),
  department VARCHAR(64),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

DROP TABLE IF EXISTS encounters;
CREATE TABLE encounters (
  encounter_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  patient_id INT UNSIGNED NOT NULL,
  encounter_number VARCHAR(32) NOT NULL UNIQUE,
  encounter_type_code VARCHAR(16) NOT NULL,
  start_time DATETIME NOT NULL,
  end_time DATETIME,
  referring_provider_id INT UNSIGNED,
  location VARCHAR(64),
  status ENUM('Planned','InProgress','Finished','Cancelled') NOT NULL DEFAULT 'Planned',
  CONSTRAINT fk_encounter_patient FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
  CONSTRAINT fk_encounter_type FOREIGN KEY (encounter_type_code) REFERENCES encounter_types(encounter_type_code),
  CONSTRAINT fk_encounter_ref_provider FOREIGN KEY (referring_provider_id) REFERENCES providers(provider_id)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
  order_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_number VARCHAR(32) NOT NULL UNIQUE,
  accession_number VARCHAR(32) NOT NULL UNIQUE,
  patient_id INT UNSIGNED NOT NULL,
  encounter_id INT UNSIGNED,
  ordering_provider_id INT UNSIGNED,
  performing_provider_id INT UNSIGNED,
  modality_code VARCHAR(8) NOT NULL,
  body_part_code VARCHAR(32),
  reason_code VARCHAR(64),
  reason_description VARCHAR(512),
  priority ENUM('STAT','URGENT','ROUTINE') DEFAULT 'ROUTINE',
  status ENUM('Requested','Scheduled','InProgress','Completed','Cancelled') NOT NULL DEFAULT 'Requested',
  order_datetime DATETIME NOT NULL,
  scheduled_start DATETIME,
  notes TEXT,
  fhir_service_request_id VARCHAR(64),
  hl7_control_code CHAR(2) DEFAULT 'NW',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_order_patient FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
  CONSTRAINT fk_order_encounter FOREIGN KEY (encounter_id) REFERENCES encounters(encounter_id),
  CONSTRAINT fk_order_ordering_provider FOREIGN KEY (ordering_provider_id) REFERENCES providers(provider_id),
  CONSTRAINT fk_order_performing_provider FOREIGN KEY (performing_provider_id) REFERENCES providers(provider_id),
  CONSTRAINT fk_order_modality FOREIGN KEY (modality_code) REFERENCES modalities(modality_code),
  CONSTRAINT fk_order_body_part FOREIGN KEY (body_part_code) REFERENCES body_parts(body_part_code),
  CONSTRAINT chk_order_accession CHECK (accession_number REGEXP '^ACC-[0-9]{4}-[0-9]{4}$')
) ENGINE=InnoDB;

DROP TABLE IF EXISTS order_procedures;
CREATE TABLE order_procedures (
  order_procedure_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_id INT UNSIGNED NOT NULL,
  procedure_code VARCHAR(32) NOT NULL,
  procedure_description VARCHAR(128) NOT NULL,
  laterality ENUM('Left','Right','Bilateral','Unspecified') DEFAULT 'Unspecified',
  quantity TINYINT UNSIGNED DEFAULT 1,
  CONSTRAINT fk_order_procedure_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
) ENGINE=InnoDB;

DROP TABLE IF EXISTS imaging_studies;
CREATE TABLE imaging_studies (
  imaging_study_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_id INT UNSIGNED NOT NULL,
  study_instance_uid VARCHAR(64) NOT NULL UNIQUE,
  study_started DATETIME,
  study_completed DATETIME,
  status ENUM('Registered','Available','Cancelled','EnteredInError') DEFAULT 'Registered',
  number_of_series SMALLINT UNSIGNED,
  number_of_instances INT UNSIGNED,
  fhir_imaging_study_id VARCHAR(64),
  CONSTRAINT fk_imaging_study_order FOREIGN KEY (order_id) REFERENCES orders(order_id)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS reports;
CREATE TABLE reports (
  report_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  imaging_study_id INT UNSIGNED NOT NULL,
  report_number VARCHAR(32) NOT NULL UNIQUE,
  author_provider_id INT UNSIGNED,
  report_status ENUM('Preliminary','Final','Amended','Cancelled') DEFAULT 'Preliminary',
  report_datetime DATETIME,
  report_text LONGTEXT,
  impression TEXT,
  fhir_diagnostic_report_id VARCHAR(64),
  hl7_message_control_id VARCHAR(32),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_report_imaging_study FOREIGN KEY (imaging_study_id) REFERENCES imaging_studies(imaging_study_id),
  CONSTRAINT fk_report_author FOREIGN KEY (author_provider_id) REFERENCES providers(provider_id)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS mwl_tasks;
CREATE TABLE mwl_tasks (
  mwl_task_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_id INT UNSIGNED NOT NULL,
  scheduled_station_aet VARCHAR(16) NOT NULL,
  scheduled_station_name VARCHAR(64),
  scheduled_start DATETIME NOT NULL,
  scheduled_end DATETIME,
  scheduled_performing_provider_id INT UNSIGNED,
  status ENUM('Scheduled','InProgress','Completed','Cancelled') DEFAULT 'Scheduled',
  mwl_payload JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_mwl_order FOREIGN KEY (order_id) REFERENCES orders(order_id),
  CONSTRAINT fk_mwl_performing_provider FOREIGN KEY (scheduled_performing_provider_id) REFERENCES providers(provider_id)
) ENGINE=InnoDB;

CREATE INDEX idx_orders_patient_status ON orders(patient_id, status);
CREATE INDEX idx_orders_accession ON orders(accession_number);
CREATE INDEX idx_encounter_patient ON encounters(patient_id);
CREATE INDEX idx_study_uid ON imaging_studies(study_instance_uid);
CREATE INDEX idx_mwl_station_start ON mwl_tasks(scheduled_station_aet, scheduled_start);

-- -----------------------------------------------------------------------------
-- Seed data for local development
-- -----------------------------------------------------------------------------

INSERT INTO modalities (modality_code, modality_name) VALUES
  ('CT', 'Computed Tomography'),
  ('MR', 'Magnetic Resonance Imaging'),
  ('US', 'Ultrasound'),
  ('DX', 'Digital Radiography'),
  ('CR', 'Computed Radiography'),
  ('MG', 'Mammography'),
  ('XA', 'X-Ray Angiography'),
  ('RF', 'Radio Fluoroscopy'),
  ('NM', 'Nuclear Medicine'),
  ('PT', 'Positron Emission Tomography'),
  ('SC', 'Secondary Capture'),
  ('OT', 'Other')
ON DUPLICATE KEY UPDATE modality_name = VALUES(modality_name);

INSERT INTO body_parts (body_part_code, description) VALUES
  ('HEAD', 'Head/Brain'),
  ('CHEST', 'Chest/Thorax'),
  ('ABD', 'Abdomen'),
  ('PELV', 'Pelvis'),
  ('NECK', 'Neck/Cervical'),
  ('SPINE', 'Spine'),
  ('HEART', 'Heart/Cardiac'),
  ('BRAIN', 'Brain (Detailed)'),
  ('EXT_UP', 'Upper Extremity'),
  ('EXT_LOW', 'Lower Extremity')
ON DUPLICATE KEY UPDATE description = VALUES(description);

INSERT INTO encounter_types (encounter_type_code, description) VALUES
  ('OP', 'Outpatient encounter'),
  ('ER', 'Emergency encounter'),
  ('IP', 'Inpatient encounter')
ON DUPLICATE KEY UPDATE description = VALUES(description);

INSERT INTO patients (mrn, given_name, family_name, date_of_birth, sex, phone, email, address_line, city, state, postal_code, country_code, preferred_language)
VALUES
  ('MRN1001', 'Alex', 'Johnson', '1984-03-12', 'M', '+1-555-0101', 'alex.johnson@example.org', '100 Main St', 'Metropolis', 'CA', '90001', 'US', 'en'),
  ('MRN1002', 'Maria', 'Lopez', '1976-11-05', 'F', '+1-555-0102', 'maria.lopez@example.org', '250 Oak Ave', 'Metropolis', 'CA', '90002', 'US', 'es'),
  ('MRN1003', 'Sam', 'Nguyen', '1992-07-21', 'O', '+1-555-0103', 'sam.nguyen@example.org', '42 Elm Street', 'Metropolis', 'CA', '90003', 'US', 'en')
ON DUPLICATE KEY UPDATE given_name = VALUES(given_name), family_name = VALUES(family_name);

INSERT INTO providers (npi, provider_type, given_name, family_name, phone, email, department)
VALUES
  ('1234567890', 'Ordering', 'Emily', 'Chen', '+1-555-0201', 'echen@metrohospital.org', 'Primary Care'),
  ('2234567890', 'Radiologist', 'Robert', 'Stein', '+1-555-0202', 'rstein@metrohospital.org', 'Radiology'),
  ('3234567890', 'Technologist', 'Casey', 'Wells', '+1-555-0203', 'cwells@metrohospital.org', 'Imaging Services')
ON DUPLICATE KEY UPDATE given_name = VALUES(given_name), family_name = VALUES(family_name);

INSERT INTO encounters (patient_id, encounter_number, encounter_type_code, start_time, referring_provider_id, location, status)
VALUES
  (1, 'ENC-5001', 'OP', '2025-06-01 09:00:00', 1, 'Radiology Check-In', 'InProgress'),
  (2, 'ENC-5002', 'OP', '2025-06-02 08:30:00', 1, 'Radiology Check-In', 'Planned')
ON DUPLICATE KEY UPDATE status = VALUES(status);

INSERT INTO orders (
  order_number, accession_number, patient_id, encounter_id, ordering_provider_id,
  performing_provider_id, modality_code, body_part_code, reason_code, reason_description,
  priority, status, order_datetime, scheduled_start, notes, fhir_service_request_id, hl7_control_code
) VALUES
  ('ORD-2025-0001', 'ACC-2025-0001', 1, 1, 1, 3, 'CT', 'CHEST', 'R07.9', 'Chest pain evaluation',
   'URGENT', 'Scheduled', '2025-06-01 08:45:00', '2025-06-01 09:15:00', 'Rule out pulmonary embolism', NULL, 'NW'),
  ('ORD-2025-0002', 'ACC-2025-0002', 2, 2, 1, 3, 'US', 'ABD', 'R10.9', 'Abdominal pain',
   'ROUTINE', 'Requested', '2025-06-02 08:15:00', '2025-06-02 10:00:00', 'Assess gallbladder', NULL, 'NW')
ON DUPLICATE KEY UPDATE status = VALUES(status);

INSERT INTO order_procedures (order_id, procedure_code, procedure_description, laterality)
VALUES
  (1, '71250', 'CT Thorax without contrast', 'Unspecified'),
  (2, '76700', 'Ultrasound abdomen complete', 'Unspecified')
ON DUPLICATE KEY UPDATE procedure_description = VALUES(procedure_description);

INSERT INTO imaging_studies (order_id, study_instance_uid, study_started, status, number_of_series, number_of_instances)
VALUES
  (1, '1.2.840.113619.2.55.3.2831164352.2025.6.1.9.30.1', '2025-06-01 09:32:00', 'Available', 4, 120)
ON DUPLICATE KEY UPDATE status = VALUES(status);

INSERT INTO reports (
  imaging_study_id, report_number, author_provider_id, report_status, report_datetime,
  report_text, impression
) VALUES
  (1, 'RPT-2025-0001', 2, 'Preliminary', '2025-06-01 11:00:00',
   'CT chest shows no evidence of pulmonary embolism. Mild dependent atelectasis.',
   'No acute findings.')
ON DUPLICATE KEY UPDATE report_status = VALUES(report_status), report_text = VALUES(report_text);

INSERT INTO mwl_tasks (
  order_id, scheduled_station_aet, scheduled_station_name, scheduled_start,
  scheduled_end, scheduled_performing_provider_id, status, mwl_payload
) VALUES
  (1, 'ORTHANC', 'Main CT Suite', '2025-06-01 09:15:00', '2025-06-01 09:45:00', 3, 'Completed',
   JSON_OBJECT(
     'PatientID', 'MRN1001',
     'PatientName', 'Johnson^Alex',
     'PatientBirthDate', '19840312',
     'AccessionNumber', 'ACC-2025-0001',
     'RequestedProcedureDescription', 'CT Thorax without contrast',
     'ScheduledProcedureStepStartDate', '20250601',
     'ScheduledProcedureStepStartTime', '091500',
     'Modality', 'CT',
     'ScheduledStationAETitle', 'ORTHANC'
   ))
ON DUPLICATE KEY UPDATE status = VALUES(status);

-- -----------------------------------------------------------------------------
-- End of mini-RIS schema
-- -----------------------------------------------------------------------------

