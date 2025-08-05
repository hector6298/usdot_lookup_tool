from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from pydantic import ConfigDict
from sqlmodel import Relationship

if TYPE_CHECKING:
    from app.models.carrier_data import CarrierData
    from app.models.user_org_membership import AppUser, AppOrg

class OCRResultCreate(SQLModel):
    """Schema for creating a new OCR result."""
    extracted_text: str | None = Field(default=None, max_length=250)
    filename: str = Field(nullable=False, max_length=250)
    user_id: str = Field(nullable=False)
    org_id: str = Field(nullable=False)
    
class OCRResult(SQLModel, table=True):
    """Represents an OCR result in the database."""    
    model_config = ConfigDict(
        orm_mode = True 
    )
    id: int = Field(default=None, primary_key=True)
    extracted_text: str | None = Field(default=None, max_length=250)
    dot_reading: str | None = Field(default=None, max_length=32)
    filename: str = Field(nullable=False, max_length=250)
    timestamp: datetime = Field(nullable=False)
    user_id: str = Field(nullable=False, foreign_key="appuser.user_id")
    org_id: str = Field(nullable=False, foreign_key="apporg.org_id")
    lookup_success_flag: bool = Field(default=False, nullable=False)
    
    app_user: "AppUser" = Relationship(back_populates="ocr_results")
    app_org: "AppOrg" = Relationship(back_populates="ocr_results")

class OCRResultResponse(SQLModel):
    """Schema for returning OCR result data."""
    dot_reading: str | None
    timestamp: str
    filename: str
    lookup_success_flag: bool
    user_id: str
    org_id: str
    