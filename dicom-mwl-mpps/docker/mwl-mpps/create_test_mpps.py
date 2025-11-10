#!/usr/bin/env python3
"""
Script to create properly formatted test MPPS DICOM files and test them via pynetdicom
"""

from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import (
    ExplicitVRLittleEndian,
    generate_uid,
    PYDICOM_IMPLEMENTATION_UID
)
from pydicom import dcmwrite
from datetime import datetime, date
import os

# Import the correct SOP Class UID from pynetdicom
try:
    from pynetdicom.sop_class import ModalityPerformedProcedureStep
    MPPS_SOP_CLASS_UID = ModalityPerformedProcedureStep
except ImportError:
    MPPS_SOP_CLASS_UID = "1.2.840.10008.3.1.2.3.3"

def create_mpps_create_file(sop_instance_uid):
    """Create MPPS N-CREATE test file with specified SOP Instance UID"""
    
    # Create the main dataset
    ds = Dataset()
    
    # File Meta Information
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 0
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = MPPS_SOP_CLASS_UID
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = PYDICOM_IMPLEMENTATION_UID
    file_meta.ImplementationVersionName = "PYDICOM"
    
    # Set file meta information
    ds.file_meta = file_meta
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    
    # SOP Class and Instance
    ds.SOPClassUID = MPPS_SOP_CLASS_UID
    ds.SOPInstanceUID = sop_instance_uid
    
    # Patient Information (matches the README JSON example exactly)
    ds.PatientName = "DOE^JOHN"
    ds.PatientID = "P1"
    ds.PatientBirthDate = "19800101"
    ds.PatientSex = "M"
    
    # Study Information (matches the README JSON example exactly)
    ds.StudyInstanceUID = "1.2.3.4.5"
    ds.AccessionNumber = "TEST123"
    
    # Performed Procedure Step Information
    ds.PerformedProcedureStepID = "PPS001"
    ds.PerformedProcedureStepStatus = "IN PROGRESS"
    ds.PerformedProcedureStepStartDate = date.today().strftime("%Y%m%d")
    ds.PerformedProcedureStepStartTime = datetime.now().strftime("%H%M%S")
    
    # Modality and Station Info
    ds.Modality = "CT"
    ds.PerformedStationAETitle = "ORTHANC"
    ds.PerformedStationName = "CT_SCANNER_01"
    
    # Performed Procedure Step Description
    ds.PerformedProcedureStepDescription = "Chest CT Scan"
    
    # Performed Protocol Code Sequence
    protocol_item = Dataset()
    protocol_item.CodeValue = "CHEST_CT"
    protocol_item.CodingSchemeDesignator = "LOCAL"
    protocol_item.CodeMeaning = "Chest CT Protocol"
    ds.PerformedProtocolCodeSequence = [protocol_item]
    
    # Scheduled Step Attributes Sequence (links back to the MWL entry)
    sched_step_item = Dataset()
    sched_step_item.StudyInstanceUID = ds.StudyInstanceUID
    sched_step_item.AccessionNumber = ds.AccessionNumber
    sched_step_item.RequestedProcedureID = "REQ001"
    sched_step_item.ScheduledProcedureStepID = "SPS001"
    sched_step_item.ScheduledProcedureStepStartDate = "20240625"
    sched_step_item.ScheduledStationAETitle = "ORTHANC"
    ds.ScheduledStepAttributesSequence = [sched_step_item]
    
    return ds

