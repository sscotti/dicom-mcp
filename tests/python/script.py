import orthanc
import json

def OnChange(changeType, level, resource):
    """
    This function is called whenever a DICOM resource is added/modified/deleted.
    Useful for custom processing, notifications, or integrations.
    """
    if changeType == orthanc.ChangeType.STABLE_STUDY:
        # A study has become stable (no new instances for a while)
        study_info = orthanc.RestApiGet('/studies/%s' % resource)
        study_data = json.loads(study_info)
        
        orthanc.LogInfo('New stable study: %s - %s' % (
            study_data.get('PatientMainDicomTags', {}).get('PatientName', 'Unknown'),
            study_data.get('MainDicomTags', {}).get('StudyDescription', 'No description')
        ))
        
        # Example: Auto-send to AI analysis node (if configured)
        # orthanc.RestApiPost('/modalities/AI_NODE/store', resource)

def OnStoredInstance(dicom, instanceId):
    """
    This function is called whenever a new DICOM instance is stored.
    """
    # Extract some basic information
    tags = json.loads(dicom.GetInstanceSimplifiedJson())
    
    orthanc.LogInfo('New instance stored: %s' % instanceId)
    
    # Example: Log patient and study information
    patient_name = tags.get('PatientName', 'Unknown')
    study_description = tags.get('StudyDescription', 'No description')
    modality = tags.get('Modality', 'Unknown')
    
    orthanc.LogInfo('  Patient: %s' % patient_name)
    orthanc.LogInfo('  Study: %s' % study_description) 
    orthanc.LogInfo('  Modality: %s' % modality)
    
    # Example: Auto-process chest X-rays
    if modality == 'CR' or modality == 'DX':
        body_part = tags.get('BodyPartExamined', '')
        if 'CHEST' in body_part.upper():
            orthanc.LogInfo('  -> Chest X-ray detected, could trigger AI analysis')

def OnHeartBeat():
    """
    This function is called periodically by Orthanc.
    Useful for maintenance tasks or periodic checks.
    """
    # Example: Log system status every few minutes
    pass

# Register the callbacks
orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterOnStoredInstanceCallback(OnStoredInstance)
orthanc.RegisterOnHeartBeatCallback(OnHeartBeat)

orthanc.LogInfo('Enhanced Orthanc Python plugin loaded successfully!')
