-- Hand-built rows shaped exactly like the SQL-on-FHIR view outputs. Period end = 2026-09-30.
create table dcg_patient (patient_id varchar, birth_date date, administrative_gender varchar, deceased_datetime timestamp, deceased_flag boolean, province varchar, fsa varchar,
  service_language varchar, indigenous_identity varchar, racialized_group varchar);
insert into dcg_patient values
 ('P1','1966-05-01','female',null,null,'ON','K1A','en',null,null),   -- T2, 60: everything done
 ('P2','1956-02-01','male',  null,null,'ON','K2B','fr',null,null),   -- T2, 70: all gaps
 ('P3','1996-03-01','female',null,null,'BC','V5K',null,null,null),   -- T1, 30: A1C 7.0 at target, little else
 ('P4','1970-01-01','male',  null,null,'ON','K1A',null,null,null),   -- prediabetes only: not in cohort
 ('P5','1981-04-01','male',  null,null,'BC','V6B',null,null,null),   -- T2, 45: A1C in mmol/mol (DQ), on statin + retinopathy
 ('P6','2010-01-01','female',null,null,'ON','K1A',null,null,null),   -- T1, 16: excluded (age)
 ('P7','1950-01-01','male','2025-12-01',null,'ON','K1A',null,null,null), -- T2, deceased: excluded
 ('P8','1990-01-01','female',null,null,'ON','K1A',null,null,null),   -- adult, no diabetes
 ('P9','1960-01-01','male',  null,null,'AB','T2P',null,null,null),   -- v0.4: hospital ICD-10-CA E11 only; DKA emergency visit
 ('P10','1975-06-01','female',null,null,'ON','M5V',null,null,null),  -- v0.4: 2 ambulatory E11 claims; lab CKD; SGLT2i dispense
 ('P11','1985-03-01','male',  null,null,'QC','H3B',null,null,null),  -- v0.4: lab route only (2 A1C >= 6.5); semaglutide
 ('P12','1980-01-01','male',  null,null,'ON','K1A',null,null,null),  -- v0.4: metformin dispense only -> possible case, not in cohort
 ('P13','1992-01-01','female',null,null,'BC','V6B',null,null,null);  -- v0.4: GDM; A1C >= 6.5 inside GDM window -> not in cohort
create table dcg_condition (condition_id varchar, patient_id varchar, encounter_id varchar, clinical_status varchar, verification_status varchar,
  condition_category varchar, onset_datetime timestamp, abatement_datetime timestamp, recorded_date timestamp, snomed_code varchar, code_display varchar, icd10ca_code varchar);
insert into dcg_condition values
 ('C1','P1',null,'active','confirmed','problem-list-item','2015-01-01',null,null,'44054006','T2DM',null),
 ('C2','P2',null,'active','confirmed','problem-list-item','2010-01-01',null,null,'44054006','T2DM',null),
 ('C2b','P2',null,'active','confirmed','problem-list-item','2012-05-01',null,null,'44054006','T2DM (duplicate record)',null),
 ('C3','P3',null,'active','confirmed','problem-list-item','2005-01-01',null,null,'46635009','T1DM',null),
 ('C4','P4',null,'active','confirmed','problem-list-item','2020-01-01',null,null,'15777000','Prediabetes',null),
 ('C5','P5',null,'active','confirmed','problem-list-item','2022-01-01',null,null,'44054006','T2DM',null),
 ('C5b','P5',null,'active','confirmed','problem-list-item','2024-01-01',null,null,'422034002','Retinopathy T2',null),
 ('C6','P6',null,'active','confirmed','problem-list-item','2020-01-01',null,null,'46635009','T1DM',null),
 ('C7','P7',null,'active','confirmed','problem-list-item','2000-01-01',null,null,'44054006','T2DM',null),
 ('C2c','P2',null,'active','confirmed','problem-list-item','2023-01-01',null,null,'22298006','Myocardial infarction',null),
 ('C9','P9','E9a','active','confirmed','encounter-diagnosis','2024-03-10',null,null,null,'T2DM (hospital)','E11.9'),
 ('C9b','P9','E9b','resolved','confirmed','encounter-diagnosis','2026-03-05',null,null,null,'T2DM with ketoacidosis','E11.10'),
 ('C10a','P10','E10a','active','confirmed','encounter-diagnosis','2025-01-15',null,null,null,'T2DM (claim 1)','E11.9'),
 ('C10b','P10','E10b','active','confirmed','encounter-diagnosis','2025-11-20',null,null,null,'T2DM (claim 2)','E11.9'),
 ('C13','P13',null,'resolved','confirmed','problem-list-item','2025-06-01',null,null,'11687002','Gestational diabetes',null);
create table dcg_observation (observation_id varchar, patient_id varchar, status varchar, category varchar, effective_datetime timestamp,
  value_numeric double, ucum_unit varchar, loinc_code varchar, code_display varchar);
