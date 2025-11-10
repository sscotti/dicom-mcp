#!/usr/bin/env python3
"""
Integration tests for DICOM MWL-MPPS functionality
"""

import pytest
from pynetdicom import AE
from pynetdicom.sop_class import ModalityPerformedProcedureStep
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid, PYDICOM_IMPLEMENTATION_UID
from datetime import datetime, date
import requests
import time
import os
import socket

# Import the correct SOP Class UID
try:
    from pynetdicom.sop_class import ModalityPerformedProcedureStep
    MPPS_SOP_CLASS_UID = ModalityPerformedProcedureStep
except ImportError:
    MPPS_SOP_CLASS_UID = "1.2.840.10008.3.1.2.3.3"

# Configuration for different environments
def get_api_url():
    """Get API URL based on environment"""
    # Check if we're running inside a Docker container
    if os.path.exists('/.dockerenv'):
        return "http://mwl-api:8000"
    else:
        return "http://localhost:8000"

def get_dicom_host():
    """Get DICOM host based on environment"""
    # Check if we're running inside a Docker container
    if os.path.exists('/.dockerenv'):
        # Resolve to IP address to work around pynetdicom DNS issues
        try:
            return socket.gethostbyname('dicom-mwl-mpps')
        except socket.gaierror:
            return "dicom-mwl-mpps"  # Fallback to hostname
    else:
        return "localhost"

def get_dicom_port():
    """Get DICOM port based on environment"""
    return 104 if os.path.exists('/.dockerenv') else 4104

class TestData:
    """Test data factory for DICOM datasets"""
    
    @staticmethod
    def create_mwl_entry_json():
        """Create MWL entry via REST API"""
        return {
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
    
    @staticmethod
    def create_mpps_dataset(sop_instance_uid, status="IN PROGRESS"):
        """Create MPPS dataset dynamically"""
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
        
        ds.file_meta = file_meta
        ds.is_little_endian = True
        ds.is_implicit_VR = False
        
        # SOP Class and Instance
        ds.SOPClassUID = MPPS_SOP_CLASS_UID
        ds.SOPInstanceUID = sop_instance_uid
        
        # Patient Information
        ds.PatientName = "DOE^JOHN"
        ds.PatientID = "P1"
        ds.PatientBirthDate = "19800101"
        ds.PatientSex = "M"
        
        # Study Information
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.AccessionNumber = "TEST123"
        
        if status == "IN PROGRESS":
            # N-CREATE dataset
            ds.PerformedProcedureStepID = "PPS001"
            ds.PerformedProcedureStepStatus = status
            ds.PerformedProcedureStepStartDate = date.today().strftime("%Y%m%d")
            ds.PerformedProcedureStepStartTime = datetime.now().strftime("%H%M%S")
            ds.Modality = "CT"
            ds.PerformedStationAETitle = "ORTHANC"
            ds.PerformedStationName = "CT_SCANNER_01"
            ds.PerformedProcedureStepDescription = "Chest CT Scan"
            
            # Scheduled Step Attributes Sequence
            sched_step_item = Dataset()
            sched_step_item.StudyInstanceUID = ds.StudyInstanceUID
            sched_step_item.AccessionNumber = ds.AccessionNumber
            sched_step_item.RequestedProcedureID = "REQ001"
            sched_step_item.ScheduledProcedureStepID = "SPS001"
            sched_step_item.ScheduledProcedureStepStartDate = "20240625"
            sched_step_item.ScheduledStationAETitle = "ORTHANC"
            ds.ScheduledStepAttributesSequence = [sched_step_item]
        else:
            # N-SET dataset
            ds.PerformedProcedureStepStatus = status
            ds.PerformedProcedureStepEndDate = date.today().strftime("%Y%m%d")
            ds.PerformedProcedureStepEndTime = datetime.now().strftime("%H%M%S")
            
            # Performed Series Sequence
            series_item = Dataset()
            series_item.SeriesInstanceUID = generate_uid()
            series_item.SeriesDescription = "Chest CT Images"
            series_item.Modality = "CT"
            series_item.OperatorsName = "TECH^JOHN"
            
            image_item = Dataset()
            image_item.ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
            image_item.ReferencedSOPInstanceUID = generate_uid()
            series_item.ReferencedImageSequence = [image_item]
            
            ds.PerformedSeriesSequence = [series_item]
        
        return ds

class TestMWLMPPS:
    """Integration tests for MWL-MPPS functionality"""
    
    @pytest.fixture(scope="class")
    def setup_mwl_entry(self):
        """Create MWL entry via REST API before tests"""
        mwl_data = TestData.create_mwl_entry_json()
        api_url = get_api_url()
        
        print(f"Creating MWL entry via: {api_url}")
        response = requests.post(
            f"{api_url}/mwl/create_from_json",
            json=mwl_data
        )
        assert response.status_code == 200, f"Failed to create MWL entry: {response.text}"
        time.sleep(1)  # Allow DB to update
        return mwl_data
    
    def test_mpps_ncreate(self, setup_mwl_entry):
        """Test MPPS N-CREATE operation"""
        sop_instance_uid = generate_uid()
        ds = TestData.create_mpps_dataset(sop_instance_uid, "IN PROGRESS")
        
        dicom_host = get_dicom_host()
        dicom_port = get_dicom_port()
        print(f"Connecting to DICOM service: {dicom_host}:{dicom_port}")
        
        ae = AE()
        ae.add_requested_context(ModalityPerformedProcedureStep)
        
        assoc = ae.associate(dicom_host, dicom_port)
        assert assoc.is_established, f"Failed to establish DICOM association with {dicom_host}:{dicom_port}"
        
        try:
            status, ds_out = assoc.send_n_create(
                ds, ModalityPerformedProcedureStep, sop_instance_uid
            )
            assert status.Status == 0x0000, f"N-CREATE failed with status: 0x{status.Status:04X}"
            print("N-CREATE operation successful!")
        finally:
            assoc.release()
    
    def test_mpps_nset(self, setup_mwl_entry):
        """Test MPPS N-SET operation"""
        # First create an MPPS entry
        sop_instance_uid = generate_uid()
        dicom_host = get_dicom_host()
        dicom_port = get_dicom_port()
        
        # N-CREATE
        ds_create = TestData.create_mpps_dataset(sop_instance_uid, "IN PROGRESS")
        ae = AE()
        ae.add_requested_context(ModalityPerformedProcedureStep)
        
        assoc = ae.associate(dicom_host, dicom_port)
        assert assoc.is_established
        
        try:
            status, _ = assoc.send_n_create(
                ds_create, ModalityPerformedProcedureStep, sop_instance_uid
            )
            assert status.Status == 0x0000
            print("N-CREATE for N-SET test successful!")
        finally:
            assoc.release()
        
        time.sleep(1)  # Allow processing
        
        # N-SET to complete
        ds_set = TestData.create_mpps_dataset(sop_instance_uid, "COMPLETED")
        assoc = ae.associate(dicom_host, dicom_port)
        assert assoc.is_established
        
        try:
            status, _ = assoc.send_n_set(
                ds_set, ModalityPerformedProcedureStep, sop_instance_uid
            )
            assert status.Status == 0x0000, f"N-SET failed with status: 0x{status.Status:04X}"
            print("N-SET operation successful!")
        finally:
            assoc.release()
    
    def test_mwl_cfind(self):
        """Test MWL C-FIND operation"""
        # This would require findscu or pynetdicom C-FIND implementation
        # Can be added as separate test
        pass

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 