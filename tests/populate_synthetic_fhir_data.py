#!/usr/bin/env python3
"""
Populate local HAPI FHIR server with synthetic data for testing orchestration workflows.

This script creates:
- Patients with realistic demographics
- ServiceRequests (orders) for radiology studies
- ImagingStudies linked to patients and orders
- DiagnosticReports with findings

Usage:
    python tests/populate_synthetic_fhir_data.py
    
Requirements:
    - Local HAPI FHIR server running (docker-compose -f tests/docker-compose-fhir.yaml up -d)
    - httpx installed (pip install httpx)
"""

import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import uuid


FHIR_BASE_URL = "http://localhost:8080/fhir"
HEADERS = {
    "Accept": "application/fhir+json",
    "Content-Type": "application/fhir+json"
}


def create_patient(mrn: str, name: Dict[str, str], birthdate: str, gender: str) -> Dict[str, Any]:
    """Create a FHIR Patient resource."""
    return {
        "resourceType": "Patient",
        "id": f"patient-{mrn.lower()}",
        "identifier": [
            {
                "system": "http://hospital.example.org/mrn",
                "value": mrn
            }
        ],
        "name": [
            {
                "family": name["family"],
                "given": name["given"]
            }
        ],
        "birthDate": birthdate,
        "gender": gender
    }


def create_service_request(patient_id: str, order_id: str, study_description: str, 
                          modality: str, requested_date: str) -> Dict[str, Any]:
    """Create a FHIR ServiceRequest (order) for an imaging study."""
    return {
        "resourceType": "ServiceRequest",
        "id": f"order-{order_id}",
        "status": "active",
        "intent": "order",
        "code": {
            "coding": [
                {
                    "system": "http://www.radlex.org",
                    "code": "RID10318" if modality == "CT" else "RID10319",
                    "display": study_description
                }
            ],
            "text": study_description
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "occurrenceDateTime": requested_date,
        "authoredOn": requested_date
        # Note: requester field removed - HAPI FHIR validates references and requires
        # the Practitioner resource to exist. Can be added later if needed.
    }


def create_imaging_study(patient_id: str, study_instance_uid: str, 
                        modality: str, study_date: str, 
                        series_count: int = 1) -> Dict[str, Any]:
    """Create a FHIR ImagingStudy resource."""
    series = []
    for i in range(1, series_count + 1):
        series.append({
            "uid": f"{study_instance_uid}.{i}",
            "number": i,
            "modality": {
                "code": modality,
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "display": modality
            },
            "numberOfInstances": 100 if modality == "CT" else 200
        })
    
    return {
        "resourceType": "ImagingStudy",
        "id": f"study-{study_instance_uid}",
        "status": "available",
        "modality": [
            {
                "code": modality,
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "display": modality
            }
        ],
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "started": study_date,
        "series": series
    }


def create_diagnostic_report(patient_id: str, imaging_study_id: str, 
                            report_text: str, report_date: str) -> Dict[str, Any]:
    """Create a FHIR DiagnosticReport."""
    return {
        "resourceType": "DiagnosticReport",
        "id": f"report-{imaging_study_id}",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "RAD",
                        "display": "Radiology"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "18726-0",
                    "display": "Radiology report"
                }
            ]
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": report_date,
        "issued": report_date,
        # Note: performer field removed - HAPI FHIR validates references and requires
        # the Practitioner resource to exist. Can be added later if needed.
        "imagingStudy": [
            {
                "reference": f"ImagingStudy/{imaging_study_id}"
            }
        ],
        "conclusion": report_text
    }


def post_resource(resource: Dict[str, Any], client: httpx.Client) -> Dict[str, Any]:
    """Post a FHIR resource to the server."""
    resource_type = resource["resourceType"]
    resource_id = resource.get("id")
    
    url = f"{FHIR_BASE_URL}/{resource_type}"
    if resource_id:
        url = f"{url}/{resource_id}"
    
    response = client.put(url, headers=HEADERS, json=resource)
    response.raise_for_status()
    return response.json()