insert into dcg_observation values
 ('O1','P1','final','laboratory','2026-07-01',6.8,'%','4548-4','A1C'),
 ('O2','P1','final','laboratory','2026-03-01',85,'mL/min/{1.73_m2}','33914-3','eGFR'),
 ('O3','P1','final','laboratory','2026-03-01',1.2,'mg/g','14959-1','UACR'),
 ('O4','P1','final','laboratory','2026-03-01',2.1,'mmol/L','18262-6','LDL'),
 ('O5','P2','final','laboratory','2026-01-15',8.5,'%','4548-4','A1C'),
 ('O6','P3','final','laboratory','2026-09-01',7.0,'%','4548-4','A1C'),
 ('O7','P5','final','laboratory','2026-05-01',53,'mmol/mol','4548-4','A1C IFCC unit'),
 ('O8','P1','final','vital-signs','2026-08-01',27.4,'kg/m2','39156-5','BMI'),
 ('O9','P2','final','vital-signs','2026-08-01',31.2,'kg/m2','39156-5','BMI'),
 ('O10','P5','final','vital-signs','2026-02-01',150,'kg/m2','39156-5','BMI implausible (excluded)'),
 ('O11','P10','final','laboratory','2025-12-01',50,'mL/min/{1.73_m2}','62238-1','eGFR'),
 ('O12','P10','final','laboratory','2026-06-01',45,'mL/min/{1.73_m2}','62238-1','eGFR'),
 ('O13','P10','final','laboratory','2026-06-01',8.2,'%','4548-4','A1C'),
 ('O18','P10','final','laboratory','2026-06-01',100,'mg/dL','2089-1','LDL mass units (converted)'),
 ('O14','P11','final','laboratory','2026-02-01',7.2,'%','4548-4','A1C'),
 ('O15','P11','final','laboratory','2026-06-01',7.2,'%','4548-4','A1C'),
 ('O16','P13','final','laboratory','2025-07-01',6.8,'%','4548-4','A1C in GDM window'),
 ('O17','P13','final','laboratory','2025-08-01',6.8,'%','4548-4','A1C in GDM window'),
 ('O19','P9','final','laboratory','2025-12-01',7.5,null,'4548-4','A1C with no unit (DQ + stewardship)');
create table dcg_blood_pressure (observation_id varchar, patient_id varchar, effective_datetime timestamp, systolic double, diastolic double);
insert into dcg_blood_pressure values ('B1','P1','2026-08-01',120,75), ('B2','P2','2026-08-01',140,85), ('B5','P5','2026-02-01',135,82),
 ('B10','P10','2026-06-01',128,78), ('B11','P11','2026-06-01',150,95), ('B99','P11','2026-07-01',400,95);  -- B99 implausible: ignored
create table dcg_procedure (procedure_id varchar, patient_id varchar, status varchar, performed_datetime timestamp, snomed_code varchar, code_display varchar);
insert into dcg_procedure values ('PR1','P1','completed','2025-06-01','36228007','Eye exam'), ('PR2','P1','completed','2026-01-10','401191002','Foot exam');
create table dcg_medication_request (medication_request_id varchar, patient_id varchar, status varchar, intent varchar, authored_on timestamp,
  med_code_system varchar, med_code varchar, med_display varchar, med_text varchar, atc_code varchar);
insert into dcg_medication_request values
 ('M1','P1','active','order','2026-01-01','http://www.nlm.nih.gov/research/umls/rxnorm','617310','atorvastatin 20 MG Oral Tablet', null, null),
 ('M2','P1','active','order','2026-01-01','http://www.nlm.nih.gov/research/umls/rxnorm','860975','24 HR Metformin hydrochloride 500 MG Extended Release Oral Tablet', null, null),
 ('M5','P5','stopped','order','2026-02-01','http://www.nlm.nih.gov/research/umls/rxnorm','859747','rosuvastatin calcium 10 MG Oral Tablet', null, null),
 ('M6','P1','active','order','2026-01-01','http://www.nlm.nih.gov/research/umls/rxnorm','314076','lisinopril 10 MG Oral Tablet', null, null),
 ('M7','P2','active','order','2026-03-01',null,null,null,'insulin glargine 100 units/mL', 'A10AE04'),
 ('M8','P3','active','order','2025-06-01',null,null,null,'Insulin pen (basal)', null),
 ('M9','P11','active','order','2026-01-01',null,null,null,'semaglutide 1 mg/dose pen', null),
 ('M10','P1','active','order','2026-01-01','http://www.nlm.nih.gov/research/umls/rxnorm','313782','Acetaminophen 325 MG Oral Tablet', null, null);  -- unclassified: stewardship queue
create table dcg_medication_dispense (medication_dispense_id varchar, patient_id varchar, status varchar, when_handed_over timestamp, days_supply double,
  med_text varchar, atc_code varchar, med_code_system varchar, med_code varchar, med_display varchar);
insert into dcg_medication_dispense values
 ('D1','P10','completed','2026-07-01',90,'Jardiance 10 mg', 'A10BK03', null, null, null),
 ('D2','P12','completed','2026-05-01',90,'metformin 500 mg', 'A10BA02', null, null, null),
 ('D3','P9','completed','2026-04-01',30,'Basal insulin pen', 'A10AE04', null, null, null);
create table dcg_encounter (encounter_id varchar, patient_id varchar, status varchar, encounter_class varchar, period_start timestamp, period_end timestamp);
insert into dcg_encounter values
 ('E9a','P9','finished','IMP','2024-03-08','2024-03-12'),
 ('E9b','P9','finished','EMER','2026-03-05','2026-03-05'),
 ('E10a','P10','finished','AMB','2025-01-15','2025-01-15'),
 ('E10b','P10','finished','AMB','2025-11-20','2025-11-20');
