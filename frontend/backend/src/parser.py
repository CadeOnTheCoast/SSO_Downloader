import re
import logging
import pdfplumber
from typing import Dict, Any, Optional
from datetime import datetime
from PIL import Image
try:
    from pdf2image import convert_from_path
    import pytesseract
except ImportError:
    logging.warning("Optional OCR dependencies (pdf2image, pytesseract) not found.")

from models import SSOReportCreate

class SSOParser:
    """Enterprise-grade parser for ADEM SSO PDF reports."""
    
    # Enhanced regex patterns with better boundary handling and multiline support
    REGEX_PATTERNS = {
        "permit_number": r"Permit Number\s+([A-Z0-9]+)",
        "permittee": r"Permittee\s+([A-Za-z0-9 ,.&\-]+)",
        "facility_name": r"Facility Name\s+(.+?)\s+Facility County",
        "facility_county": r"Facility County\s+(\w+)",
        "sso_id": r"Assigned SSO ID\s+SSO-(\d+)",
        "volume": r"Estimated Volume Discharged \(in gallons\)\s+([\d,<> to]+)",
        "volume_range": r"Estimated Volume Discharged \(Range\)\s*[\d,<=> ]*gallons\s*<=\s*([\d,]+)",
        "source": r"Indicate source of discharge event\s+(.+?)\s+County in which",
        "latitude": r"Latitude/Longitude of discharge\s+([\d\.\-]+),",
        "longitude": r"Latitude/Longitude of discharge\s+[\d\.\-]+,\s*([\d\.\-]+)",
        "address": r"Street Address\s+(.+)",
        "city": r"City\s+(.+?),",
        "state": r"State\s+([A-Z]{2})",
        "zip": r"ZIP Code\s+(\d+)",
        "location_desc": r"Location Description\s+(.+?)\s+Known or suspected cause",
        "cause": r"Known or suspected cause of the discharge\s*(.*?)(?=\s*Destination of discharge|$)",
        "destination": r"Destination of discharge\s*(.*?)(?=\s*Note:|$)",
        "receiving_water": r"Provide the first named creek or river that receives the flow\.\s*(.*?)(?=\s*Did the discharge|$)",
        "corrective_action": r"Describe corrective actions taken.*?\n(.+?)\nPlease attach",
        "public_notice": r"Indicate efforts to notify public.*?\n(.+?)\nDate signs were placed:",
        "signs_date": r"Date signs were placed:\s+([\d/]+)",
        "health_notified": r"County Health Department notification date:\s+([\d/]+)",
    }

    def extract_text(self, file_path: str) -> str:
        """Extract text from PDF with OCR fallback."""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text(layout=True) or ""
            
            if not text.strip():
                raise ValueError("Extracted text is empty. Attempting OCR.")
                
        except Exception as e:
            logging.info(f"PDF extract failed for {file_path}, trying OCR: {e}")
            text = self._ocr_pdf(file_path)
            
        return text

    def _ocr_pdf(self, file_path: str) -> str:
        """Perform OCR if text extraction fails."""
        try:
            images = convert_from_path(file_path)
            return "\n".join([pytesseract.image_to_string(img) for img in images])
        except Exception as e:
            logging.error(f"OCR failed for {file_path}: {e}")
            return ""

    def parse_text(self, text: str) -> SSOReportCreate:
        """Parse raw text into a validated SSOReportCreate model."""
        data: Dict[str, Any] = {}
        
        for key, pattern in self.REGEX_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1).strip()
                
                # Special handling for volume logic inherited from legacy
                if key == "volume":
                    if '<' in value or 'to' in value.lower():
                        data["est_volume_is_range"] = True
                        data["volume_gallons"] = 9999 # Standard placeholder for ranges
                    else:
                        data["volume_gallons"] = value
                elif key == "volume_range":
                    # If we already have a volume, don't overwrite with range unless it's missing
                    if "volume_gallons" not in data or data["volume_gallons"] == 9999:
                        data["volume_gallons"] = value
                else:
                    # Map to model field names if different
                    model_key = key
                    if key == "permit_number": model_key = "utility_id"
                    if key == "permittee": model_key = "utility_name"
                    
                    data[model_key] = value

        # Metadata
        data["raw"] = {"parsed_at": datetime.now().isoformat()}

        return SSOReportCreate(**data)

    def process_file(self, file_path: str) -> Optional[SSOReportCreate]:
        """Orchestrate the extraction and parsing of a single file."""
        text = self.extract_text(file_path)
        if not text:
            return None
            
        try:
            return self.parse_text(text)
        except Exception as e:
            logging.error(f"Failed to parse {file_path}: {e}")
            return None