def create_mpps_set_file(sop_instance_uid):
    """Create MPPS N-SET test file with specified SOP Instance UID"""
    
    # Create the main dataset
    ds = Dataset()
    
    # File Meta Information
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 0
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = MPPS_SOP_CLASS_UID
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = PYDICOM_IMPLEMENTATION_UID
    file_meta.ImplementationVersionName = "PYDICOM"
    
    # Set file meta information
    ds.file_meta = file_meta
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    
    # SOP Class and Instance
    ds.SOPClassUID = MPPS_SOP_CLASS_UID
    ds.SOPInstanceUID = sop_instance_uid
    
    # Performed Procedure Step Status (completion)
    ds.PerformedProcedureStepStatus = "COMPLETED"
    ds.PerformedProcedureStepEndDate = date.today().strftime("%Y%m%d")
    ds.PerformedProcedureStepEndTime = datetime.now().strftime("%H%M%S")
    
    # Performed Series Sequence (images that were acquired)
    series_item = Dataset()
    series_item.SeriesInstanceUID = generate_uid()
    series_item.SeriesDescription = "Chest CT Images"
    series_item.Modality = "CT"
    series_item.OperatorsName = "TECH^JOHN"
    
    # Referenced Image Sequence (images in this series)
    image_item = Dataset()
    image_item.ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT Image Storage
    image_item.ReferencedSOPInstanceUID = generate_uid()
    series_item.ReferencedImageSequence = [image_item]
    
    ds.PerformedSeriesSequence = [series_item]
    
    return ds

def create_mpps_test_client():
    """Create a Python script to test MPPS using pynetdicom"""
    
    test_script = '''#!/usr/bin/env python3
"""
Test MPPS functionality using pynetdicom
"""

from pynetdicom import AE
from pynetdicom.sop_class import ModalityPerformedProcedureStep
from pydicom import dcmread
import sys

def test_mpps_ncreate(host, port, dcm_file):
    """Test MPPS N-CREATE"""
    
    # Read the DICOM file
    ds = dcmread(dcm_file)
    
    # Create Application Entity
    ae = AE()
    ae.add_requested_context(ModalityPerformedProcedureStep)
    
    # Associate with the server
    assoc = ae.associate(host, port)
    
    if assoc.is_established:
        print(f"Association established with {host}:{port}")
        
        # Send N-CREATE request
        status, ds_out = assoc.send_n_create(
            ds,
            ModalityPerformedProcedureStep,
            ds.SOPInstanceUID
        )
        
        print(f"N-CREATE Status: 0x{status.Status:04X}")
        if status.Status == 0x0000:
            print("✓ N-CREATE successful")
        else:
            print(f"✗ N-CREATE failed: {status}")
        
        # Release association
        assoc.release()
    else:
        print(f"✗ Failed to establish association with {host}:{port}")

def test_mpps_nset(host, port, dcm_file):
    """Test MPPS N-SET"""
    
    # Read the DICOM file
    ds = dcmread(dcm_file)
    
    # Create Application Entity
    ae = AE()
    ae.add_requested_context(ModalityPerformedProcedureStep)
    
    # Associate with the server
    assoc = ae.associate(host, port)
    
    if assoc.is_established:
        print(f"Association established with {host}:{port}")
        
        # Send N-SET request
        status, ds_out = assoc.send_n_set(
            ds,
            ModalityPerformedProcedureStep,
            ds.SOPInstanceUID
        )
        
        print(f"N-SET Status: 0x{status.Status:04X}")
        if status.Status == 0x0000:
            print("✓ N-SET successful")
        else:
            print(f"✗ N-SET failed: {status}")
        
        # Release association
        assoc.release()
    else:
        print(f"✗ Failed to establish association with {host}:{port}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 test_mpps_client.py <host> <port> <dcm_file>")
        print("Example: python3 test_mpps_client.py localhost 4104 mpps_create.dcm")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    dcm_file = sys.argv[3]
    
    print(f"Testing MPPS with {dcm_file}")
    
    # Determine if this is N-CREATE or N-SET based on file content
    ds = dcmread(dcm_file)
    status = getattr(ds, 'PerformedProcedureStepStatus', 'IN PROGRESS')
    
    if status == "IN PROGRESS":
        print("Testing N-CREATE (procedure start)...")
        test_mpps_ncreate(host, port, dcm_file)
    else:
        print("Testing N-SET (procedure completion)...")
        test_mpps_nset(host, port, dcm_file)
'''
    
    return test_script

def create_matching_mwl_json():
    """Create the exact JSON that should be sent to create the matching MWL entry"""
    
    mwl_json = {
        "AccessionNumber": "TEST123",
        "PatientID": "P1", 
        "PatientName": "DOE^JOHN",
        "PatientBirthDate": "19800101",
        "PatientSex": "M",
        "StudyInstanceUID": "1.2.3.4.5",
        "ScheduledProcedureStepSequence": [{
            "ScheduledProcedureStepStartDate": "20240625",
            "ScheduledStationAETitle": "ORTHANC"
        }]
    }
    
    return mwl_json

