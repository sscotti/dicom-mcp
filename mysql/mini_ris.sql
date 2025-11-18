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

-- DICOM Tags Reference (from dicom.dic standard)
-- Useful for MWL creation and DICOM attribute validation
DROP TABLE IF EXISTS dicom_tags;
CREATE TABLE dicom_tags (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tag VARCHAR(64),
  tag_group VARCHAR(16),
  element VARCHAR(16),
  vr VARCHAR(4),
  name VARCHAR(128),
  vm VARCHAR(8),
  version VARCHAR(16),
  INDEX idx_tag (tag),
  INDEX idx_name (name)
) ENGINE=InnoDB;

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

-- Procedures catalog (focused on CR for single-image studies)
DROP TABLE IF EXISTS procedures;
CREATE TABLE procedures (
  procedure_code VARCHAR(32) PRIMARY KEY,
  procedure_name VARCHAR(128) NOT NULL,
  modality_code VARCHAR(8) NOT NULL,
  body_part_code VARCHAR(32),
  typical_views VARCHAR(64),
  typical_image_count TINYINT UNSIGNED DEFAULT 1,
  description TEXT,
  active BOOLEAN DEFAULT TRUE,
  CONSTRAINT fk_procedure_modality FOREIGN KEY (modality_code) REFERENCES modalities(modality_code),
  CONSTRAINT fk_procedure_body_part FOREIGN KEY (body_part_code) REFERENCES body_parts(body_part_code)
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
  CONSTRAINT fk_order_procedure_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
  CONSTRAINT fk_order_procedure_code FOREIGN KEY (procedure_code) REFERENCES procedures(procedure_code)
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
CREATE TABLE `reports` (
  `report_id` int unsigned NOT NULL AUTO_INCREMENT,
  `imaging_study_id` int unsigned NOT NULL,
  `report_number` varchar(32) NOT NULL,
  `author_provider_id` int unsigned DEFAULT NULL,
  `report_status` enum('Preliminary','Final','Amended','Cancelled') DEFAULT 'Preliminary',
  `report_datetime` datetime DEFAULT NULL,
  `report_text` longtext,
  `impression` text,
  `fhir_diagnostic_report_id` varchar(64) DEFAULT NULL,
  `dicom_sop_instance_uid` varchar(64) DEFAULT NULL,
  `dicom_series_instance_uid` varchar(64) DEFAULT NULL,
  `hl7_message_control_id` varchar(32) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`report_id`),
  UNIQUE KEY `report_number` (`report_number`),
  KEY `fk_report_imaging_study` (`imaging_study_id`),
  KEY `fk_report_author` (`author_provider_id`),
  KEY `idx_report_sop_uid` (`dicom_sop_instance_uid`),
  CONSTRAINT `fk_report_author` FOREIGN KEY (`author_provider_id`) REFERENCES `providers` (`provider_id`),
  CONSTRAINT `fk_report_imaging_study` FOREIGN KEY (`imaging_study_id`) REFERENCES `imaging_studies` (`imaging_study_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- DICOM MWL/MPPS integration tables
DROP TABLE IF EXISTS mpps;
DROP TABLE IF EXISTS mwl;
DROP TABLE IF EXISTS mwl_tasks;
CREATE TABLE mwl (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  completed TINYINT(1) NOT NULL DEFAULT 0,
  AccessionNumber VARCHAR(32) UNIQUE,
  StudyInstanceUID VARCHAR(64),
  PatientID VARCHAR(32),
  PatientName VARCHAR(128),
  ScheduledProcedureStepStartDate VARCHAR(8),
  ScheduledStationAETitle VARCHAR(16),
  Dataset LONGBLOB,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_mwl_accession (AccessionNumber),
  INDEX idx_mwl_study_uid (StudyInstanceUID),
  INDEX idx_mwl_patient (PatientID),
  INDEX idx_mwl_completed (completed),
  INDEX idx_mwl_sps_date (ScheduledProcedureStepStartDate),
  INDEX idx_mwl_station (ScheduledStationAETitle)
) ENGINE=InnoDB;

CREATE TABLE mpps (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  sop_instance_uid VARCHAR(64) NOT NULL,
  mwl_id INT UNSIGNED,
  AccessionNumber VARCHAR(32),
  StudyInstanceUID VARCHAR(64),
  PatientID VARCHAR(32),
  status ENUM('IN_PROGRESS','COMPLETED','DISCONTINUED') DEFAULT 'IN_PROGRESS',
  performed_procedure_step_id VARCHAR(32),
  performed_station_ae_title VARCHAR(16),
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  dataset_blob LONGBLOB,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY idx_mpps_sop_uid (sop_instance_uid),
  INDEX idx_mpps_mwl (mwl_id),
  INDEX idx_mpps_accession (AccessionNumber),
  INDEX idx_mpps_study_uid (StudyInstanceUID),
  INDEX idx_mpps_patient (PatientID),
  INDEX idx_mpps_status (status),
  INDEX idx_mpps_station (performed_station_ae_title),
  CONSTRAINT fk_mpps_mwl FOREIGN KEY (mwl_id) REFERENCES mwl(id) ON DELETE SET NULL
) ENGINE=InnoDB;

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

-- Essential DICOM tags for MWL and MPPS (subset of ~50 most common tags)
INSERT INTO dicom_tags (id, tag, tag_group, element, vr, name, vm, version) VALUES
  (1,'(0008,0005)','0008','0005','CS','SpecificCharacterSet','1-n','DICOM'),
  (2,'(0008,0008)','0008','0008','CS','ImageType','2-n','DICOM'),
  (3,'(0008,0016)','0008','0016','UI','SOPClassUID','1','DICOM'),
  (4,'(0008,0018)','0008','0018','UI','SOPInstanceUID','1','DICOM'),
  (5,'(0008,0020)','0008','0020','DA','StudyDate','1','DICOM'),
  (6,'(0008,0021)','0008','0021','DA','SeriesDate','1','DICOM'),
  (7,'(0008,0030)','0008','0030','TM','StudyTime','1','DICOM'),
  (8,'(0008,0031)','0008','0031','TM','SeriesTime','1','DICOM'),
  (9,'(0008,0050)','0008','0050','SH','AccessionNumber','1','DICOM'),
  (10,'(0008,0060)','0008','0060','CS','Modality','1','DICOM'),
  (11,'(0008,0070)','0008','0070','LO','Manufacturer','1','DICOM'),
  (12,'(0008,0080)','0008','0080','LO','InstitutionName','1','DICOM'),
  (13,'(0008,0090)','0008','0090','PN','ReferringPhysicianName','1','DICOM'),
  (14,'(0008,1030)','0008','1030','LO','StudyDescription','1','DICOM'),
  (15,'(0008,103E)','0008','103E','LO','SeriesDescription','1','DICOM'),
  (16,'(0008,1090)','0008','1090','LO','ManufacturerModelName','1','DICOM'),
  (17,'(0010,0010)','0010','0010','PN','PatientName','1','DICOM'),
  (18,'(0010,0020)','0010','0020','LO','PatientID','1','DICOM'),
  (19,'(0010,0030)','0010','0030','DA','PatientBirthDate','1','DICOM'),
  (20,'(0010,0040)','0010','0040','CS','PatientSex','1','DICOM'),
  (21,'(0018,0015)','0018','0015','CS','BodyPartExamined','1','DICOM'),
  (22,'(0018,1030)','0018','1030','LO','ProtocolName','1','DICOM'),
  (23,'(0020,000D)','0020','000D','UI','StudyInstanceUID','1','DICOM'),
  (24,'(0020,000E)','0020','000E','UI','SeriesInstanceUID','1','DICOM'),
  (25,'(0020,0010)','0020','0010','SH','StudyID','1','DICOM'),
  (26,'(0020,0011)','0020','0011','IS','SeriesNumber','1','DICOM'),
  (27,'(0020,0013)','0020','0013','IS','InstanceNumber','1','DICOM'),
  (28,'(0032,1032)','0032','1032','PN','RequestingPhysician','1','DICOM'),
  (29,'(0032,1033)','0032','1033','LO','RequestingService','1','DICOM'),
  (30,'(0032,1060)','0032','1060','LO','RequestedProcedureDescription','1','DICOM'),
  (31,'(0040,0100)','0040','0100','SQ','ScheduledProcedureStepSequence','1','DICOM'),
  (32,'(0040,0001)','0040','0001','AE','ScheduledStationAETitle','1','DICOM'),
  (33,'(0040,0002)','0040','0002','DA','ScheduledProcedureStepStartDate','1','DICOM'),
  (34,'(0040,0003)','0040','0003','TM','ScheduledProcedureStepStartTime','1','DICOM'),
  (35,'(0040,0006)','0040','0006','PN','ScheduledPerformingPhysicianName','1','DICOM'),
  (36,'(0040,0007)','0040','0007','LO','ScheduledProcedureStepDescription','1','DICOM'),
  (37,'(0040,0009)','0040','0009','SH','ScheduledProcedureStepID','1','DICOM'),
  (38,'(0040,0010)','0040','0010','SH','ScheduledStationName','1','DICOM'),
  (39,'(0040,1001)','0040','1001','SH','RequestedProcedureID','1','DICOM'),
  (40,'(0040,0400)','0040','0400','LT','CommentsOnScheduledProcedureStep','1','DICOM'),
  (41,'(0040,0244)','0040','0244','DA','PerformedProcedureStepStartDate','1','DICOM'),
  (42,'(0040,0245)','0040','0245','TM','PerformedProcedureStepStartTime','1','DICOM'),
  (43,'(0040,0250)','0040','0250','DA','PerformedProcedureStepEndDate','1','DICOM'),
  (44,'(0040,0251)','0040','0251','TM','PerformedProcedureStepEndTime','1','DICOM'),
  (45,'(0040,0252)','0040','0252','CS','PerformedProcedureStepStatus','1','DICOM'),
  (46,'(0040,0253)','0040','0253','SH','PerformedProcedureStepID','1','DICOM'),
  (47,'(0040,0254)','0040','0254','LO','PerformedProcedureStepDescription','1','DICOM'),
  (48,'(0040,0260)','0040','0260','SQ','PerformedProtocolCodeSequence','1','DICOM'),
  (49,'(0040,0270)','0040','0270','SQ','ScheduledStepAttributesSequence','1','DICOM'),
  (50,'(0040,A040)','0040','A040','CS','PerformedProcedureStepTypeCode','1','DICOM')
ON DUPLICATE KEY UPDATE name = VALUES(name);

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

-- CR/XR Procedures (balanced set for single-image studies)
-- Focused on common radiography exams with typical 1-2 image acquisitions
INSERT INTO procedures (procedure_code, procedure_name, modality_code, body_part_code, typical_views, typical_image_count, description) VALUES
  ('CR_CHEST_1V', 'Chest X-Ray 1 View', 'CR', 'CHEST', 'PA or AP', 1, 'Single view chest radiograph, typically PA'),
  ('CR_CHEST_2V', 'Chest X-Ray 2 Views', 'CR', 'CHEST', 'PA and Lateral', 2, 'Standard two-view chest radiograph'),
  ('CR_ABD_1V', 'Abdomen X-Ray 1 View', 'CR', 'ABD', 'AP Supine', 1, 'Single supine abdominal radiograph'),
  ('CR_ABD_2V', 'Abdomen X-Ray 2 Views', 'CR', 'ABD', 'AP Supine and Erect', 2, 'Two-view abdomen for obstruction series'),
  ('CR_PELV_1V', 'Pelvis X-Ray 1 View', 'CR', 'PELV', 'AP', 1, 'Standard AP pelvis radiograph'),
  ('CR_SPINE_C_2V', 'Cervical Spine 2 Views', 'CR', 'SPINE', 'AP and Lateral', 2, 'Two-view cervical spine series'),
  ('CR_SPINE_L_2V', 'Lumbar Spine 2 Views', 'CR', 'SPINE', 'AP and Lateral', 2, 'Two-view lumbar spine series'),
  ('CR_HAND_2V', 'Hand X-Ray 2 Views', 'CR', 'EXT_UP', 'PA and Oblique', 2, 'Two-view hand radiograph'),
  ('CR_WRIST_2V', 'Wrist X-Ray 2 Views', 'CR', 'EXT_UP', 'PA and Lateral', 2, 'Two-view wrist radiograph'),
  ('CR_SHOULDER_2V', 'Shoulder X-Ray 2 Views', 'CR', 'EXT_UP', 'AP and Y-View', 2, 'Two-view shoulder radiograph'),
  ('CR_KNEE_2V', 'Knee X-Ray 2 Views', 'CR', 'EXT_LOW', 'AP and Lateral', 2, 'Two-view knee radiograph'),
  ('CR_ANKLE_2V', 'Ankle X-Ray 2 Views', 'CR', 'EXT_LOW', 'AP and Lateral', 2, 'Two-view ankle radiograph'),
  ('CR_FOOT_2V', 'Foot X-Ray 2 Views', 'CR', 'EXT_LOW', 'AP and Oblique', 2, 'Two-view foot radiograph'),
  ('CR_SKULL_2V', 'Skull X-Ray 2 Views', 'CR', 'HEAD', 'AP and Lateral', 2, 'Two-view skull radiograph')
ON DUPLICATE KEY UPDATE procedure_name = VALUES(procedure_name);

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
  ('ORD-2025-0001', 'ACC-2025-0001', 1, 1, 1, 3, 'CR', 'CHEST', 'R07.9', 'Chest pain evaluation',
   'URGENT', 'Scheduled', '2025-06-01 08:45:00', '2025-06-01 09:15:00', 'Possible pneumonia', NULL, 'NW'),
  ('ORD-2025-0002', 'ACC-2025-0002', 2, 2, 1, 3, 'CR', 'ABD', 'R10.9', 'Abdominal pain',
   'ROUTINE', 'Requested', '2025-06-02 08:15:00', '2025-06-02 10:00:00', 'Rule out obstruction', NULL, 'NW'),
  ('ORD-2025-0003', 'ACC-2025-0003', 3, NULL, 1, 3, 'CR', 'EXT_LOW', 'M25.561', 'Knee pain',
   'ROUTINE', 'Requested', '2025-06-03 10:00:00', '2025-06-03 14:00:00', 'Evaluate for fracture', NULL, 'NW')
ON DUPLICATE KEY UPDATE status = VALUES(status);

INSERT INTO order_procedures (order_id, procedure_code, procedure_description, laterality)
VALUES
  (1, 'CR_CHEST_2V', 'Chest X-Ray 2 Views', 'Unspecified'),
  (2, 'CR_ABD_1V', 'Abdomen X-Ray 1 View', 'Unspecified'),
  (3, 'CR_KNEE_2V', 'Knee X-Ray 2 Views', 'Right')
ON DUPLICATE KEY UPDATE procedure_description = VALUES(procedure_description);

-- Imaging studies and reports are now created dynamically through the workflow:
-- 1. create_synthetic_cr_study() creates imaging_studies records when studies are sent to PACS
-- 2. create_radiology_report() creates reports after studies are available

INSERT INTO mwl_tasks (
  order_id, scheduled_station_aet, scheduled_station_name, scheduled_start,
  scheduled_end, scheduled_performing_provider_id, status, mwl_payload
) VALUES
  (1, 'ORTHANC', 'CR Room 1', '2025-06-01 09:15:00', '2025-06-01 09:30:00', 3, 'Completed',
   JSON_OBJECT(
     'PatientID', 'MRN1001',
     'PatientName', 'Johnson^Alex',
     'PatientBirthDate', '19840312',
     'PatientSex', 'M',
     'AccessionNumber', 'ACC-2025-0001',
     'RequestedProcedureDescription', 'Chest X-Ray 2 Views',
     'RequestedProcedureID', 'ORD-2025-0001',
     'StudyInstanceUID', '1.2.826.0.1.3680043.8.498.59676346561651051188898732525991691632',
     'ScheduledProcedureStepSequence', JSON_ARRAY(
       JSON_OBJECT(
         'Modality', 'CR',
         'ScheduledStationAETitle', 'ORTHANC',
         'ScheduledProcedureStepStartDate', '20250601',
         'ScheduledProcedureStepStartTime', '091500',
         'ScheduledProcedureStepDescription', 'Chest X-Ray 2 Views',
         'ScheduledProcedureStepID', 'SPS1',
         'ScheduledPerformingPhysicianName', 'Wells^Casey'
       )
     )
   )),
  (2, 'ORTHANC', 'CR Room 1', '2025-06-02 10:00:00', '2025-06-02 10:10:00', 3, 'Completed',
   JSON_OBJECT(
     'PatientID', 'MRN1002',
     'PatientName', 'Lopez^Maria',
     'PatientBirthDate', '19761105',
     'PatientSex', 'F',
     'AccessionNumber', 'ACC-2025-0002',
     'RequestedProcedureDescription', 'Abdomen X-Ray 1 View',
     'RequestedProcedureID', 'ORD-2025-0002',
     'StudyInstanceUID', '1.2.826.0.1.3680043.8.498.12345678901234567890123456789012',
     'ScheduledProcedureStepSequence', JSON_ARRAY(
       JSON_OBJECT(
         'Modality', 'CR',
         'ScheduledStationAETitle', 'ORTHANC',
         'ScheduledProcedureStepStartDate', '20250602',
         'ScheduledProcedureStepStartTime', '100000',
         'ScheduledProcedureStepDescription', 'Abdomen X-Ray 1 View',
         'ScheduledProcedureStepID', 'SPS2',
         'ScheduledPerformingPhysicianName', 'Wells^Casey'
       )
     )
   )),
  (3, 'ORTHANC', 'CR Room 2', '2025-06-03 14:00:00', '2025-06-03 14:15:00', 3, 'Scheduled',
   JSON_OBJECT(
     'PatientID', 'MRN1003',
     'PatientName', 'Nguyen^Sam',
     'PatientBirthDate', '19920721',
     'PatientSex', 'O',
     'AccessionNumber', 'ACC-2025-0003',
     'RequestedProcedureDescription', 'Knee X-Ray 2 Views',
     'RequestedProcedureID', 'ORD-2025-0003',
     'StudyInstanceUID', '1.2.826.0.1.3680043.8.498.98765432109876543210987654321098',
     'ScheduledProcedureStepSequence', JSON_ARRAY(
       JSON_OBJECT(
         'Modality', 'CR',
         'ScheduledStationAETitle', 'ORTHANC',
         'ScheduledProcedureStepStartDate', '20250603',
         'ScheduledProcedureStepStartTime', '140000',
         'ScheduledProcedureStepDescription', 'Knee X-Ray 2 Views',
         'ScheduledProcedureStepID', 'SPS3',
         'ScheduledPerformingPhysicianName', 'Wells^Casey'
       )
     )
   ))
ON DUPLICATE KEY UPDATE status = VALUES(status);

-- -----------------------------------------------------------------------------
-- End of mini-RIS schema
-- -----------------------------------------------------------------------------

