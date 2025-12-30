from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class SSOReportBase(BaseModel):
    sso_id: Optional[str] = Field(None, description="Assigned SSO ID (e.g., SSO-00213733)")
    utility_id: Optional[str] = Field(None, description="Permit Number")
    utility_name: Optional[str] = Field(None, description="Permittee Name")
    sewer_system: Optional[str] = None
    county: Optional[str] = None
    location_desc: Optional[str] = None
    
    date_sso_began: Optional[datetime] = None
    date_sso_stopped: Optional[datetime] = None
    
    volume_gallons: Optional[float] = Field(None, ge=0)
    est_volume: Optional[str] = None
    est_volume_gal: Optional[int] = Field(None, ge=0)
    est_volume_is_range: Optional[bool] = False
    est_volume_range_label: Optional[str] = None
    
    cause: Optional[str] = None
    receiving_water: Optional[str] = None
    
    x: Optional[float] = None
    y: Optional[float] = None
    
    raw: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('volume_gallons', 'est_volume_gal', mode='before')
    @classmethod
    def parse_numeric(cls, v: Any) -> Optional[float]:
        if v is None or v == '' or v == '–':
            return None
        if isinstance(v, str):
            # Clean up strings like "< 1000" or "None"
            v = v.replace('<', '').replace('>', '').replace(',', '').strip()
            if v.lower() in ('none', 'unknown', ''):
                return None
            try:
                return float(v)
            except ValueError:
                return None
        return v

class SSOReportCreate(SSOReportBase):
    pass

class SSOReport(SSOReportBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