def main():
    """Main function to populate synthetic data."""
    print("Populating synthetic FHIR data...")
    print(f"Target: {FHIR_BASE_URL}\n")
    
    # Synthetic patients with realistic data
    patients_data = [
        {
            "mrn": "MRN001",
            "name": {"family": "Smith", "given": ["John", "Robert"]},
            "birthdate": "1985-03-15",
            "gender": "male"
        },
        {
            "mrn": "MRN002",
            "name": {"family": "Johnson", "given": ["Sarah", "Marie"]},
            "birthdate": "1992-07-22",
            "gender": "female"
        },
        {
            "mrn": "MRN003",
            "name": {"family": "Williams", "given": ["Michael"]},
            "birthdate": "1978-11-08",
            "gender": "male"
        },
        {
            "mrn": "MRN004",
            "name": {"family": "Brown", "given": ["Emily", "Anne"]},
            "birthdate": "1995-02-14",
            "gender": "female"
        },
        {
            "mrn": "MRN005",
            "name": {"family": "Davis", "given": ["David", "James"]},
            "birthdate": "1989-09-30",
            "gender": "male"
        }
    ]
    
    # Generate study dates (some in past, some recent)
    base_date = datetime.now()
    study_dates = [
        (base_date - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
        (base_date - timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%S"),
        (base_date - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
        base_date.strftime("%Y-%m-%dT%H:%M:%S"),
        (base_date + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
    ]
    
    with httpx.Client(timeout=30.0, verify=False) as client:
        created_resources = {
            "patients": [],
            "service_requests": [],
            "imaging_studies": [],
            "diagnostic_reports": []
        }
        
        # Create patients
        print("Creating patients...")
        for patient_data in patients_data:
            patient = create_patient(**patient_data)
            result = post_resource(patient, client)
            created_resources["patients"].append(result)
            print(f"  ✓ Created Patient: {patient_data['name']['family']}, {patient_data['name']['given'][0]} (MRN: {patient_data['mrn']})")
        
        print()
        
        # Create ServiceRequests and ImagingStudies for each patient
        print("Creating orders and imaging studies...")
        study_counter = 1
        
        for i, patient in enumerate(created_resources["patients"]):
            patient_id = patient["id"]
            study_date = study_dates[i % len(study_dates)]
            
            # Create ServiceRequest (order)
            order_id = f"ORD{study_counter:03d}"
            service_request = create_service_request(
                patient_id=patient_id,
                order_id=order_id,
                study_description="Chest X-Ray PA" if i % 2 == 0 else "Chest CT",
                modality="CR" if i % 2 == 0 else "CT",
                requested_date=study_date
            )
            result = post_resource(service_request, client)
            created_resources["service_requests"].append(result)
            print(f"  ✓ Created ServiceRequest: {order_id} for Patient {patient_id}")
            
            # Create ImagingStudy
            study_instance_uid = f"1.2.840.113619.2.55.3.1234567890.{study_counter}"
            imaging_study = create_imaging_study(
                patient_id=patient_id,
                study_instance_uid=study_instance_uid,
                modality="CR" if i % 2 == 0 else "CT",
                study_date=study_date,
                series_count=2 if i % 2 == 0 else 1
            )
            result = post_resource(imaging_study, client)
            created_resources["imaging_studies"].append(result)
            print(f"  ✓ Created ImagingStudy: {study_instance_uid} for Patient {patient_id}")
            
            # Create DiagnosticReport for completed studies (skip future ones)
            if i < len(study_dates) - 1:  # Don't create reports for future studies
                report_text = f"Normal {imaging_study['modality'][0]['display']} examination. No acute abnormalities."
                diagnostic_report = create_diagnostic_report(
                    patient_id=patient_id,
                    imaging_study_id=imaging_study["id"],
                    report_text=report_text,
                    report_date=(datetime.fromisoformat(study_date.replace("Z", "+00:00")) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
                )
                result = post_resource(diagnostic_report, client)
                created_resources["diagnostic_reports"].append(result)
                print(f"  ✓ Created DiagnosticReport for ImagingStudy {imaging_study['id']}")
            
            study_counter += 1
            print()
        
        # Summary
        print("=" * 60)
        print("Synthetic data population complete!")
        print(f"  Patients: {len(created_resources['patients'])}")
        print(f"  ServiceRequests: {len(created_resources['service_requests'])}")
        print(f"  ImagingStudies: {len(created_resources['imaging_studies'])}")
        print(f"  DiagnosticReports: {len(created_resources['diagnostic_reports'])}")
        print()
        print("You can now test FHIR workflows with this data.")
        print(f"Example: Search for patients at {FHIR_BASE_URL}/Patient")


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print(f"ERROR: Could not connect to {FHIR_BASE_URL}")
        print("Make sure HAPI FHIR server is running:")
        print("  docker-compose -f tests/docker-compose-fhir.yaml up -d")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

