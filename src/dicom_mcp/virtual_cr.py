"""
Virtual CR Device - Synthetic DICOM image generation for testing/demo.

WARNING: Synthetic images are for development/testing/training purposes only.
NOT for clinical use or diagnosis. NOT based on real patient data.
"""

import base64
import io
import logging
import os
import ssl
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import numpy as np
import pydicom
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid, ExplicitVRLittleEndian
from pynetdicom import AE, StoragePresentationContexts
from pynetdicom.sop_class import ComputedRadiographyImageStorage

logger = logging.getLogger("dicom_mcp.virtual_cr")


class VirtualCRDevice:
    """Simulates a CR device that generates synthetic DICOM images."""
    
    def __init__(
        self,
        manufacturer: str = "Virtual Devices Inc.",
        model: str = "VirtualCR-2000",
        station_name: str = "CR-VIRTUAL-01",
        openai_api_key: Optional[str] = None
    ):
        self.manufacturer = manufacturer
        self.model = model
        self.station_name = station_name
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
    def create_study(
        self,
        mwl_data: Dict[str, Any],
        image_mode: str = "auto",
        image_description: str = "normal",
        num_images: int = None
    ) -> Dict[str, Any]:
        """Create a complete CR study from MWL data.
        
        Args:
            mwl_data: Dictionary with MWL information (patient, procedure, etc.)
            image_mode: "auto", "ai", "simple", or "sample"
            image_description: Description for AI generation (e.g., "pneumonia")
            num_images: Number of images to create (default from MWL)
            
        Returns:
            Dictionary with study creation results
        """
        # Determine image mode
        if image_mode == "auto":
            image_mode = "ai" if self.openai_api_key else "simple"
        
        # Extract MWL data
        procedure_desc = mwl_data.get('procedure_description', 'CR Study')
        typical_views = mwl_data.get('typical_views', 'AP')
        typical_count = num_images or int(mwl_data.get('typical_image_count', 1))
        
        # Parse views
        views = self._parse_views(typical_views, typical_count)
        
        logger.info(f"Creating CR study with {len(views)} images using '{image_mode}' mode")
        
        # Generate images for each view
        study_uid = mwl_data.get('StudyInstanceUID', generate_uid())
        series_uid = generate_uid()
        
        created_files = []
        for idx, view in enumerate(views, 1):
            try:
                # Generate image
                if image_mode == "ai":
                    try:
                        image = self._generate_ai_image(
                            mwl_data['modality_code'],
                            mwl_data.get('body_part_code', 'CHEST'),
                            view,
                            image_description
                        )
                    except Exception as ai_error:
                        logger.warning(f"AI generation failed ({str(ai_error)}), falling back to simple mode")
                        image = self._generate_simple_image(
                            mwl_data.get('body_part_code', 'CHEST'),
                            view,
                            mwl_data
                        )
                        image_mode = "simple"  # Update mode for result
                elif image_mode == "sample":
                    image = self._load_sample_image(
                        mwl_data.get('body_part_code', 'CHEST'),
                        view
                    )
                else:  # simple
                    image = self._generate_simple_image(
                        mwl_data.get('body_part_code', 'CHEST'),
                        view,
                        mwl_data
                    )
                
                # Create DICOM file
                dcm_file = self._create_dicom_file(
                    image=image,
                    mwl_data=mwl_data,
                    study_uid=study_uid,
                    series_uid=series_uid,
                    instance_number=idx,
                    view=view
                )
                
                created_files.append({
                    'file': dcm_file,
                    'instance_number': idx,
                    'view': view
                })
                
            except Exception as e:
                import traceback
                logger.error(f"Error creating image {idx}: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
        
        return {
            'success': True,
            'study_uid': study_uid,
            'series_uid': series_uid,
            'num_images': len(created_files),
            'files': created_files,
            'image_mode': image_mode
        }
    
    def _parse_views(self, views_str: str, count: int) -> list:
        """Parse view string into list of views."""
        if not views_str:
            return ['AP'] * count
        
        # Split on common separators
        views = []
        for sep in [' and ', ', ', '/']:
            if sep in views_str:
                views = [v.strip() for v in views_str.split(sep)]
                break
        
        if not views:
            views = [views_str.strip()]
        
        # Pad or trim to match count
        while len(views) < count:
            views.append(views[-1] if views else 'AP')
        
        return views[:count]
    
    def _generate_simple_image(
        self, body_part: str, view: str, mwl_data: Dict
    ) -> Image.Image:
        """Generate simple synthetic CR image without API."""
        # Create 2048x2048 grayscale image (typical CR size)
        img = Image.new('L', (2048, 2048), color=20)
        draw = ImageDraw.Draw(img)
        
        # Add subtle gradient for realism
        for y in range(2048):
            gray_value = int(20 + (y / 2048) * 15)
            draw.line([(0, y), (2048, y)], fill=gray_value)
        
        # Add anatomical outlines based on body part
        if body_part in ['CHEST', 'THORAX']:
            # Simple chest outline
            # Heart shadow (left side)
            draw.ellipse([700, 800, 1100, 1400], fill=50, outline=70, width=3)
            # Lung fields
            draw.ellipse([400, 400, 900, 1600], outline=40, width=2)
            draw.ellipse([1100, 400, 1600, 1600], outline=40, width=2)
            # Ribs (simplified)
            for i in range(8):
                y = 500 + i * 150
                draw.arc([300, y, 1700, y+100], 0, 180, fill=45, width=2)
        
        elif body_part in ['ABD', 'ABDOMEN']:
            # Pelvis outline
            draw.ellipse([700, 1200, 1300, 1800], outline=50, width=3)
            # Spine
            for y in range(200, 1800, 50):
                draw.rectangle([980, y, 1020, y+30], fill=55)
        
        elif body_part in ['EXT_LOW', 'KNEE']:
            # Knee joint simplified
            draw.rectangle([800, 600, 1200, 1400], outline=60, width=3)
            draw.ellipse([850, 950, 1150, 1100], fill=45)
        
        # Add markers and labels
        font = None
        # Try system fonts first
        for font_path in ["/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
            try:
                font = ImageFont.truetype(font_path, 40)
                break
            except:
                continue
        
        # Fallback to default font
        if font is None:
            try:
                font = ImageFont.load_default()
            except:
                font = None  # Will use PIL's built-in default
        
        # Add view marker
        draw.text((100, 100), f"{view}", fill=200, font=font)
        
        # Add patient info (lower corner)
        patient_text = f"{mwl_data.get('mrn', 'MRN')} - {mwl_data.get('accession_number', 'ACC')}"
        draw.text((100, 1900), patient_text, fill=200, font=font)
        
        # Add "L" or "R" marker if applicable
        if 'Left' in view or 'LEFT' in view.upper():
            draw.text((1900, 1000), "L", fill=220, font=font)
        elif 'Right' in view or 'RIGHT' in view.upper():
            draw.text((1900, 1000), "R", fill=220, font=font)
        
        # Add noise for realism
        img_array = np.array(img)
        noise = np.random.normal(0, 3, img_array.shape)
        img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
        
        return Image.fromarray(img_array)
    
    def _generate_ai_image(
        self, modality: str, body_part: str, view: str, description: str
    ) -> Image.Image:
        """Generate realistic CR image using OpenAI image models."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key required for AI image generation")
        
        # Build prompt for medical imaging
        prompt = self._build_ai_prompt(modality, body_part, view, description)
        
        logger.info(f"Prompt: {prompt[:150]}...")
        
        # Initialize OpenAI client with extended timeout
        client = OpenAI(
            api_key=self.openai_api_key,
            timeout=90.0
        )
        
        # Generate with gpt-image-1
        try:
            logger.info("Generating with gpt-image-1...")
            response = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1024x1024",  # Can use "512x512" for faster generation
                n=1
                # Note: gpt-image-1 doesn't support response_format parameter
            )
            
            # Handle response - can be URL or base64
            if not response.data:
                raise Exception("No data in response")
            
            if hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
                # Base64 encoded
                image_data = base64.b64decode(response.data[0].b64_json)
                logger.info(f"Image received (b64) - {len(image_data)} bytes")
            elif hasattr(response.data[0], 'url') and response.data[0].url:
                # URL - need to download
                import requests
                logger.info(f"Downloading image from URL: {response.data[0].url[:50]}...")
                img_response = requests.get(response.data[0].url, timeout=30)
                img_response.raise_for_status()
                image_data = img_response.content
                logger.info(f"Image downloaded (url) - {len(image_data)} bytes")
            else:
                raise Exception("Unexpected response format - no b64_json or url")
                
        except Exception as e:
            logger.error(f"gpt-image-1 generation failed: {e}", exc_info=True)
            raise Exception(f"gpt-image-1 failed: {str(e)}")
        
        # Convert to grayscale and resize to CR dimensions
        img = Image.open(io.BytesIO(image_data)).convert('L')
        img = img.resize((2048, 2048), Image.Resampling.LANCZOS)
        
        # Post-process for CR appearance
        img = self._apply_cr_processing(img)
        
        return img
    
    def _build_ai_prompt(
        self, modality: str, body_part: str, view: str, description: str
    ) -> str:
        """Build optimized prompt for medical image generation."""
        body_map = {
            'CHEST': 'chest',
            'ABD': 'abdomen',
            'PELV': 'pelvis',
            'EXT_UP': 'arm',
            'EXT_LOW': 'leg',
            'KNEE': 'knee',
            'HAND': 'hand'
        }
        
        body_text = body_map.get(body_part, body_part.lower())
        
        # Build prompt emphasizing photorealistic clinical appearance
        prompt = f"""Photorealistic chest X-ray radiograph image from a hospital radiology department.
Real clinical {view} view {body_text} X-ray with authentic medical imaging characteristics.
Actual radiographic film appearance showing natural asymmetry, realistic tissue densities,
organic bone structure with normal variations. Heart positioned on left side, lung fields
with natural vascular markings, realistic rib spacing and contours. Authentic grayscale
gradients from dense bone (bright white) through soft tissue to lung air spaces (dark gray).
Natural imperfections in patient positioning, realistic scatter radiation patterns"""
        
        if description and description.lower() != "normal":
            prompt += f", with visible {description}"
        else:
            prompt += ", unremarkable study with no acute findings"
        
        prompt += """. Genuine medical radiology imaging quality, not illustration or diagram.
Raw radiograph appearance as acquired from CR detector, suitable for clinical review and
medical training purposes only. Photographic realism required."""
        
        return prompt
    
    def _apply_cr_processing(self, img: Image.Image) -> Image.Image:
        """Apply CR-specific image processing."""
        img_array = np.array(img)
        
        # Adjust contrast
        img_array = np.clip(img_array * 1.1, 0, 255).astype(np.uint8)
        
        # Add realistic sensor noise
        noise = np.random.normal(0, 2.5, img_array.shape)
        img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
        
        return Image.fromarray(img_array)
    
    def _load_sample_image(self, body_part: str, view: str) -> Image.Image:
        """Load pre-made sample image from library."""
        # Look for sample images in samples directory
        samples_dir = Path(__file__).parent.parent.parent / "samples" / "cr_images"
        
        # Try to find matching sample
        pattern = f"{body_part.lower()}_{view.lower()}.png"
        sample_file = samples_dir / pattern
        
        if sample_file.exists():
            return Image.open(sample_file).convert('L')
        
        # Fallback to generic sample or simple generation
        logger.warning(f"Sample image not found: {sample_file}, using simple generation")
        return self._generate_simple_image(body_part, view, {})
    
    def _create_dicom_file(
        self,
        image: Image.Image,
        mwl_data: Dict[str, Any],
        study_uid: str,
        series_uid: str,
        instance_number: int,
        view: str
    ) -> str:
        """Create DICOM file from image and MWL data."""
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.dcm', delete=False, mode='wb'
        )
        temp_file.close()
        
        # Convert image to numpy array
        pixel_array = np.array(image)
        
        # Create DICOM dataset
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.1'  # CR Image Storage
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.ImplementationClassUID = generate_uid()
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        
        ds = FileDataset(
            temp_file.name, {},
            file_meta=file_meta,
            preamble=b"\0" * 128
        )
        
        # Patient Module
        ds.PatientName = mwl_data.get('patient_name', mwl_data.get('PatientName', ''))
        ds.PatientID = mwl_data.get('mrn', mwl_data.get('PatientID', ''))
        
        # Handle date_of_birth (might be date object or string)
        dob = mwl_data.get('date_of_birth', mwl_data.get('PatientBirthDate', ''))
        if dob:
            ds.PatientBirthDate = str(dob).replace('-', '')
        else:
            ds.PatientBirthDate = ''
        
        ds.PatientSex = mwl_data.get('sex', mwl_data.get('PatientSex', 'O'))
        
        # Study Module
        ds.StudyInstanceUID = study_uid
        ds.StudyDate = datetime.now().strftime('%Y%m%d')
        ds.StudyTime = datetime.now().strftime('%H%M%S')
        ds.AccessionNumber = mwl_data.get('accession_number', mwl_data.get('AccessionNumber', ''))
        ds.StudyDescription = mwl_data.get('procedure_description', 'CR Study')
        
        # Series Module
        ds.SeriesInstanceUID = series_uid
        ds.SeriesNumber = 1
        ds.SeriesDescription = f"CR {view}"
        ds.Modality = 'CR'
        
        # Equipment Module
        ds.Manufacturer = self.manufacturer
        ds.ManufacturerModelName = self.model
        ds.StationName = self.station_name
        ds.SoftwareVersions = "VirtualCR v1.0"
        
        # Image Module
        ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.InstanceNumber = instance_number
        ds.ImageType = ['ORIGINAL', 'PRIMARY', 'SYNTHETIC']  # Mark as synthetic!
        ds.AcquisitionDate = ds.StudyDate
        ds.AcquisitionTime = ds.StudyTime
        
        # Image Pixel Module
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.Rows, ds.Columns = pixel_array.shape
        ds.BitsAllocated = 16
        ds.BitsStored = 12
        ds.HighBit = 11
        ds.PixelRepresentation = 0
        
        # Scale pixel data to 12-bit range
        pixel_array_16 = (pixel_array.astype(np.float32) / 255.0 * 4095).astype(np.uint16)
        ds.PixelData = pixel_array_16.tobytes()
        
        # Save
        ds.save_as(temp_file.name, write_like_original=False)
        logger.info(f"Created DICOM file: {temp_file.name}")
        
        return temp_file.name
    
    def send_to_pacs(
        self,
        dicom_files: list,
        pacs_host: str,
        pacs_port: int,
        pacs_aet: str,
        calling_aet: str = "VIRTUALCR",
        use_tls: bool = True
    ) -> Dict[str, Any]:
        """Send DICOM files to PACS using pynetdicom with TLS support."""
        results = []
        
        # Create Application Entity
        ae = AE(ae_title=calling_aet)
        ae.add_requested_context(ComputedRadiographyImageStorage)
        
        # Setup TLS if needed
        tls_args = {}
        if use_tls:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            tls_args = {'tls_args': (ssl_context, None)}
            logger.info(f"Using TLS connection to {pacs_host}:{pacs_port}")
        
        # Send each file
        for file_info in dicom_files:
            dcm_file = file_info['file']
            try:
                # Read DICOM file
                ds = pydicom.dcmread(dcm_file)
                
                # Associate with PACS
                assoc = ae.associate(
                    pacs_host,
                    pacs_port,
                    ae_title=pacs_aet,
                    **tls_args
                )
                
                if assoc.is_established:
                    # Send C-STORE
                    status = assoc.send_c_store(ds)
                    
                    success = status and status.Status == 0x0000
                    
                    results.append({
                        'file': dcm_file,
                        'instance': file_info['instance_number'],
                        'success': success,
                        'message': f"Status: 0x{status.Status:04X}" if status else "No response"
                    })
                    
                    if success:
                        logger.info(f"Sent image {file_info['instance_number']} to PACS successfully")
                    else:
                        logger.error(f"Failed to send image {file_info['instance_number']}: Status 0x{status.Status:04X}")
                    
                    # Release association
                    assoc.release()
                else:
                    logger.error(f"Association rejected by {pacs_aet}")
                    results.append({
                        'file': dcm_file,
                        'instance': file_info['instance_number'],
                        'success': False,
                        'error': 'Association rejected'
                    })
                
            except Exception as e:
                logger.error(f"Error sending {dcm_file}: {e}")
                results.append({
                    'file': dcm_file,
                    'instance': file_info['instance_number'],
                    'success': False,
                    'error': str(e)
                })
        
        # Clean up temporary files
        for file_info in dicom_files:
            try:
                os.unlink(file_info['file'])
            except:
                pass
        
        success_count = sum(1 for r in results if r['success'])
        
        return {
            'success': success_count == len(results),
            'sent': success_count,
            'total': len(results),
            'results': results
        }