def main():
    """Create test MPPS files and testing tools"""
    
    # Generate ONE SOP Instance UID for both files
    shared_sop_instance_uid = generate_uid()
    
    # Create output directory
    os.makedirs("test_mpps", exist_ok=True)
    
    # Create N-CREATE file with shared UID
    print("Creating MPPS N-CREATE test file...")
    create_ds = create_mpps_create_file(shared_sop_instance_uid)
    
    # Write with proper DICOM format
    dcmwrite("test_mpps/mpps_create.dcm", create_ds, 
             write_like_original=False,
             enforce_file_format=True)
    print("Created: test_mpps/mpps_create.dcm")
    
    # Create N-SET file with same shared UID
    print("Creating MPPS N-SET test file...")
    set_ds = create_mpps_set_file(shared_sop_instance_uid)
    
    # Write with proper DICOM format
    dcmwrite("test_mpps/mpps_set.dcm", set_ds,
             write_like_original=False,
             enforce_file_format=True)
    print("Created: test_mpps/mpps_set.dcm")
    
    # Create matching MWL JSON
    mwl_json = create_matching_mwl_json()
    with open("test_mpps/matching_mwl.json", "w") as f:
        import json
        json.dump(mwl_json, f, indent=2)
    print("Created: test_mpps/matching_mwl.json")
    
    # Create MPPS test client
    test_script = create_mpps_test_client()
    with open("test_mpps/test_mpps_client.py", "w") as f:
        f.write(test_script)
    print("Created: test_mpps/test_mpps_client.py")
    
    print("\nTest files created successfully!")
    print("\nComplete test workflow:")
    print("1. Start services: docker-compose up")
    print("2. Create MWL entry:")
    print("   curl -X POST http://localhost:8000/mwl/create_from_json \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d @test_mpps/matching_mwl.json")
    print("3. Test MWL query: findscu localhost 4104 -W -v -d -k AccessionNumber=TEST123")
    print("4. Test MPPS N-CREATE: python3 test_mpps/test_mpps_client.py localhost 4104 test_mpps/mpps_create.dcm")
    print("5. Test MPPS N-SET: python3 test_mpps/test_mpps_client.py localhost 4104 test_mpps/mpps_set.dcm")
    
    # Verify file format
    print(f"\nVerifying DICOM file format...")
    try:
        from pydicom import dcmread
        test_ds = dcmread("test_mpps/mpps_create.dcm")
        print(f"✓ MPPS N-CREATE file is valid DICOM")
        print(f"  SOP Class: {test_ds.SOPClassUID}")
        print(f"  SOP Instance UID: {test_ds.SOPInstanceUID}")
        print(f"  Transfer Syntax: {test_ds.file_meta.TransferSyntaxUID}")
        
        test_ds2 = dcmread("test_mpps/mpps_set.dcm")
        print(f"✓ MPPS N-SET file is valid DICOM")
        print(f"  SOP Class: {test_ds2.SOPClassUID}")
        print(f"  SOP Instance UID: {test_ds2.SOPInstanceUID}")
        
        # Verify they have the same SOP Instance UID
        if test_ds.SOPInstanceUID == test_ds2.SOPInstanceUID:
            print(f"✓ Both files share the same SOP Instance UID: {shared_sop_instance_uid}")
        else:
            print(f"✗ SOP Instance UID mismatch!")
        
    except Exception as e:
        print(f"✗ Error verifying DICOM files: {e}")
    
    # Display key information
    print(f"\nKey identifiers:")
    print(f"Shared SOP Instance UID: {shared_sop_instance_uid}")
    print(f"AccessionNumber: {create_ds.AccessionNumber}")
    print(f"StudyInstanceUID: {create_ds.StudyInstanceUID}")
    print(f"PatientID: {create_ds.PatientID}")
    print(f"PerformedStationAETitle: {create_ds.PerformedStationAETitle}")
    print(f"MPPS SOP Class UID: {MPPS_SOP_CLASS_UID}")

if __name__ == "__main__":
    main()